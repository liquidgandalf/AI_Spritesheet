# AI Spritesheet Builder – How To

This guide explains how to use the editor to build sprite sheets, preview animations, and auto-populate grid cells. It also outlines the planned export bundle and sound support.

## 1) Setup
- Create and activate venv (optional):
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
- Launch the app:
  ```bash
  python -m spritesheet_builder.builder_app
  ```

## 2) Create or Continue a Project
- Welcome screen:
  - Choose Source Folder (PNG frames).
  - Set Grid (Cols, Rows, Tile Width/Height). Power-of-two can be kept on.
  - Create Project ▶ to start.
- If a project is already open, you can use Continue Editing ▶ to return to the editor without losing the current grid.

## 3) Editor Overview
- Left: `Grid` where you place frames into cells.
- Right: `Row Preview` and `Raw Sprites` list.
- Bottom: FPS and Loop controls for the selected row, Play/Stop preview.
- Auto Populate (per row) section below with per-row controls.

## 4) Loading Raw Sprites
- The `Raw Sprites` list displays PNGs from your source folder.
- You can adjust crop/scale via Crop / Align… to define how frames are cut from source images.

## 5) Placing Frames in the Grid
- Drag PNGs from `Raw Sprites` and drop onto grid cells.
- Right-click a cell → Clear Cell to remove an image.
- Click the first column in a row to “select” that row and tint it (used for preview controls).

## 6) Row Preview and Playback
- Select a row in the grid to preview it on the right.
- Controls:
  - FPS: playback speed (1–60).
  - Loop: choose `pingpong` or `loop`.
  - ▶ Play Row / ■ Stop to control playback.
- Behavior:
  - Loop: cycles 0→N-1.
  - Pingpong: cycles 0→…→N-1→…→0.

## 7) Auto Populate (Per Row)
- Each grid row has its own controls:
  - Name field (e.g., "idle", "attack").
  - Start: numeric value (index into source images to start from).
  - Step: numeric value for how many images to advance per cell (min 1).
  - Fill Row: fills that row according to Start and Step.
- Auto-fill on change: when enabled, changing Start/Step immediately refills the row.

## 8) Crop / Align (Global)
- Click Crop / Align… to open the crop/align dialog using an example image from your source folder.
- Set offsets (top-left) and scale to crop each source image into a tile.
- These settings affect how thumbnails are generated and how the final sheet will be composed.

## 9) Per-row Metadata
- Row Name, FPS, and Loop Mode are stored per row and persist with the project.
- This metadata is used by preview and will be included in the export bundle.

## 10) Export (Planned)
The Export feature will generate a drop-in ZIP bundle:
- spritesheet.png – the composed grid image.
- meta.json – rows, frames, fps, loop mode, and (future) sound triggers.
- python_helper.py – helper to load meta, animate frames, and emit sound events.
- sounds/ – optional folder for any attached sounds.

### Proposed meta.json (example)
```json
{
  "sheet_name": "EnemyName",
  "image": "spritesheet.png",
  "grid": {
    "cols": 6,
    "rows": 4,
    "tile_width": 128,
    "tile_height": 128,
    "padding": 0,
    "margin": 0,
    "power_of_two": true,
    "crop_enabled": true,
    "offset_x": 2,
    "offset_y": 6,
    "source_scale": 100
  },
  "rows": [
    {
      "name": "idle",
      "fps": 6,
      "loop_mode": "pingpong",
      "frames": [[0,0,128,128],[128,0,128,128]]
    },
    {
      "name": "attack",
      "fps": 10,
      "loop_mode": "loop",
      "frames": [[0,128,128,128],[128,128,128,128]]
    }
  ],
  "sounds": []
}
```

## 11) Python Usage (Planned Helper)
A minimal helper for animation and sound triggers (engine-agnostic):
```python
from bundle_helper import load_bundle, Animator

image_path, anims, sounds_map = load_bundle("EnemyName")
row = anims["idle"]
anim = Animator(row["frames"], row["fps"], row["loop_mode"], row.get("sounds", []))

# in game loop (dt_ms = milliseconds since last frame)
frame_rect, sound_events = anim.advance(dt_ms)
# draw spritesheet subrect = frame_rect
# for e in sound_events: play sounds_map[e["name"]] at volume e.get("volume",1.0)
```

## 12) Sound Triggers (Planned)
Per-row sound entries, each with:
- name, file (relative), trigger_frame (0-based cell index), repeat_ms (0=no repeat), volume (0..1), optional pitch.
- The helper will emit sound events when the animation reaches the specified frame; if repeat_ms > 0, it will re-emit at that interval while the animation remains active.

## 13) Tips & Troubleshooting
- If raw thumbnails look misaligned, revisit Crop / Align and adjust offsets and scale.
- Auto-fill only works when the source folder has PNGs; Start must be within the list size.
- FPS and Loop changes apply to the currently selected row.
- Ensure row names are unique if your game references animations by name.

## 14) Roadmap
- Export ZIP bundle with spritesheet.png, meta.json, python_helper.py, sounds/.
- Per-row sounds UI and bundle inclusion.
- Optional: grid templates, selection sync options, multi-row autofill patterns.
