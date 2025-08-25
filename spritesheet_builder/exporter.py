from __future__ import annotations
from PySide6 import QtGui, QtCore, QtWidgets
from pathlib import Path
import json
import shutil
import zipfile
from .project_model import ProjectModel


def _compose_spritesheet(project: ProjectModel, cells: list[list[str | None]]) -> tuple[QtGui.QImage, list[list[QtCore.QRect]]]:
    g = project.grid
    cols, rows = g.cols, g.rows
    tw, th = g.tile_width, g.tile_height
    pad, mar = g.padding, g.margin
    sheet_w = mar * 2 + cols * tw + max(0, cols - 1) * pad
    sheet_h = mar * 2 + rows * th + max(0, rows - 1) * pad

    img = QtGui.QImage(sheet_w, sheet_h, QtGui.QImage.Format.Format_ARGB32)
    img.fill(QtCore.Qt.GlobalColor.transparent)

    painter = QtGui.QPainter(img)
    frames: list[list[QtCore.QRect]] = []

    # helper to load and prepare a tile image
    def load_tile(path: str) -> QtGui.QImage:
        src = QtGui.QImage(path)
        if src.isNull():
            return src
        # scale whole source first if requested
        scale_percent = getattr(g, 'source_scale', 100)
        if scale_percent != 100:
            s = max(10, min(400, int(scale_percent))) / 100.0
            new_w = max(1, int(src.width() * s))
            new_h = max(1, int(src.height() * s))
            src = src.scaled(new_w, new_h, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        if g.crop_enabled:
            x = max(0, min(g.offset_x, max(0, src.width() - 1)))
            y = max(0, min(g.offset_y, max(0, src.height() - 1)))
            avail_w = src.width() - x
            avail_h = src.height() - y
            if avail_w > 0 and avail_h > 0:
                w = max(1, min(tw, avail_w))
                h = max(1, min(th, avail_h))
                src = src.copy(QtCore.QRect(x, y, w, h))
            # center if smaller than tile
            if src.width() != tw or src.height() != th:
                # scale to fit tile preserving aspect
                src = src.scaled(QtCore.QSize(tw, th), QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        else:
            # no crop: scale to fit tile preserving aspect
            src = src.scaled(QtCore.QSize(tw, th), QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        return src

    for r in range(rows):
        row_frames: list[QtCore.QRect] = []
        for c in range(cols):
            x = mar + c * (tw + pad)
            y = mar + r * (th + pad)
            rect = QtCore.QRect(x, y, tw, th)
            path = cells[r][c] if r < len(cells) and c < len(cells[r]) else None
            if path:
                tile = load_tile(str(path))
                if not tile.isNull():
                    # center within tile rect
                    dx = x + (tw - tile.width()) // 2
                    dy = y + (th - tile.height()) // 2
                    painter.drawImage(QtCore.QPoint(dx, dy), tile)
                    row_frames.append(rect)
            else:
                # empty cell -> do not add a frame entry
                pass
        frames.append(row_frames)

    painter.end()
    return img, frames


def export_bundle(parent: QtWidgets.QWidget, project: ProjectModel, cells: list[list[str | None]]) -> None:
    if not project:
        return
    ok, msg = project.validate()
    if not ok:
        QtWidgets.QMessageBox.warning(parent, "Invalid Project", msg)
        return

    # Ask for destination folder
    dest_dir = QtWidgets.QFileDialog.getExistingDirectory(parent, "Choose Export Folder")
    if not dest_dir:
        return
    dest_dir = Path(dest_dir)

    bundle_dir = dest_dir / project.sheet_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    sounds_dir = bundle_dir / "sounds"
    sounds_dir.mkdir(exist_ok=True)

    # Compose spritesheet
    sheet, frames = _compose_spritesheet(project, cells)
    sheet_path = bundle_dir / "spritesheet.png"
    sheet.save(str(sheet_path))

    # Build meta.json
    g = project.grid
    rows_meta = []
    for r in range(g.rows):
        meta = project.rows_meta.get(r)
        name = meta.name if meta and getattr(meta, 'name', None) else f"row_{r}"
        fps = int(meta.fps) if meta else 6
        loop_mode = meta.loop_mode if meta else "pingpong"
        sounds = list(meta.sounds) if meta and getattr(meta, 'sounds', None) else []
        # For sounds in rows, rewrite file to relative if possible and copy into sounds/
        new_sounds = []
        for s in sounds:
            s = dict(s)
            f = s.get("file", "")
            if f:
                src_path = Path(f)
                if src_path.exists():
                    dst = sounds_dir / src_path.name
                    try:
                        if dst.resolve() != src_path.resolve():
                            shutil.copy2(src_path, dst)
                    except Exception:
                        pass
                    s["file"] = f"sounds/{dst.name}"
            new_sounds.append(s)
        # Frames: only include non-empty positions from composed frames
        rects = []
        for rect in frames[r]:
            rects.append([rect.x(), rect.y(), rect.width(), rect.height()])
        rows_meta.append({
            "name": name,
            "fps": fps,
            "loop_mode": loop_mode,
            "frames": rects,
            "sounds": new_sounds,
        })

    # Global trigger sounds 0..15 -> copy and relativize
    trigger_sounds = []
    for i, ts in enumerate(project.trigger_sounds):
        ts = dict(ts or {})
        f = ts.get("file", "")
        if f:
            src_path = Path(f)
            if src_path.exists():
                dst = sounds_dir / src_path.name
                try:
                    if dst.resolve() != src_path.resolve():
                        shutil.copy2(src_path, dst)
                except Exception:
                    pass
                ts["file"] = f"sounds/{dst.name}"
        ts["volume"] = float(ts.get("volume", 1.0))
        trigger_sounds.append(ts)
    # ensure length 16
    if len(trigger_sounds) < 16:
        trigger_sounds.extend({"file": "", "volume": 1.0} for _ in range(16 - len(trigger_sounds)))
    trigger_sounds = trigger_sounds[:16]

    meta = {
        "sheet_name": project.sheet_name,
        "image": "spritesheet.png",
        "grid": {
            "cols": g.cols,
            "rows": g.rows,
            "tile_width": g.tile_width,
            "tile_height": g.tile_height,
            "padding": g.padding,
            "margin": g.margin,
            "power_of_two": g.power_of_two,
            "crop_enabled": g.crop_enabled,
            "offset_x": g.offset_x,
            "offset_y": g.offset_y,
            "source_scale": getattr(g, 'source_scale', 100),
        },
        "rows": rows_meta,
        "trigger_sounds": trigger_sounds,
    }

    (bundle_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # python_helper.py
    helper_code = _python_helper_code()
    (bundle_dir / "python_helper.py").write_text(helper_code, encoding="utf-8")

    # Zip bundle
    zip_path = dest_dir / f"{project.sheet_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in [sheet_path, bundle_dir / "meta.json", bundle_dir / "python_helper.py"]:
            z.write(p, p.relative_to(bundle_dir.parent))
        # include sounds
        if sounds_dir.exists():
            for f in sounds_dir.iterdir():
                if f.is_file():
                    z.write(f, f.relative_to(bundle_dir.parent))

    QtWidgets.QMessageBox.information(parent, "Export Complete", f"Exported to:\n{zip_path}")


def _python_helper_code() -> str:
    return """# Auto-generated helper for spritesheet bundle
import json, time
from pathlib import Path

class Animator:
    def __init__(self, frames, fps=6, loop_mode="pingpong", sounds=None):
        self.frames = frames or []
        self.fps = max(1, int(fps))
        self.loop_mode = loop_mode if loop_mode in ("loop", "pingpong") else "pingpong"
        self.sounds = sounds or []
        self.idx = 0
        self._dir = 1
        self._accum = 0.0
        self._last_play_ms = {s.get("name", str(i)): -1_000_000 for i, s in enumerate(self.sounds)}

    def set_animation(self, frames, fps=None, loop_mode=None, sounds=None):
        self.frames = frames or []
        if fps is not None: self.fps = max(1, int(fps))
        if loop_mode is not None: self.loop_mode = loop_mode if loop_mode in ("loop","pingpong") else "pingpong"
        if sounds is not None: self.sounds = sounds
        self.idx = 0
        self._dir = 1
        self._accum = 0.0
        self._last_play_ms = {s.get("name", str(i)): -1_000_000 for i, s in enumerate(self.sounds)}

    def _advance_one(self):
        n = len(self.frames)
        if n <= 1: return
        if self.loop_mode == "loop":
            self.idx = (self.idx + 1) % n
        else:
            self.idx += self._dir
            if self.idx >= n:
                self.idx = n - 2 if n >= 2 else 0
            if self.idx < 0:
                self.idx = 1 if n >= 2 else 0
            if self.idx == n - 1: self._dir = -1
            elif self.idx == 0: self._dir = 1

    def advance(self, dt_ms):
        self._accum += float(dt_ms)
        interval = 1000.0 / self.fps
        while self._accum >= interval:
            self._accum -= interval
            self._advance_one()
        frame = self.frames[self.idx] if self.frames else None
        now = time.monotonic() * 1000.0
        events = []
        for s in self.sounds:
            name = s.get("name") or "sound"
            trig = int(s.get("trigger_frame", 0))
            rep = int(s.get("repeat_ms", 0))
            vol = float(s.get("volume", 1.0))
            if trig == self.idx:
                last = self._last_play_ms.get(name, -1_000_000)
                if rep == 0:
                    if now - last > 50.0:
                        events.append({"name": name, "file": s.get("file", ""), "volume": vol})
                        self._last_play_ms[name] = now
                else:
                    if now - last >= rep:
                        events.append({"name": name, "file": s.get("file", ""), "volume": vol})
                        self._last_play_ms[name] = now
        return frame, events

def load_bundle(bundle_dir):
    bundle_dir = Path(bundle_dir)
    meta = json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))
    image_path = bundle_dir / meta["image"]
    animations = {}
    for row in meta.get("rows", []):
        name = row.get("name") or "row"
        animations[name] = {
            "frames": [tuple(f) for f in row.get("frames", [])],
            "fps": int(row.get("fps", 6)),
            "loop_mode": row.get("loop_mode", "pingpong"),
            "sounds": row.get("sounds", []),
        }
    trigger_sounds = meta.get("trigger_sounds", [{"file": "", "volume": 1.0} for _ in range(16)])
    # Return absolute paths for sound files
    trig_map = []
    for ts in trigger_sounds[:16]:
        f = ts.get("file", "")
        trig_map.append({"file": str((bundle_dir / f).resolve()) if f else "", "volume": float(ts.get("volume", 1.0))})
    return image_path, animations, trig_map
"""
