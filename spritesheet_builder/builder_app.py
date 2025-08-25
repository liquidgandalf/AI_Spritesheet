from PySide6 import QtWidgets, QtCore
from .welcome_page import WelcomePage
from .editor_page import EditorPage
from .project_model import ProjectModel


class BuilderApp(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sprite Sheet Builder")

        self._stack = QtWidgets.QStackedWidget()
        self.setCentralWidget(self._stack)

        self.project: ProjectModel | None = None
        self.project_path: str | None = None  # current .json project file path

        self.welcome = WelcomePage()
        self.welcome.create_project_requested.connect(self._on_create_project)
        self.welcome.continue_requested.connect(self._continue_editing)
        self._stack.addWidget(self.welcome)

        self.editor = None  # type: EditorPage | None

        self._stack.setCurrentWidget(self.welcome)

        # Menubar: File (Open/Save), Settings
        self._build_menus()

    def _build_menus(self):
        mb = self.menuBar()
        file_menu = mb.addMenu("&File")
        act_open = file_menu.addAction("Open Project…")
        act_save = file_menu.addAction("Save Project")
        act_save_as = file_menu.addAction("Save Project As…")
        act_export = file_menu.addAction("Export Bundle…")
        file_menu.addSeparator()
        act_back = file_menu.addAction("Back to Welcome")

        act_open.triggered.connect(self._on_open_project)
        act_save.triggered.connect(self._on_save_project)
        act_save_as.triggered.connect(self._on_save_project_as)
        act_export.triggered.connect(self._on_export_bundle)
        act_back.triggered.connect(self._back_to_welcome)

        settings_menu = mb.addMenu("&Settings")
        act_save_settings = settings_menu.addAction("Save Settings As…")
        act_load_settings = settings_menu.addAction("Load Settings…")
        act_apply_settings_new = settings_menu.addAction("New Project From Settings…")

        act_save_settings.triggered.connect(self._on_save_settings)
        act_load_settings.triggered.connect(self._on_load_settings_apply_current)
        act_apply_settings_new.triggered.connect(self._on_new_from_settings)

    @QtCore.Slot(ProjectModel)
    def _on_create_project(self, project: ProjectModel):
        # If a project is already open, treat this as an update of settings
        if self.project and self.editor:
            # Preserve current cell placements
            cells = self.editor.grid.get_all_paths()
            # Update existing project fields
            self.project.sheet_name = project.sheet_name
            self.project.source_folder = project.source_folder
            self.project.grid = project.grid
            self.project.rows_meta = project.rows_meta
            # Reload editor with updated settings
            self.editor.load_project(self.project)
            # Re-apply previous cells (will clip to new grid size if changed)
            if cells:
                self.editor.grid.set_all_paths(cells)
                self.editor._refresh_row_preview()
        else:
            # No project open; create new
            self.project = project
            self.project_path = None
            if self.editor is None:
                self.editor = EditorPage()
                self.editor.request_back.connect(self._back_to_welcome)
                self._stack.addWidget(self.editor)
            self.editor.load_project(self.project)
        self._stack.setCurrentWidget(self.editor)

    @QtCore.Slot()
    def _back_to_welcome(self):
        # Toggle welcome button to Update if a project exists
        try:
            self.welcome.set_update_mode(self.project is not None)
            # Populate form with current project so Update preserves
            self.welcome.populate_from_project(self.project)
        except Exception:
            pass
        self._stack.setCurrentWidget(self.welcome)

    @QtCore.Slot()
    def _continue_editing(self):
        # Simply return to the editor without changing anything
        if self.editor and self.project:
            self._stack.setCurrentWidget(self.editor)

    # --- File ops ---
    def _resolve_cells(self, cells, cells_basenames, source_folder: str):
        """Return a 2D list of paths by preferring absolute cells when they exist,
        otherwise resolving via basenames within source_folder."""
        if cells is None and cells_basenames is None:
            return None
        rows = cells or cells_basenames or []
        out = []
        for r_idx, row in enumerate(rows):
            out_row = []
            for c_idx, val in enumerate(row):
                path = None
                # prefer existing absolute path
                if cells and r_idx < len(cells) and c_idx < len(cells[r_idx]):
                    cand = cells[r_idx][c_idx]
                    if isinstance(cand, str) and QtCore.QFile.exists(cand):
                        path = cand
                if path is None and cells_basenames and r_idx < len(cells_basenames) and c_idx < len(cells_basenames[r_idx]):
                    base = cells_basenames[r_idx][c_idx]
                    if isinstance(base, str):
                        cand2 = QtCore.QDir(source_folder).filePath(base)
                        if QtCore.QFile.exists(cand2):
                            path = cand2
                out_row.append(path)
            out.append(out_row)
        return out
    def _on_open_project(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Project", "", "Project Files (*.json *.plj);;All Files (*)")
        if not path:
            return
        try:
            proj, cells, cells_basenames = ProjectModel.load_json(path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Open Failed", f"Could not open project:\n{e}")
            return
        self.project = proj
        self.project_path = path
        if self.editor is None:
            self.editor = EditorPage()
            self.editor.request_back.connect(self._back_to_welcome)
            self._stack.addWidget(self.editor)
        self.editor.load_project(self.project)
        resolved = self._resolve_cells(cells, cells_basenames, self.project.source_folder)
        if resolved:
            self.editor.grid.set_all_paths(resolved)
            # Also refresh preview if a row already selected
            self.editor._refresh_row_preview()
        self._stack.setCurrentWidget(self.editor)

    def _do_save(self, path: str | None, include_cells: bool) -> bool:
        if not self.project or not self.editor:
            return False
        save_path = path or self.project_path
        if not save_path:
            save_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Project", "", "Project Files (*.json *.plj);;All Files (*)")
            if not save_path:
                return False
        cells = self.editor.grid.get_all_paths() if include_cells else None
        try:
            self.project.save_json(save_path, cells)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Save Failed", f"Could not save project:\n{e}")
            return False
        if include_cells:
            self.project_path = save_path
        return True

    def _on_save_project(self):
        ok = self._do_save(None, include_cells=True)
        if ok:
            QtWidgets.QMessageBox.information(self, "Saved", "Project saved.")

    def _on_save_project_as(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Project As", "", "Project Files (*.json *.plj);;All Files (*)")
        if not path:
            return
        ok = self._do_save(path, include_cells=True)
        if ok:
            QtWidgets.QMessageBox.information(self, "Saved", "Project saved.")

    # --- Settings ops ---
    def _on_save_settings(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Settings As", "", "Settings Files (*.json *.plj);;All Files (*)")
        if not path:
            return
        ok = self._do_save(path, include_cells=False)
        if ok:
            QtWidgets.QMessageBox.information(self, "Saved", "Settings saved.")

    def _on_load_settings_apply_current(self):
        if not self.project or not self.editor:
            QtWidgets.QMessageBox.information(self, "No Project", "Create or open a project first.")
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Settings", "", "Settings Files (*.json *.plj);;All Files (*)")
        if not path:
            return
        try:
            proj_loaded, _cells_unused, _bases_unused = ProjectModel.load_json(path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Load Failed", f"Could not load settings:\n{e}")
            return
        # Apply settings (grid + rows_meta) to current project, allow changing name/folder optionally
        # Prompt optionally for new source folder
        new_folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Optionally pick a new Source Folder (Cancel to keep current)")
        if new_folder:
            self.project.source_folder = new_folder
        # Prompt optionally for new sheet name
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Sheet Name", "Enter new sheet name (leave as-is to keep):", text=self.project.sheet_name)
        if ok and new_name.strip():
            self.project.sheet_name = new_name.strip()
        # Apply grid + rows meta
        self.project.grid = proj_loaded.grid
        self.project.rows_meta = proj_loaded.rows_meta
        # Refresh editor visuals
        self.editor.load_project(self.project)
        QtWidgets.QMessageBox.information(self, "Settings Applied", "Settings applied to current project.")

    def _on_new_from_settings(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "New Project From Settings", "", "Settings Files (*.json *.plj);;All Files (*)")
        if not path:
            return
        try:
            proj_loaded, _ = ProjectModel.load_json(path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Load Failed", f"Could not load settings:\n{e}")
            return
        # Ask for folder and name
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Source Folder for New Project")
        if not folder:
            return
        name, ok = QtWidgets.QInputDialog.getText(self, "Sheet Name", "Enter sheet name:", text=proj_loaded.sheet_name or "")
        if not ok or not name.strip():
            return
        new_proj = ProjectModel(sheet_name=name.strip(), source_folder=folder, grid=proj_loaded.grid, rows_meta=proj_loaded.rows_meta)
        ok_valid, msg = new_proj.validate()
        if not ok_valid:
            QtWidgets.QMessageBox.warning(self, "Invalid Project", msg)
            return
        self._on_create_project(new_proj)

    # --- Export ---
    def _on_export_bundle(self):
        if not self.project or not self.editor:
            QtWidgets.QMessageBox.information(self, "No Project", "Create or open a project first.")
            return
        try:
            from . import exporter
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Exporter Error", f"Failed to import exporter: {e}")
            return
        cells = self.editor.grid.get_all_paths()
        try:
            exporter.export_bundle(self, self.project, cells)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Export Failed", str(e))
