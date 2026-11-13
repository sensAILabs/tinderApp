# Vehicle Tinder — EV / ICE labeling app

No special installs are required beyond **Python 3**. Labels are saved automatically to a CSV file you can send back.

---

## What you will do

1. Start the app.
2. Enter your name.
3. For each photo:
   - **Swipe right** or press **EV** / `→` → label as **EV**
   - **Swipe left** or press **ICE** / `←` → label as **ICE**
   - **Swipe up** or press **Skip** / `↑` → skip unclear images
   - Press **Undo** / `Z` if you make a mistake
4. When finished, download / send `output/annotations.csv`.

---

## Quick start (annotators)

### 1. Make sure Python 3 is installed

You only need this once. In a terminal / command prompt:

```bash
python3 --version
```

If that fails, try `python --version`. You need Python **3.9+**.
Install from [https://www.python.org/downloads/](https://www.python.org/downloads/) if needed.
On Windows, enable **“Add Python to PATH”** during install.

### 2. Start the app (double-click)

Do **not** open `index.html` in your browser.

Instead, open the `Vehicle tinder` folder and double-click:

| Computer | Double-click this |
|---|---|
| **Mac** | `Start Vehicle Tinder (Mac).command` |
| **Windows** | `Start Vehicle Tinder (Windows).bat` |

A Terminal / Command Prompt window will open, and your browser should go to
[http://127.0.0.1:8765](http://127.0.0.1:8765).

**Keep that Terminal window open** while you label. Close it (or press `Ctrl+C`) when you are done.

#### First time on Mac

If macOS says the file can’t be opened:

1. Right-click `Start Vehicle Tinder (Mac).command`
2. Click **Open**
3. Confirm **Open** again

#### Folder layout

```text
Vehicle tinder/
  Start Vehicle Tinder (Macos).command   ← Mac: double-click this
  Start Vehicle Tinder (Windows).bat       ← Windows: double-click this
  app.py
  config.json
  README.md
  static/
  images/
    ev/          ← EV candidate photos go here
    ice/         ← ICE candidate photos go here
  output/        ← your labels are saved here
```

### 3. Label in the browser

Enter your name → **Start labeling**.

If the browser does not open automatically, visit [http://127.0.0.1:8765](http://127.0.0.1:8765) yourself.

### 4. Send back the CSV

When you are done (or pausing), send this file:

```text
Vehicle tinder/output/annotations.csv
```

You can also click **Download CSV** in the app.

To stop the app, go back to the terminal and press `Ctrl+C`.

---

## How labeling works

| Action | Result |
|---|---|
| Swipe **right** / button **EV** / key `→` | `label = ev` |
| Swipe **left** / button **ICE** / key `←` | `label = ice` |
| Swipe **up** / button **Skip** / key `↑` | `label = skip` |
| **Undo** / key `Z` | removes the last label |

Progress is saved after **every** swipe, so you can close the app and continue later. Already-labeled images are skipped automatically.

---

## CSV output

`output/annotations.csv` columns:

| Column | Meaning |
|---|---|
| `image_id` | Stable id for the image |
| `filename` | File name |
| `relative_path` | Path inside the dataset (e.g. `ev/photo.jpg`) |
| `source_folder` | Folder the image came from (`ev` or `ice`) — **not** your label |
| `label` | Your decision: `ev`, `ice`, or `skip` |
| `annotator` | Name you entered |
| `labeled_at_utc` | Timestamp (UTC) |

> Important: `source_folder` is where the image was stored before review. Your actual decision is always in the **`label`** column.

---

## Putting images into the app

### Option A — shared package (recommended for annotators)

Copy photos into:

```text
Vehicle tinder/images/ev/
Vehicle tinder/images/ice/
```

Then run `python3 app.py`.

Supported formats: `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.gif`

### Option B — project layout (developers)

If this app sits next to the scraper dataset, it will automatically use:

```text
../EV training dataset/ev/
../EV training dataset/ice/
```

The app checks `images/` first, then falls back to that dataset folder.

---

## Tips for accurate labels

- Label based on the **vehicle in the photo**, not the folder name.
- If the image is not a car, too blurry, or ambiguous → **Skip**.
- Hybrids: if it is clearly marketed / identifiable as a plug-in hybrid / EV, prefer **EV**; if unsure, **Skip**.
- Use **Undo** immediately if you mis-swipe.

---

## Troubleshooting

**Page looks plain / Start does nothing / shows 0 / 0**
- You probably opened the HTML file directly. Close that tab.
- Double-click `Start Vehicle Tinder.command` (Mac) or `Start Vehicle Tinder.bat` (Windows) instead.
- Use the browser tab that opens at `http://127.0.0.1:8765`

**Browser shows “No images found”**
- Confirm photos exist in `images/ev` and/or `images/ice`
- Click **Start labeling** again (the app re-scans the folders)

**`python3` not found / launcher says Python was not found**
- Install Python 3, or use `python app.py` on Windows after installing with PATH enabled

**Port already in use**
```bash
python3 app.py --port 8777
```

**App does not open a browser**
- Manually visit `http://127.0.0.1:8765`

**Want to start from a terminal instead**
```bash
cd "/path/to/Vehicle tinder"
python3 app.py
```

---

## Requirements

- Python 3.9+
- A modern browser (Chrome, Edge, Firefox, Safari)
- No `pip install` needed — this app uses only the Python standard library
