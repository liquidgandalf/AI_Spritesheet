from PySide6 import QtWidgets, QtCore, QtGui
from .project_model import ProjectModel
import os
from .image_utils import make_icon_pixmap


ROLE_PATH = QtCore.Qt.ItemDataRole.UserRole + 1


class GridWidget(QtWidgets.QTableWidget):
    selected_path_changed = QtCore.Signal(str)
    row_selected = QtCore.Signal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: ProjectModel | None = None
        self._tinted_row: int | None = None
        self.setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DropOnly)
        self.setDefaultDropAction(QtCore.Qt.DropAction.CopyAction)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectItems)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(True)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self.itemSelectionChanged.connect(self._on_item_selection_changed)
        self.itemClicked.connect(self._on_item_clicked)

    def configure(self, project: ProjectModel):
        self.project = project
        self.clear()
        self.setRowCount(project.grid.rows)
        self.setColumnCount(project.grid.cols)

        tile_w = project.grid.tile_width
        tile_h = project.grid.tile_height
        # Use actual tile size within sensible bounds so thumbnails aren't tiny
        cell_w = max(64, min(tile_w, 256))
        cell_h = max(64, min(tile_h, 256))
        for c in range(project.grid.cols):
            self.setColumnWidth(c, cell_w)
        for r in range(project.grid.rows):
            self.setRowHeight(r, cell_h)
        # Ensure icons use most of the cell
        self.setIconSize(QtCore.QSize(cell_w - 2, cell_h - 2))

        for r in range(project.grid.rows):
            for c in range(project.grid.cols):
                item = QtWidgets.QTableWidgetItem()
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                item.setData(ROLE_PATH, None)
                item.setSizeHint(QtCore.QSize(cell_w, cell_h))
                self.setItem(r, c, item)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if self._has_image_path(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        if self._has_image_path(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent):
        path = self._extract_path(event.mimeData())
        if path and os.path.isfile(path):
            pos = event.position().toPoint()
            row = self.rowAt(pos.y())
            col = self.columnAt(pos.x())
            if row >= 0 and col >= 0:
                self._set_cell_image(row, col, path)
                # Notify listeners: selection path changed (for syncing) and
                # re-fire row_selected if this row is currently tinted to refresh previews
                try:
                    self.selected_path_changed.emit(path)
                except Exception:
                    pass
                if self._tinted_row is not None and self._tinted_row == row:
                    try:
                        self.row_selected.emit(row)
                    except Exception:
                        pass
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def _set_cell_image(self, row: int, col: int, path: str):
        if not self.project:
            return
        item = self.item(row, col)
        if not item:
            item = QtWidgets.QTableWidgetItem()
            self.setItem(row, col, item)
        item.setText("")
        item.setData(ROLE_PATH, path)
        tile_w = max(1, self.columnWidth(col) - 2)
        tile_h = max(1, self.rowHeight(row) - 2)
        pm = make_icon_pixmap(path, QtCore.QSize(tile_w, tile_h), self.project.grid if self.project else None)
        if not pm.isNull():
            item.setIcon(QtGui.QIcon(pm))
        else:
            item.setIcon(QtGui.QIcon())
            item.setText("?")

    # Public API to set a cell's image path
    def set_cell_path(self, row: int, col: int, path: str | None):
        it = self.item(row, col)
        if path:
            self._set_cell_image(row, col, path)
        else:
            if not it:
                it = QtWidgets.QTableWidgetItem()
                self.setItem(row, col, it)
            it.setIcon(QtGui.QIcon())
            it.setText("")
            it.setData(ROLE_PATH, None)

    def _on_context_menu(self, pos: QtCore.QPoint):
        index = self.indexAt(pos)
        if not index.isValid():
            return
        menu = QtWidgets.QMenu(self)
        act_clear = menu.addAction("Clear Cell")
        act = menu.exec(self.viewport().mapToGlobal(pos))
        if act == act_clear:
            item = self.item(index.row(), index.column())
            if item:
                item.setIcon(QtGui.QIcon())
                item.setText("")
                item.setData(ROLE_PATH, None)

    def _has_image_path(self, mime: QtCore.QMimeData) -> bool:
        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith('.png'):
                    return True
        if mime.hasText():
            t = mime.text()
            if t.lower().endswith('.png') and os.path.exists(t):
                return True
        return False

    def _extract_path(self, mime: QtCore.QMimeData) -> str | None:
        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith('.png'):
                    return url.toLocalFile()
        if mime.hasText():
            t = mime.text()
            if t.lower().endswith('.png') and os.path.exists(t):
                return t
        return None

    def highlight_by_path(self, path: str):
        """Select and scroll to the first cell that uses the given path.
        If multiple cells match, keep selecting the first; future: multi-select.
        """
        if not path:
            return
        self.clearSelection()
        first_item = None
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                it = self.item(r, c)
                if it and it.data(ROLE_PATH) == path:
                    first_item = it
                    break
            if first_item:
                break
        if first_item:
            self.setCurrentItem(first_item)
            self.scrollToItem(first_item, QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter)

    def _on_item_selection_changed(self):
        it = self.currentItem()
        if not it:
            return
        path = it.data(ROLE_PATH)
        if path:
            self.selected_path_changed.emit(path)

    def _on_item_clicked(self, item: QtWidgets.QTableWidgetItem):
        r = item.row()
        c = item.column()
        # Clicking first column selects entire row logically
        if c == 0:
            self._tint_row(r)
            self.row_selected.emit(r)

    def refresh_icons(self, grid_config=None):
        """Rebuild icons for all cells using current or provided grid config (for cropping)."""
        grid = grid_config if grid_config is not None else (self.project.grid if self.project else None)
        if grid is None:
            return
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                it = self.item(r, c)
                if not it:
                    continue
                path = it.data(ROLE_PATH)
                if not path:
                    continue
                tile_w = max(1, self.columnWidth(c) - 2)
                tile_h = max(1, self.rowHeight(r) - 2)
                pm = make_icon_pixmap(path, QtCore.QSize(tile_w, tile_h), grid)
                if not pm.isNull():
                    it.setIcon(QtGui.QIcon(pm))

    def _tint_row(self, row: int):
        # Clear previous
        if self._tinted_row is not None and 0 <= self._tinted_row < self.rowCount():
            for c in range(self.columnCount()):
                it = self.item(self._tinted_row, c)
                if it:
                    it.setBackground(QtGui.QBrush())
        # Apply new tint
        self._tinted_row = row
        tint = QtGui.QColor(0, 170, 255, 40)
        for c in range(self.columnCount()):
            it = self.item(row, c)
            if it:
                it.setBackground(QtGui.QBrush(tint))

    def get_row_paths(self, row: int) -> list[str]:
        paths: list[str] = []
        if row < 0 or row >= self.rowCount():
            return paths
        for c in range(self.columnCount()):
            it = self.item(row, c)
            p = it.data(ROLE_PATH) if it else None
            if p:
                paths.append(p)
        return paths

    def get_all_paths(self) -> list[list[str | None]]:
        """Return a 2D list of size rows x cols with file paths or None."""
        data: list[list[str | None]] = []
        for r in range(self.rowCount()):
            row_list: list[str | None] = []
            for c in range(self.columnCount()):
                it = self.item(r, c)
                row_list.append(it.data(ROLE_PATH) if it else None)
            data.append(row_list)
        return data

    def set_all_paths(self, data: list[list[str | None]]):
        """Populate the grid from a 2D list of paths, rebuilding icons."""
        if not data:
            return
        rows = min(self.rowCount(), len(data))
        for r in range(rows):
            cols = min(self.columnCount(), len(data[r]))
            for c in range(cols):
                p = data[r][c]
                if p:
                    self._set_cell_image(r, c, p)
                else:
                    it = self.item(r, c)
                    if it:
                        it.setIcon(QtGui.QIcon())
                        it.setText("")
                        it.setData(ROLE_PATH, None)
