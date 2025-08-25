from PySide6 import QtWidgets, QtCore, QtGui
from .project_model import ProjectModel
from .grid_widget import GridWidget
from .raw_sprites_panel import RawSpritesPanel
from .crop_dialog import CropAlignDialog
from .row_preview import RowPreview


class EditorPage(QtWidgets.QWidget):
    request_back = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: ProjectModel | None = None
        # Guards to avoid selection sync feedback loops
        self._syncing_from_raw = False
        self._syncing_from_grid = False
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Top bar: back, sheet name, grid summary
        top = QtWidgets.QHBoxLayout()
        self.back_btn = QtWidgets.QPushButton("◀ Back")
        self.back_btn.clicked.connect(self.request_back)
        top.addWidget(self.back_btn)
        top.addSpacing(12)
        self.title_label = QtWidgets.QLabel("Sheet: -")
        font = self.title_label.font()
        font.setPointSize(12)
        font.setBold(True)
        self.title_label.setFont(font)
        top.addWidget(self.title_label)
        top.addStretch(1)
        self.crop_btn = QtWidgets.QPushButton("Crop / Align…")
        self.crop_btn.setToolTip("Draw a tile-sized box over an example image and apply offsets to all frames")
        self.crop_btn.clicked.connect(self._on_crop_align)
        top.addWidget(self.crop_btn)
        layout.addLayout(top)

        # Splitter: left grid, right raw list
        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)

        self.grid = GridWidget()
        splitter.addWidget(self.grid)

        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        # Live row preview area
        self.row_preview = RowPreview()
        right_layout.addWidget(self.row_preview)
        right_layout.addSpacing(6)
        right_layout.addWidget(QtWidgets.QLabel("Raw Sprites"))
        self.raw_panel = RawSpritesPanel()
        right_layout.addWidget(self.raw_panel)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter, 1)

        # Bottom bar: simple row controls placeholder
        bottom = QtWidgets.QHBoxLayout()
        bottom.addWidget(QtWidgets.QLabel("FPS:"))
        self.fps_spin = QtWidgets.QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(6)
        bottom.addWidget(self.fps_spin)
        bottom.addSpacing(12)
        self.loop_combo = QtWidgets.QComboBox()
        self.loop_combo.addItems(["pingpong", "loop"])
        bottom.addWidget(QtWidgets.QLabel("Loop:"))
        bottom.addWidget(self.loop_combo)
        bottom.addStretch(1)
        self.play_btn = QtWidgets.QPushButton("▶ Play Row")
        bottom.addWidget(self.play_btn)
        self.stop_btn = QtWidgets.QPushButton("■ Stop")
        bottom.addWidget(self.stop_btn)
        layout.addLayout(bottom)

        # Auto populate controls (per-row)
        auto_box = QtWidgets.QGroupBox("Auto Populate (per row)")
        auto_v = QtWidgets.QVBoxLayout(auto_box)
        header = QtWidgets.QHBoxLayout()
        self.auto_enable = QtWidgets.QCheckBox("Auto-fill on change")
        header.addWidget(self.auto_enable)
        self.fill_all_btn = QtWidgets.QPushButton("Fill All Rows")
        header.addWidget(self.fill_all_btn)
        header.addStretch(1)
        auto_v.addLayout(header)

        # Scroll area with one control row per grid row
        self.auto_scroll = QtWidgets.QScrollArea()
        self.auto_scroll.setWidgetResizable(True)
        self.auto_rows_container = QtWidgets.QWidget()
        self.auto_rows_layout = QtWidgets.QVBoxLayout(self.auto_rows_container)
        self.auto_rows_layout.setContentsMargins(4, 4, 4, 4)
        self.auto_rows_layout.setSpacing(6)
        self.auto_scroll.setWidget(self.auto_rows_container)
        auto_v.addWidget(self.auto_scroll)

        layout.addWidget(auto_box)

        # Engine triggers (0..15)
        trig_box = QtWidgets.QGroupBox("Engine Trigger Sounds (0..15)")
        trig_v = QtWidgets.QVBoxLayout(trig_box)
        self.trig_grid = QtWidgets.QGridLayout()
        self.trig_grid.setHorizontalSpacing(6)
        self.trig_grid.setVerticalSpacing(4)
        self._trigger_widgets = []  # list of dicts per index
        # header row
        self.trig_grid.addWidget(QtWidgets.QLabel("Idx"), 0, 0)
        self.trig_grid.addWidget(QtWidgets.QLabel("File"), 0, 1)
        self.trig_grid.addWidget(QtWidgets.QLabel(""), 0, 2)
        self.trig_grid.addWidget(QtWidgets.QLabel("Vol"), 0, 3)
        for i in range(16):
            idx_lbl = QtWidgets.QLabel(str(i))
            f_edit = QtWidgets.QLineEdit()
            f_edit.setPlaceholderText("file…")
            f_edit.setReadOnly(True)
            browse = QtWidgets.QPushButton("Browse…")
            vol = QtWidgets.QDoubleSpinBox()
            vol.setRange(0.0, 1.0)
            vol.setSingleStep(0.05)
            vol.setValue(1.0)

            self.trig_grid.addWidget(idx_lbl, i + 1, 0)
            self.trig_grid.addWidget(f_edit, i + 1, 1)
            self.trig_grid.addWidget(browse, i + 1, 2)
            self.trig_grid.addWidget(vol, i + 1, 3)

            def make_on_browse(ii=i, edit=f_edit):
                def _handler():
                    if not self.project:
                        return
                    dlg = QtWidgets.QFileDialog(self, f"Select Trigger {ii} Sound", self.project.source_folder if self.project else "", "Audio Files (*.wav *.ogg *.mp3);;All Files (*)")
                    dlg.setFileMode(QtWidgets.QFileDialog.ExistingFile)
                    if dlg.exec() == QtWidgets.QDialog.Accepted:
                        path = dlg.selectedFiles()[0]
                        edit.setText(path)
                        try:
                            self.project.trigger_sounds[ii]["file"] = path
                        except Exception:
                            pass
                return _handler
            browse.clicked.connect(make_on_browse())

            def make_on_vol(ii=i):
                def _on(val: float):
                    if not self.project:
                        return
                    try:
                        self.project.trigger_sounds[ii]["volume"] = float(val)
                    except Exception:
                        pass
                return _on
            vol.valueChanged.connect(make_on_vol())

            def make_on_edit_changed(ii=i):
                def _on(text: str):
                    if not self.project:
                        return
                    try:
                        self.project.trigger_sounds[ii]["file"] = text
                    except Exception:
                        pass
                return _on
            f_edit.textChanged.connect(make_on_edit_changed())

            self._trigger_widgets.append({"file": f_edit, "browse": browse, "vol": vol})

        trig_v.addLayout(self.trig_grid)
        layout.addWidget(trig_box)

    def load_project(self, project: ProjectModel):
        self.project = project
        self.title_label.setText(f"Sheet: {project.sheet_name} | {project.grid.cols}x{project.grid.rows} tiles @ {project.grid.tile_width}x{project.grid.tile_height}")
        self.grid.configure(project)
        self.raw_panel.load_folder(project.source_folder, project.grid)
        self.row_preview.configure(project)
        # Adjust raw icon size to be more visible (cap for performance)
        icon_w = max(64, min(project.grid.tile_width, 192))
        icon_h = max(64, min(project.grid.tile_height, 192))
        self.raw_panel.setIconSize(QtCore.QSize(icon_w, icon_h))
        # Build per-row auto-fill controls for current grid configuration
        self._rebuild_auto_rows()
        self._sync_auto_slider_max()
        # Load trigger widgets from project
        try:
            for i, w in enumerate(self._trigger_widgets):
                ts = project.trigger_sounds[i] if i < len(project.trigger_sounds) else {"file": "", "volume": 1.0}
                try:
                    w["file"].blockSignals(True)
                    w["vol"].blockSignals(True)
                    w["file"].setText(str(ts.get("file", "")))
                    w["vol"].setValue(float(ts.get("volume", 1.0)))
                finally:
                    w["file"].blockSignals(False)
                    w["vol"].blockSignals(False)
        except Exception:
            pass

        # Temporarily disable selection synchronization between raw <-> grid
        try:
            self.raw_panel.selected_path_changed.disconnect()
        except Exception:
            pass
        # Intentionally do not sync raw -> grid on selection

        try:
            self.grid.selected_path_changed.disconnect()
        except Exception:
            pass
        # Intentionally do not sync grid -> raw on selection
        # Future: connect play/stop to preview row
        # Row preview wiring
        self.grid.row_selected.connect(self._on_row_selected)
        self.fps_spin.valueChanged.connect(self._on_fps_changed)
        self.loop_combo.currentTextChanged.connect(self._on_loop_changed)
        self.play_btn.clicked.connect(self._on_play_row)
        self.stop_btn.clicked.connect(self.row_preview.stop)

        # Auto populate wiring
        self.auto_enable.toggled.connect(self._maybe_auto_fill_all)
        self.fill_all_btn.clicked.connect(self._auto_fill_all)

    def _on_export_bundle(self):
        if not self.project:
            return
        try:
            from . import exporter
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Exporter Error", f"Failed to import exporter: {e}")
            return
        cells = self.grid.get_all_paths()
        try:
            exporter.export_bundle(self, self.project, cells)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Export Failed", str(e))

    def _on_crop_align(self):
        if not self.project:
            return
        images = self.project.list_source_images()
        if not images:
            QtWidgets.QMessageBox.information(self, "No Images", "No PNGs found in the source folder.")
            return
        g = self.project.grid
        # Pass full list so dialog can cycle and overlay; falls back internally if a string
        dlg = CropAlignDialog(images, g.tile_width, g.tile_height, g.offset_x, g.offset_y, self, scale_percent=getattr(g, 'source_scale', 100))
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            x, y = dlg.offsets()
            g.offset_x = x
            g.offset_y = y
            # propagate scale back to project
            # Save scale
            g.source_scale = dlg.scale_percent()
            # Refresh visuals
            self.raw_panel.set_grid_config(g)
            self.grid.refresh_icons(g)
            # Refresh preview if a row is selected
            self._refresh_row_preview()

    def _on_row_selected(self, row_idx: int):
        paths = self.grid.get_row_paths(row_idx)
        self.row_preview.set_paths(paths)
        # Load row meta controls
        if self.project:
            meta = self.project.rows_meta.get(row_idx)
            if meta:
                # avoid feedback signals while setting
                try:
                    self.fps_spin.blockSignals(True)
                    self.loop_combo.blockSignals(True)
                    self.fps_spin.setValue(int(meta.fps))
                    # Ensure valid index for text
                    mode = meta.loop_mode if meta.loop_mode in ("pingpong", "loop") else "pingpong"
                    self.loop_combo.setCurrentText(mode)
                finally:
                    self.fps_spin.blockSignals(False)
                    self.loop_combo.blockSignals(False)
                self.row_preview.set_fps(int(meta.fps))
                self.row_preview.set_loop_mode(mode)

    def _refresh_row_preview(self):
        # Re-apply current selection to update preview frames against new crop/scale
        it = self.grid.currentItem()
        if it:
            r = it.row()
            if self.grid._tinted_row is not None:
                r = self.grid._tinted_row
            self._on_row_selected(r)

    def _current_row_index(self) -> int | None:
        it = self.grid.currentItem()
        r = None
        if it:
            r = it.row()
        if self.grid._tinted_row is not None:
            r = self.grid._tinted_row
        return r

    def _on_fps_changed(self, val: int):
        self.row_preview.set_fps(val)
        r = self._current_row_index()
        if self.project is not None and r is not None:
            meta = self.project.rows_meta.get(r)
            if not meta:
                # lazy create meta
                from .project_model import RowMeta
                meta = RowMeta()
                self.project.rows_meta[r] = meta
            meta.fps = int(val)

    def _on_loop_changed(self, mode: str):
        mode = (mode or "pingpong").lower()
        if mode not in ("pingpong", "loop"):
            mode = "pingpong"
        self.row_preview.set_loop_mode(mode)
        r = self._current_row_index()
        if self.project is not None and r is not None:
            meta = self.project.rows_meta.get(r)
            if not meta:
                from .project_model import RowMeta
                meta = RowMeta()
                self.project.rows_meta[r] = meta
            meta.loop_mode = mode

    def _on_play_row(self):
        # Ensure preview has current row frames and settings
        r = self._current_row_index()
        if r is not None:
            paths = self.grid.get_row_paths(r)
            self.row_preview.set_paths(paths)
        self.row_preview.start()

    # --- Auto populate helpers (per-row) ---
    def _rebuild_auto_rows(self):
        # Clear existing
        while self.auto_rows_layout.count():
            item = self.auto_rows_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._auto_row_widgets = []  # list of dicts per row
        if not self.project:
            return
        rows = self.grid.rowCount()
        for r in range(rows):
            row_widget = QtWidgets.QWidget()
            h = QtWidgets.QHBoxLayout(row_widget)
            h.setContentsMargins(4, 2, 4, 2)
            # Per-row name field before the row label
            name_edit = QtWidgets.QLineEdit()
            name_edit.setPlaceholderText(f"Row {r}")
            name_edit.setFixedWidth(120)
            h.addWidget(name_edit)
            h.addWidget(QtWidgets.QLabel(f"Row {r}:"))

            start_lbl = QtWidgets.QLabel("Start")
            start = QtWidgets.QSpinBox()
            start.setRange(0, 0)  # max updated dynamically
            start.setSingleStep(1)
            start.setAccelerated(False)
            start.setFixedWidth(140)
            # Try to disable press-and-hold auto repeat on spin buttons
            for btn in start.findChildren(QtWidgets.QAbstractButton):
                try:
                    btn.setAutoRepeat(False)
                except Exception:
                    pass
            h.addWidget(start_lbl)
            h.addWidget(start)

            step_lbl = QtWidgets.QLabel("Step")
            step = QtWidgets.QSpinBox()
            step.setRange(1, 64)
            step.setSingleStep(1)
            step.setAccelerated(False)
            step.setFixedWidth(140)
            for btn in step.findChildren(QtWidgets.QAbstractButton):
                try:
                    btn.setAutoRepeat(False)
                except Exception:
                    pass
            h.addWidget(step_lbl)
            h.addWidget(step)

            fill_btn = QtWidgets.QPushButton("Fill Row")
            h.addWidget(fill_btn)
            h.addSpacing(8)

            # --- Sound controls (single entry per row for now) ---
            h.addWidget(QtWidgets.QLabel("Sound:"))
            snd_name = QtWidgets.QLineEdit()
            snd_name.setPlaceholderText("name")
            snd_name.setFixedWidth(110)
            h.addWidget(snd_name)

            snd_file = QtWidgets.QLineEdit()
            snd_file.setPlaceholderText("file…")
            snd_file.setReadOnly(True)
            snd_file.setFixedWidth(180)
            snd_browse = QtWidgets.QPushButton("Browse…")
            h.addWidget(snd_file)
            h.addWidget(snd_browse)

            h.addWidget(QtWidgets.QLabel("Trig:"))
            trig = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            trig.setRange(0, max(0, self.grid.columnCount() - 1))
            trig.setFixedWidth(100)
            trig.setTickInterval(1)
            trig.setSingleStep(1)
            trig.setPageStep(1)
            trig.setTickPosition(QtWidgets.QSlider.TickPosition.NoTicks)
            h.addWidget(trig)

            h.addWidget(QtWidgets.QLabel("Repeat ms:"))
            rep = QtWidgets.QSpinBox()
            rep.setRange(0, 600000)
            rep.setSingleStep(50)
            rep.setFixedWidth(80)
            h.addWidget(rep)

            h.addWidget(QtWidgets.QLabel("Vol:"))
            vol = QtWidgets.QDoubleSpinBox()
            vol.setRange(0.0, 1.0)
            vol.setSingleStep(0.05)
            vol.setValue(1.0)
            vol.setFixedWidth(70)
            h.addWidget(vol)

            h.addStretch(1)

            # Initialize name from meta if available
            if self.project:
                meta = self.project.rows_meta.get(r)
                if meta and getattr(meta, 'name', ""):
                    name_edit.setText(meta.name)
                # init sound if exists (use first entry only for now)
                if meta and getattr(meta, 'sounds', None):
                    s0 = meta.sounds[0] if meta.sounds else None
                    if s0:
                        snd_name.setText(str(s0.get('name', "")))
                        snd_file.setText(str(s0.get('file', "")))
                        try:
                            trig.setValue(int(s0.get('trigger_frame', 0)))
                        except Exception:
                            pass
                        try:
                            rep.setValue(int(s0.get('repeat_ms', 0)))
                        except Exception:
                            pass
                        try:
                            vol.setValue(float(s0.get('volume', 1.0)))
                        except Exception:
                            pass

            # bind events
            def on_value_changed(_=None, row_index=r, s=start, st=step):
                if self.auto_enable.isChecked():
                    self._auto_fill_row(row_index, s.value(), st.value())
            start.valueChanged.connect(on_value_changed)
            step.valueChanged.connect(on_value_changed)
            fill_btn.clicked.connect(lambda _=False, row_index=r, s=start, st=step: self._auto_fill_row(row_index, s.value(), st.value()))

            def on_name_changed(text: str, row_index=r):
                if not self.project:
                    return
                meta = self.project.rows_meta.get(row_index)
                if not meta:
                    from .project_model import RowMeta
                    meta = RowMeta()
                    self.project.rows_meta[row_index] = meta
                meta.name = text
            name_edit.textChanged.connect(on_name_changed)

            # sound persistence helpers
            def ensure_meta(row_index=r):
                if not self.project:
                    return None
                m = self.project.rows_meta.get(row_index)
                if not m:
                    from .project_model import RowMeta
                    m = RowMeta()
                    self.project.rows_meta[row_index] = m
                if not hasattr(m, 'sounds') or m.sounds is None:
                    m.sounds = []
                if not m.sounds:
                    m.sounds.append({"name": "", "file": "", "trigger_frame": 0, "repeat_ms": 0, "volume": 1.0})
                return m

            def on_snd_name(text: str, row_index=r):
                m = ensure_meta(row_index)
                if not m: return
                m.sounds[0]["name"] = text
            snd_name.textChanged.connect(on_snd_name)

            def on_snd_browse(_=False, row_index=r):
                m = ensure_meta(row_index)
                if not m: return
                dlg = QtWidgets.QFileDialog(self, "Select Sound File", self.project.source_folder if self.project else "", "Audio Files (*.wav *.ogg *.mp3);;All Files (*)")
                dlg.setFileMode(QtWidgets.QFileDialog.ExistingFile)
                if dlg.exec() == QtWidgets.QDialog.Accepted:
                    path = dlg.selectedFiles()[0]
                    snd_file.setText(path)
                    m.sounds[0]["file"] = path
            snd_browse.clicked.connect(on_snd_browse)

            def on_trig(val: int, row_index=r):
                m = ensure_meta(row_index)
                if not m: return
                m.sounds[0]["trigger_frame"] = int(val)
            trig.valueChanged.connect(on_trig)

            def on_rep(val: int, row_index=r):
                m = ensure_meta(row_index)
                if not m: return
                m.sounds[0]["repeat_ms"] = int(val)
            rep.valueChanged.connect(on_rep)

            def on_vol(val: float, row_index=r):
                m = ensure_meta(row_index)
                if not m: return
                m.sounds[0]["volume"] = float(val)
            vol.valueChanged.connect(on_vol)

            self.auto_rows_layout.addWidget(row_widget)
            self._auto_row_widgets.append({
                'name_edit': name_edit,
                'start_lbl': start_lbl,
                'start': start,
                'step_lbl': step_lbl,
                'step': step,
                'fill_btn': fill_btn,
                'snd_name': snd_name,
                'snd_file': snd_file,
                'snd_browse': snd_browse,
                'trig': trig,
                'rep': rep,
                'vol': vol,
            })

        self.auto_rows_layout.addStretch(1)
        self._sync_auto_slider_max()

    def _sync_auto_slider_max(self):
        if not self.project:
            return
        n = len(self.project.list_source_images())
        for row in getattr(self, '_auto_row_widgets', []):
            row['start'].setMaximum(max(0, max(0, n - 1)))
            # Update trigger max based on grid columns
            try:
                row['trig'].setMaximum(max(0, self.grid.columnCount() - 1))
            except Exception:
                pass

    def _maybe_auto_fill_all(self):
        if self.auto_enable.isChecked():
            self._auto_fill_all()

    def _auto_fill_all(self):
        if not self.project:
            return
        for r, row in enumerate(getattr(self, '_auto_row_widgets', [])):
            self._auto_fill_row(r, row['start'].value(), row['step'].value())
        self._refresh_row_preview()

    def _auto_fill_row(self, r: int, start: int, step: int):
        if not self.project:
            return
        images = self.project.list_source_images()
        n = len(images)
        if n == 0:
            return
        cols = self.grid.columnCount()
        idx = min(max(0, start), max(0, n - 1))
        for c in range(cols):
            if 0 <= idx < n:
                self.grid.set_cell_path(r, c, images[idx])
            else:
                break
            idx += max(1, step) if step > 0 else 1
        # Resync maxes in case image count changed
        self._sync_auto_slider_max()

    # Selection sync handlers with guards
    # Note: raw -> grid selection sync disabled to avoid selection jumping

    # grid -> raw selection sync disabled
