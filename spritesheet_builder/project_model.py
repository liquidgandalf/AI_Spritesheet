from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import os
import json


@dataclass
class GridConfig:
    cols: int = 4
    rows: int = 4
    tile_width: int = 64
    tile_height: int = 64
    padding: int = 0
    margin: int = 0
    power_of_two: bool = True  # default ON per user preference
    crop_enabled: bool = False
    offset_x: int = 0  # top-left X of the crop box applied to all frames
    offset_y: int = 0  # top-left Y of the crop box applied to all frames
    source_scale: int = 100  # percentage scaling for source images before cropping (e.g., 100 = 1.0x)


@dataclass
class RowMeta:
    name: str = ""
    fps: int = 6
    loop_mode: str = "pingpong"  # or "loop"
    sounds: List[dict] = field(default_factory=list)  # [{name,file,trigger_frame,repeat_ms,volume}]


@dataclass
class ProjectModel:
    sheet_name: str
    source_folder: str  # path to img/raw/sheets/<sheet_name>/
    grid: GridConfig = field(default_factory=GridConfig)
    rows_meta: Dict[int, RowMeta] = field(default_factory=dict)
    # 16 engine triggers mapped to sounds: index 0..15
    # each: {"file": str, "volume": float}
    trigger_sounds: List[dict] = field(default_factory=lambda: [{"file": "", "volume": 1.0} for _ in range(16)])

    def validate(self) -> Tuple[bool, str]:
        if not self.sheet_name:
            return False, "Sheet name is required"
        if not os.path.isdir(self.source_folder):
            return False, f"Source folder not found: {self.source_folder}"
        if self.grid.cols <= 0 or self.grid.rows <= 0:
            return False, "Grid dimensions must be positive"
        if self.grid.tile_width <= 0 or self.grid.tile_height <= 0:
            return False, "Tile size must be positive"
        return True, ""

    def list_source_images(self) -> List[str]:
        """Return sorted list of PNG files (00001.png, ...)."""
        files = []
        try:
            for name in os.listdir(self.source_folder):
                if name.lower().endswith(".png"):
                    files.append(os.path.join(self.source_folder, name))
        except FileNotFoundError:
            return []
        # sort numerically if names like 00001.png
        try:
            files.sort(key=lambda p: int(os.path.splitext(os.path.basename(p))[0]))
        except ValueError:
            files.sort()
        return files

    # --- Serialization helpers ---
    def to_dict(self) -> dict:
        return {
            "sheet_name": self.sheet_name,
            "source_folder": self.source_folder,
            "grid": {
                "cols": self.grid.cols,
                "rows": self.grid.rows,
                "tile_width": self.grid.tile_width,
                "tile_height": self.grid.tile_height,
                "padding": self.grid.padding,
                "margin": self.grid.margin,
                "power_of_two": self.grid.power_of_two,
                "crop_enabled": self.grid.crop_enabled,
                "offset_x": self.grid.offset_x,
                "offset_y": self.grid.offset_y,
                "source_scale": getattr(self.grid, "source_scale", 100),
            },
            "rows_meta": {
                str(idx): {
                    "name": m.name,
                    "fps": m.fps,
                    "loop_mode": m.loop_mode,
                    "sounds": m.sounds,
                }
                for idx, m in self.rows_meta.items()
            },
            "trigger_sounds": self.trigger_sounds,
        }

    @staticmethod
    def from_dict(d: dict) -> "ProjectModel":
        grid_d = d.get("grid", {})
        grid = GridConfig(
            cols=grid_d.get("cols", 4),
            rows=grid_d.get("rows", 4),
            tile_width=grid_d.get("tile_width", 64),
            tile_height=grid_d.get("tile_height", 64),
            padding=grid_d.get("padding", 0),
            margin=grid_d.get("margin", 0),
            power_of_two=grid_d.get("power_of_two", True),
            crop_enabled=grid_d.get("crop_enabled", False),
            offset_x=grid_d.get("offset_x", 0),
            offset_y=grid_d.get("offset_y", 0),
            source_scale=grid_d.get("source_scale", 100),
        )
        rows_meta_d = d.get("rows_meta", {})
        rows_meta: Dict[int, RowMeta] = {}
        for k, v in rows_meta_d.items():
            try:
                idx = int(k)
            except (ValueError, TypeError):
                continue
            rows_meta[idx] = RowMeta(
                name=v.get("name", ""),
                fps=int(v.get("fps", 6)),
                loop_mode=v.get("loop_mode", "pingpong"),
                sounds=list(v.get("sounds", [])),
            )
        return ProjectModel(
            sheet_name=d.get("sheet_name", ""),
            source_folder=d.get("source_folder", ""),
            grid=grid,
            rows_meta=rows_meta,
            trigger_sounds=[
                {"file": str(ts.get("file", "")), "volume": float(ts.get("volume", 1.0))}
                for ts in (d.get("trigger_sounds") or [{"file": "", "volume": 1.0} for _ in range(16)])
            ][:16] + ([{"file": "", "volume": 1.0}] * max(0, 16 - len(d.get("trigger_sounds", []))))
        )

    def save_json(self, path: str, cells: List[List[str | None]] | None = None):
        data = self.to_dict()
        if cells is not None:
            data["cells"] = cells
            # Also store basenames for portability across folders
            cells_basenames: List[List[str | None]] = []
            for row in cells:
                cells_basenames.append([
                    os.path.basename(p) if isinstance(p, str) else None
                    for p in row
                ])
            data["cells_basenames"] = cells_basenames
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_json(path: str) -> Tuple["ProjectModel", List[List[str | None]] | None, List[List[str | None]] | None]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise
        proj = ProjectModel.from_dict(data)
        cells = data.get("cells")
        cells_basenames = data.get("cells_basenames")
        return proj, cells, cells_basenames
