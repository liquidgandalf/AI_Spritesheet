# AI Spritesheet Builder (WIP)

> Status: Work In Progress. Not ready for general use yet.

A desktop app (PySide6/Qt) for organizing images and exporting them into sprite sheets.

## Features (so far)
- Basic UI scaffold using PySide6 (`spritesheet_builder/`)
- Load/preview rows and export utilities (work in progress)

## Requirements
- Python 3.10+
- See `requirements.txt`:
  - PySide6>=6.6
  - Pillow>=10.0.0

## Quick start
```bash
# clone
git clone git@github.com:liquidgandalf/AI_Spritesheet.git
cd AI_Spritesheet

# optional: create a virtualenv
python3 -m venv .venv
source .venv/bin/activate

# install deps
pip install -r requirements.txt

# run the app
python -m spritesheet_builder.builder_app  # if there is a __main__
# or just run main.py
python main.py
```

The entry point `main.py` creates a Qt application and shows the main window `BuilderApp` from `spritesheet_builder/builder_app.py`.

## Project layout
```
AI_Spritesheet/
├─ main.py
├─ requirements.txt
├─ spritesheet_builder/
│  ├─ builder_app.py
│  ├─ exporter.py
│  ├─ row_preview.py
│  └─ ...
└─ img/ (your assets)
```

## Roadmap / Known gaps
- UI/UX polish
- Robust image import pipeline
- Export settings and presets
- Better error handling and tests

## Contributing
This is an early-stage project. Issues/PRs are welcome, but expect breaking changes.

## License
TBD
