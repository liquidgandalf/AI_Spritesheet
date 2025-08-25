from PySide6 import QtGui, QtCore
from .project_model import GridConfig


def make_icon_pixmap(path: str, target_size: QtCore.QSize, grid: GridConfig) -> QtGui.QPixmap:
    pm = QtGui.QPixmap(path)
    if pm.isNull():
        return pm
    # Optional: scale source first
    if grid and getattr(grid, 'source_scale', 100) != 100:
        scale = max(10, min(400, int(grid.source_scale))) / 100.0
        new_w = max(1, int(pm.width() * scale))
        new_h = max(1, int(pm.height() * scale))
        pm = pm.scaled(new_w, new_h, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)

    src = pm
    if grid and grid.crop_enabled:
        # Clamp offsets so there is at least 1px available
        max_x = max(0, pm.width() - 1)
        max_y = max(0, pm.height() - 1)
        x = max(0, min(grid.offset_x, max_x))
        y = max(0, min(grid.offset_y, max_y))
        avail_w = pm.width() - x
        avail_h = pm.height() - y
        if avail_w <= 0 or avail_h <= 0:
            # Out of bounds; fall back to full image
            src = pm
        else:
            w = max(1, min(grid.tile_width, avail_w))
            h = max(1, min(grid.tile_height, avail_h))
            rect = QtCore.QRect(x, y, w, h)
            src = pm.copy(rect)
    tw = max(1, target_size.width())
    th = max(1, target_size.height())
    return src.scaled(QtCore.QSize(tw, th), QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
