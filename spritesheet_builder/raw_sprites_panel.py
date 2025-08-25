from PySide6 import QtWidgets, QtCore, QtGui
import os
from .image_utils import make_icon_pixmap


class RawSpritesPanel(QtWidgets.QListWidget):
    selected_path_changed = QtCore.Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.setIconSize(QtCore.QSize(96, 96))
        # Use Fixed layout to prevent relayout scroll jumps
        self.setResizeMode(QtWidgets.QListView.ResizeMode.Fixed)
        self.setMovement(QtWidgets.QListView.Movement.Static)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragOnly)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setUniformItemSizes(True)
        self.setWrapping(True)
        self._update_grid_metrics()
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setSpacing(6)
        self._folder = None
        self._grid = None
        # Use default autoscroll/drag behavior of QListWidget
        self._pressed_item: QtWidgets.QListWidgetItem | None = None
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def load_folder(self, folder: str, grid=None):
        self.clear()
        self._folder = folder
        self._grid = grid
        if not folder or not os.path.isdir(folder):
            return
        files = [f for f in os.listdir(folder) if f.lower().endswith('.png')]
        # numeric sort when possible
        try:
            files.sort(key=lambda n: int(os.path.splitext(n)[0]))
        except ValueError:
            files.sort()
        for name in files:
            path = os.path.join(folder, name)
            item = QtWidgets.QListWidgetItem(name)
            pm = make_icon_pixmap(path, self.iconSize(), self._grid) if self._grid else QtGui.QPixmap(path).scaled(self.iconSize(), QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
            if not pm.isNull():
                item.setIcon(QtGui.QIcon(pm))
            item.setData(QtCore.Qt.ItemDataRole.UserRole, path)
            self.addItem(item)

    # Provide file URL(s) for the selected item so drops work without custom drag code
    def mimeData(self, items: list[QtWidgets.QListWidgetItem]) -> QtCore.QMimeData:
        mime = QtCore.QMimeData()
        urls: list[QtCore.QUrl] = []
        for it in items:
            path = it.data(QtCore.Qt.ItemDataRole.UserRole)
            if path:
                urls.append(QtCore.QUrl.fromLocalFile(path))
        if not urls and self.currentItem():
            path = self.currentItem().data(QtCore.Qt.ItemDataRole.UserRole)
            if path:
                urls.append(QtCore.QUrl.fromLocalFile(path))
        if urls:
            mime.setUrls(urls)
        return mime

    def setIconSize(self, size: QtCore.QSize) -> None:
        super().setIconSize(size)
        self._update_grid_metrics()

    def _update_grid_metrics(self):
        # Ensure a stable grid so scrolling/selection doesn’t cause relayout jumps
        sz = self.iconSize()
        # Add padding for label height and spacing
        grid_w = max(32, sz.width() + 16)
        grid_h = max(32, sz.height() + 28)
        self.setGridSize(QtCore.QSize(grid_w, grid_h))

    # Temporarily suppress scrollToItem to prevent jump-to-top during selection/drag
    def scrollToItem(self, item: QtWidgets.QListWidgetItem, hint: QtWidgets.QAbstractItemView.ScrollHint = QtWidgets.QAbstractItemView.ScrollHint.EnsureVisible) -> None:
        return

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        # Make sure the item under the cursor becomes current immediately
        it = self.itemAt(event.pos())
        if it is not None:
            self.setCurrentItem(it, QtCore.QItemSelectionModel.ClearAndSelect)
        super().mousePressEvent(event)

    def _on_selection_changed(self):
        # Temporarily do nothing to avoid any external side-effects while we stabilize selection behavior
        return

    def highlight_by_path(self, path: str):
        if not path:
            return
        for i in range(self.count()):
            it = self.item(i)
            if it.data(QtCore.Qt.ItemDataRole.UserRole) == path:
                self.setCurrentItem(it)
                self.scrollToItem(it, QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter)
                break

    def set_grid_config(self, grid):
        """Update grid config reference and refresh icons to apply cropping."""
        self._grid = grid
        # refresh icons
        for i in range(self.count()):
            it = self.item(i)
            path = it.data(QtCore.Qt.ItemDataRole.UserRole)
            pm = make_icon_pixmap(path, self.iconSize(), self._grid)
            if not pm.isNull():
                it.setIcon(QtGui.QIcon(pm))
