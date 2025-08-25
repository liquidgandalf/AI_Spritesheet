from PySide6 import QtWidgets, QtCore
from .project_model import ProjectModel, GridConfig, RowMeta
import os


class WelcomePage(QtWidgets.QWidget):
    create_project_requested = QtCore.Signal(ProjectModel)
    continue_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def set_update_mode(self, update: bool):
        """Toggle button text to reflect updating existing project cells."""
        if hasattr(self, "create_btn") and self.create_btn:
            self.create_btn.setText("Update Cells ▶" if update else "Create Project ▶")
        if hasattr(self, "continue_btn") and self.continue_btn:
            self.continue_btn.setVisible(update)

    def populate_from_project(self, project: ProjectModel | None):
        if not project:
            return
        # Fill form fields from existing project so pressing Update preserves settings
        self.source_edit.setText(project.source_folder)
        self.sheet_name_edit.setText(project.sheet_name)
        self.cols_spin.setValue(project.grid.cols)
        self.rows_spin.setValue(project.grid.rows)
        self.tile_w.setValue(project.grid.tile_width)
        self.tile_h.setValue(project.grid.tile_height)
        self.pow2_check.setChecked(project.grid.power_of_two)
        # If there is a row 0 meta, use its fps/loop as defaults
        meta0 = project.rows_meta.get(0)
        if meta0:
            self.fps_spin.setValue(max(1, min(60, int(getattr(meta0, 'fps', 6)))))
            idx = 0 if getattr(meta0, 'loop_mode', 'pingpong') == 'pingpong' else 1
            self.loop_mode_combo.setCurrentIndex(idx)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Create / Open Project")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        form = QtWidgets.QFormLayout()

        # Source folder picker
        self.source_edit = QtWidgets.QLineEdit()
        browse_btn = QtWidgets.QPushButton("Browse…")
        browse_layout = QtWidgets.QHBoxLayout()
        browse_layout.addWidget(self.source_edit)
        browse_layout.addWidget(browse_btn)
        browse_widget = QtWidgets.QWidget()
        browse_widget.setLayout(browse_layout)
        form.addRow("Source folder (img/raw/sheets/<sheet_name>/):", browse_widget)

        browse_btn.clicked.connect(self._on_browse)

        # Sheet name
        self.sheet_name_edit = QtWidgets.QLineEdit()
        form.addRow("Sheet name:", self.sheet_name_edit)

        # Add the form to the main layout so fields are visible
        layout.addLayout(form)

        # Grid config
        grid_box = QtWidgets.QGroupBox("Grid Configuration")
        grid_form = QtWidgets.QFormLayout(grid_box)

        self.cols_spin = QtWidgets.QSpinBox()
        self.cols_spin.setRange(1, 512)
        self.cols_spin.setValue(4)
        self.rows_spin = QtWidgets.QSpinBox()
        self.rows_spin.setRange(1, 512)
        self.rows_spin.setValue(4)

        colrow = QtWidgets.QHBoxLayout()
        colrow.addWidget(QtWidgets.QLabel("Cols:"))
        colrow.addWidget(self.cols_spin)
        colrow.addSpacing(12)
        colrow.addWidget(QtWidgets.QLabel("Rows:"))
        colrow.addWidget(self.rows_spin)
        crw = QtWidgets.QWidget()
        crw.setLayout(colrow)
        grid_form.addRow("Grid size:", crw)

        # Tile size with presets
        self.tile_w = QtWidgets.QSpinBox()
        self.tile_w.setRange(1, 4096)
        self.tile_w.setValue(64)
        self.tile_h = QtWidgets.QSpinBox()
        self.tile_h.setRange(1, 4096)
        self.tile_h.setValue(64)

        size_row = QtWidgets.QHBoxLayout()
        size_row.addWidget(QtWidgets.QLabel("W:"))
        size_row.addWidget(self.tile_w)
        size_row.addSpacing(12)
        size_row.addWidget(QtWidgets.QLabel("H:"))
        size_row.addWidget(self.tile_h)

        # Preset buttons
        preset_layout = QtWidgets.QHBoxLayout()
        for label, w, h in [("64x64",64,64),("64x128",64,128),("128x256",128,256)]:
            btn = QtWidgets.QPushButton(label)
            btn.clicked.connect(lambda checked=False, a=(w,h): self._apply_preset(a))
            preset_layout.addWidget(btn)
        size_row.addSpacing(12)
        size_row.addLayout(preset_layout)
        sizew = QtWidgets.QWidget()
        sizew.setLayout(size_row)
        grid_form.addRow("Tile size:", sizew)

        # Power of two toggle (default ON)
        self.pow2_check = QtWidgets.QCheckBox("Force power-of-two export (next POT)")
        self.pow2_check.setChecked(True)
        grid_form.addRow("Atlas size:", self.pow2_check)

        layout.addWidget(grid_box)

        # Animation defaults
        anim_box = QtWidgets.QGroupBox("Animation Defaults")
        anim_form = QtWidgets.QFormLayout(anim_box)
        self.fps_spin = QtWidgets.QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(6)
        self.loop_mode_combo = QtWidgets.QComboBox()
        self.loop_mode_combo.addItems(["pingpong", "loop"])
        anim_form.addRow("FPS:", self.fps_spin)
        anim_form.addRow("Loop mode:", self.loop_mode_combo)
        layout.addWidget(anim_box)

        # Create/Update button
        self.create_btn = QtWidgets.QPushButton("Create Project ▶")
        self.create_btn.clicked.connect(self._create_project)
        layout.addWidget(self.create_btn)
        # Continue button (only visible when updating existing project)
        self.continue_btn = QtWidgets.QPushButton("Continue Editing ▶")
        self.continue_btn.clicked.connect(self.continue_requested)
        self.continue_btn.setVisible(False)
        layout.addWidget(self.continue_btn)
        layout.addStretch(1)

    def _apply_preset(self, size):
        w, h = size
        self.tile_w.setValue(w)
        self.tile_h.setValue(h)

    def _on_browse(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if path:
            self.source_edit.setText(path)
            # Guess sheet name from folder name
            base = os.path.basename(os.path.normpath(path))
            if not self.sheet_name_edit.text():
                self.sheet_name_edit.setText(base)

    def _create_project(self):
        source = self.source_edit.text().strip()
        sheet = self.sheet_name_edit.text().strip()
        grid = GridConfig(
            cols=self.cols_spin.value(),
            rows=self.rows_spin.value(),
            tile_width=self.tile_w.value(),
            tile_height=self.tile_h.value(),
            power_of_two=self.pow2_check.isChecked(),
        )
        project = ProjectModel(sheet_name=sheet, source_folder=source, grid=grid)
        ok, msg = project.validate()
        if not ok:
            QtWidgets.QMessageBox.warning(self, "Invalid Project", msg)
            return
        self.create_project_requested.emit(project)
