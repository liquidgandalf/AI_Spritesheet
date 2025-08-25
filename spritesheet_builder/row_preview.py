from PySide6 import QtWidgets, QtCore, QtGui
from .project_model import ProjectModel
from .image_utils import make_icon_pixmap


class RowPreview(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: ProjectModel | None = None
        self.paths: list[str] = []
        self.index: int = 0
        self.fps: int = 6
        self.loop_mode: str = "pingpong"  # or "loop"
        self._direction: int = 1  # 1 forward, -1 backward for pingpong
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._advance)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.title = QtWidgets.QLabel("Row Preview")
        font = self.title.font()
        font.setBold(True)
        self.title.setFont(font)
        layout.addWidget(self.title)

        self.view = QtWidgets.QLabel()
        self.view.setAlignment(QtCore.Qt.AlignCenter)
        self.view.setMinimumSize(160, 160)
        self.view.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.view.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333;")
        layout.addWidget(self.view, 1)

    def configure(self, project: ProjectModel):
        self.project = project
        # Use first available row metadata FPS if present; otherwise default to 6
        fps = 6
        loop_mode = "pingpong"
        try:
            if hasattr(project, 'rows_meta') and project.rows_meta:
                first_key = sorted(project.rows_meta.keys())[0]
                fps = int(getattr(project.rows_meta[first_key], 'fps', 6))
                loop_mode = getattr(project.rows_meta[first_key], 'loop_mode', 'pingpong')
        except Exception:
            fps = 6
        self.set_fps(fps)
        self.set_loop_mode(loop_mode)

    def set_paths(self, paths: list[str]):
        self.paths = [p for p in paths if p]
        self.index = 0
        self._direction = 1
        self._render()
        self._update_timer()

    def set_fps(self, fps: int):
        self.fps = max(1, min(60, int(fps)))
        self._update_timer()

    def _update_timer(self):
        if self.paths and self.fps > 0:
            self.timer.start(int(1000 / self.fps))
        else:
            self.timer.stop()

    def _advance(self):
        if not self.paths:
            return
        n = len(self.paths)
        if n == 1:
            self._render()
            return
        if self.loop_mode == "loop":
            self.index = (self.index + 1) % n
        else:  # pingpong
            self.index += self._direction
            if self.index >= n:
                # step back in-bounds and reverse
                self.index = n - 2 if n >= 2 else 0
            if self.index < 0:
                self.index = 1 if n >= 2 else 0
            # reverse at ends
            if self.index == n - 1:
                self._direction = -1
            elif self.index == 0:
                self._direction = 1
        self._render()

    def set_loop_mode(self, mode: str):
        mode = (mode or "pingpong").lower()
        if mode not in ("loop", "pingpong"):
            mode = "pingpong"
        self.loop_mode = mode
        # reset direction so pingpong starts forward
        self._direction = 1

    # Public playback controls
    def start(self):
        self._update_timer()

    def stop(self):
        self.timer.stop()

    def _render(self):
        if not self.project or not self.paths:
            self.view.clear()
            return
        size = self.view.size()
        # Add some padding in preview
        target = QtCore.QSize(max(64, size.width() - 8), max(64, size.height() - 8))
        frame_path = self.paths[self.index]
        pm = make_icon_pixmap(frame_path, target, self.project.grid)
        if not pm.isNull():
            self.view.setPixmap(pm)
        else:
            self.view.clear()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._render()
