#!/usr/bin/env python3
"""
Vehicle Tinder — local annotation app (Python stdlib only).

Swipe images left (ICE) or right (EV). Labels are saved to output/annotations.csv.

Usage:
    python3 app.py
    python3 app.py --port 8765
"""

from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import os
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
OUTPUT_DIR = APP_DIR / "output"
ANNOTATIONS_CSV = OUTPUT_DIR / "annotations.csv"
CONFIG_PATH = APP_DIR / "config.json"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

CSV_FIELDS = [
    "image_id",
    "filename",
    "relative_path",
    "source_folder",
    "label",
    "annotator",
    "labeled_at_utc",
]

DEFAULT_CONFIG = {
    "port": 8765,
    "open_browser": True,
    # Prefer a bundled images/ folder for sharing. Fall back to the sibling
    # scraper dataset so it also works in the original project layout.
    "image_roots": [
        "images",
        "../EV training dataset",
    ],
    "class_folders": ["ev", "ice"],
    "swipe": {
        "left": "ice",
        "right": "ev",
    },
}


_lock = threading.Lock()
_config: dict = {}
_image_index: list[dict] = []
_labels: dict[str, dict] = {}  # image_id -> row dict


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            user_cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(user_cfg, dict):
                cfg.update(user_cfg)
        except json.JSONDecodeError as exc:
            print(f"Warning: could not parse config.json ({exc}); using defaults.")
    return cfg


def resolve_dataset_root(cfg: dict) -> Path | None:
    for rel in cfg.get("image_roots", []):
        root = (APP_DIR / rel).resolve()
        if not root.exists():
            continue
        class_folders = cfg.get("class_folders", ["ev", "ice"])
        # Accept either root/ev + root/ice, or root itself containing images.
        if any((root / name).is_dir() for name in class_folders):
            return root
        if any(
            p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            for p in root.iterdir()
        ):
            return root
    return None


def build_image_index(cfg: dict) -> list[dict]:
    root = resolve_dataset_root(cfg)
    if root is None:
        return []

    class_folders = cfg.get("class_folders", ["ev", "ice"])
    images: list[dict] = []

    def add_image(path: Path, source_folder: str) -> None:
        rel = path.relative_to(root).as_posix()
        image_id = rel.replace("/", "__")
        images.append(
            {
                "image_id": image_id,
                "filename": path.name,
                "relative_path": rel,
                "source_folder": source_folder,
                "abs_path": str(path),
            }
        )

    found_class_dirs = False
    for folder_name in class_folders:
        folder = root / folder_name
        if not folder.is_dir():
            continue
        found_class_dirs = True
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            if path.name.startswith("."):
                continue
            if path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            # Skip scraper temp / rejected folders
            parts = {p.lower() for p in path.relative_to(folder).parts}
            if parts & {"_tmp_download", "_rejected"}:
                continue
            add_image(path, folder_name)

    if not found_class_dirs:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.name.startswith(".") or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            add_image(path, "unknown")

    return images


def ensure_output() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not ANNOTATIONS_CSV.exists():
        with ANNOTATIONS_CSV.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()


def load_labels() -> dict[str, dict]:
    ensure_output()
    labels: dict[str, dict] = {}
    with ANNOTATIONS_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            image_id = row.get("image_id")
            if image_id:
                labels[image_id] = row
    return labels


def rewrite_csv(labels: dict[str, dict]) -> None:
    ensure_output()
    tmp = ANNOTATIONS_CSV.with_suffix(".csv.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for image_id in sorted(labels):
            row = labels[image_id]
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})
    tmp.replace(ANNOTATIONS_CSV)


def refresh_image_index() -> None:
    """Re-scan image folders so newly copied photos show up without restart."""
    global _image_index
    with _lock:
        _image_index = build_image_index(_config)


def progress_payload() -> dict:
    total = len(_image_index)
    labeled = sum(1 for img in _image_index if img["image_id"] in _labels)
    by_label = {"ev": 0, "ice": 0, "skip": 0}
    for img in _image_index:
        row = _labels.get(img["image_id"])
        if not row:
            continue
        label = (row.get("label") or "").lower()
        if label in by_label:
            by_label[label] += 1
    return {
        "total": total,
        "labeled": labeled,
        "remaining": max(0, total - labeled),
        "by_label": by_label,
        "csv_path": str(ANNOTATIONS_CSV),
    }


def next_unlabeled(after_id: str | None = None) -> dict | None:
    start = 0
    if after_id:
        for i, img in enumerate(_image_index):
            if img["image_id"] == after_id:
                start = i + 1
                break
    for img in _image_index[start:] + _image_index[:start]:
        if img["image_id"] not in _labels:
            return public_image(img)
    return None


def public_image(img: dict) -> dict:
    return {
        "image_id": img["image_id"],
        "filename": img["filename"],
        "relative_path": img["relative_path"],
        "source_folder": img["source_folder"],
        "url": f"/api/file/{img['relative_path']}",
    }


def find_image(image_id: str) -> dict | None:
    for img in _image_index:
        if img["image_id"] == image_id:
            return img
    return None


def json_response(handler: SimpleHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def read_json_body(handler: SimpleHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        data = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


class AnnotationHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        # Keep the terminal quiet except for useful app messages.
        if args and str(args[0]).startswith(("GET /api", "POST /api")):
            return
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            return self._serve_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")

        if path == "/api/config":
            refresh_image_index()
            swipe = _config.get("swipe", {"left": "ice", "right": "ev"})
            root = resolve_dataset_root(_config)
            return json_response(
                self,
                {
                    "swipe": swipe,
                    "dataset_root": str(root) if root else None,
                    "progress": progress_payload(),
                },
            )

        if path == "/api/progress":
            return json_response(self, progress_payload())

        if path == "/api/next":
            after = None
            if parsed.query.startswith("after="):
                after = unquote(parsed.query.split("=", 1)[1])
            nxt = next_unlabeled(after)
            return json_response(
                self,
                {
                    "image": nxt,
                    "progress": progress_payload(),
                    "done": nxt is None,
                },
            )

        if path == "/api/queue":
            refresh_image_index()
            queue = [
                public_image(img)
                for img in _image_index
                if img["image_id"] not in _labels
            ]
            return json_response(
                self,
                {"images": queue, "progress": progress_payload()},
            )

        if path.startswith("/api/file/"):
            rel = unquote(path[len("/api/file/") :])
            return self._serve_dataset_file(rel)

        if path == "/api/export.csv":
            ensure_output()
            data = ANNOTATIONS_CSV.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header(
                "Content-Disposition",
                'attachment; filename="annotations.csv"',
            )
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        # Static assets
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        body = read_json_body(self)

        if path == "/api/label":
            return self._handle_label(body)

        if path == "/api/undo":
            return self._handle_undo()

        if path == "/api/reset":
            return self._handle_reset(body)

        json_response(self, {"error": "not_found"}, status=404)

    def _handle_label(self, body: dict) -> None:
        image_id = str(body.get("image_id") or "").strip()
        label = str(body.get("label") or "").strip().lower()
        annotator = str(body.get("annotator") or "anonymous").strip() or "anonymous"

        if label not in {"ev", "ice", "skip"}:
            return json_response(self, {"error": "invalid_label"}, status=400)

        img = find_image(image_id)
        if img is None:
            return json_response(self, {"error": "unknown_image"}, status=404)

        row = {
            "image_id": image_id,
            "filename": img["filename"],
            "relative_path": img["relative_path"],
            "source_folder": img["source_folder"],
            "label": label,
            "annotator": annotator,
            "labeled_at_utc": datetime.now(timezone.utc).isoformat(),
        }

        with _lock:
            _labels[image_id] = row
            rewrite_csv(_labels)

        return json_response(
            self,
            {
                "ok": True,
                "row": row,
                "progress": progress_payload(),
                "next": next_unlabeled(image_id),
            },
        )

    def _handle_undo(self) -> None:
        with _lock:
            if not _labels:
                return json_response(self, {"ok": False, "error": "nothing_to_undo"}, status=400)
            # Undo the most recently labeled row by timestamp.
            latest_id = max(
                _labels.items(),
                key=lambda item: item[1].get("labeled_at_utc") or "",
            )[0]
            removed = _labels.pop(latest_id)
            rewrite_csv(_labels)

        restored = find_image(latest_id)
        return json_response(
            self,
            {
                "ok": True,
                "undone": removed,
                "image": public_image(restored) if restored else None,
                "progress": progress_payload(),
            },
        )

    def _handle_reset(self, body: dict) -> None:
        confirm = str(body.get("confirm") or "").lower()
        if confirm != "yes":
            return json_response(self, {"error": "confirmation_required"}, status=400)
        with _lock:
            _labels.clear()
            rewrite_csv(_labels)
        return json_response(self, {"ok": True, "progress": progress_payload()})

    def _serve_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404, "File not found")
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _serve_dataset_file(self, rel: str) -> None:
        root = resolve_dataset_root(_config)
        if root is None:
            self.send_error(404, "No dataset")
            return
        # Prevent path traversal
        candidate = (root / rel).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            self.send_error(403, "Forbidden")
            return
        if not candidate.is_file():
            self.send_error(404, "Image not found")
            return
        mime, _ = mimetypes.guess_type(str(candidate))
        data = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)


def write_default_config_if_missing() -> None:
    if CONFIG_PATH.exists():
        return
    CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    global _config, _image_index, _labels

    parser = argparse.ArgumentParser(description="Vehicle Tinder annotation app")
    parser.add_argument("--port", type=int, default=None, help="Port to serve on")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser")
    args = parser.parse_args()

    write_default_config_if_missing()
    _config = load_config()
    port = args.port or int(_config.get("port", 8765))
    open_browser = (not args.no_browser) and bool(_config.get("open_browser", True))

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    (APP_DIR / "images").mkdir(parents=True, exist_ok=True)
    ensure_output()

    _image_index = build_image_index(_config)
    _labels = load_labels()

    root = resolve_dataset_root(_config)
    print("=" * 56)
    print("  Vehicle Tinder — EV / ICE annotation")
    print("=" * 56)
    if root is None:
        print("  WARNING: No images found.")
        print("  Put images in:")
        print(f"    {APP_DIR / 'images' / 'ev'}")
        print(f"    {APP_DIR / 'images' / 'ice'}")
        print("  Or keep the scraper dataset at:")
        print(f"    {(APP_DIR / '../EV training dataset').resolve()}")
    else:
        print(f"  Dataset : {root}")
        print(f"  Images  : {len(_image_index)}")
        print(f"  Labeled : {len(_labels)}")
    print(f"  Output  : {ANNOTATIONS_CSV}")
    print(f"  Open    : http://127.0.0.1:{port}")
    print("  Stop    : Ctrl+C")
    print("=" * 56)

    server = ThreadingHTTPServer(("127.0.0.1", port), AnnotationHandler)

    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
