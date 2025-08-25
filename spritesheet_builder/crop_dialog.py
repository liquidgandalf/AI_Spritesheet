from PySide6 import QtWidgets, QtCore, QtGui


class CropAlignDialog(QtWidgets.QDialog):
    def __init__(self, image_paths: list[str] | str, tile_w: int, tile_h: int, offset_x: int = 0, offset_y: int = 0, parent=None, scale_percent: int = 100):
        super().__init__(parent)
        self.setWindowTitle("Crop / Align")
        self.resize(800, 600)
        # Normalize input to list
        if isinstance(image_paths, str):
            self._image_paths: list[str] = [image_paths]
        else:
            self._image_paths = list(image_paths or [])
        self._img_index = 0
        self._tile_w = tile_w
        self._tile_h = tile_h
        self._offset_x = offset_x
        self._offset_y = offset_y
        self._scale_percent = max(10, min(400, int(scale_percent)))

        # Animation timer for cycling
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._on_tick)

        # Color key / overlay state
        self._color_key: QtGui.QColor | None = None
        self._overlay_item: QtWidgets.QGraphicsPixmapItem | None = None

        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        self.view = QtWidgets.QGraphicsView()
        self.view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.view.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        layout.addWidget(self.view, 1)

        self.scene = QtWidgets.QGraphicsScene(self.view)
        self.view.setScene(self.scene)

        self._base_pm = self._load_current_pm()
        pm = self._scaled_pixmap()
        self._img_item = self.scene.addPixmap(pm)
        self._img_item.setZValue(0)

        # Movable fixed-size crop rect
        self._rect_item = self.scene.addRect(0, 0, self._tile_w, self._tile_h, QtGui.QPen(QtGui.QColor("#00aaff"), 2), QtGui.QBrush(QtGui.QColor(0, 170, 255, 40)))
        self._rect_item.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self._rect_item.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self._rect_item.setZValue(1)
        self._rect_item.setPos(self._offset_x, self._offset_y)

        # Keep rect in bounds on move and sync with spin boxes
        self.scene.changed.connect(self._on_scene_changed)

        # Controls
        controls = QtWidgets.QHBoxLayout()
        # Scale slider
        self.scale_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.scale_slider.setRange(10, 400)
        self.scale_slider.setValue(self._scale_percent)
        self.scale_slider.setTickInterval(10)
        self.scale_slider.setSingleStep(1)
        controls.addWidget(QtWidgets.QLabel("Scale %:"))
        self.scale_label = QtWidgets.QLabel(str(self._scale_percent))
        controls.addWidget(self.scale_slider)
        controls.addWidget(self.scale_label)
        controls.addSpacing(16)
        # Transport controls
        self.prev_btn = QtWidgets.QPushButton("◀ Prev")
        self.play_btn = QtWidgets.QPushButton("▶ Play")
        self.next_btn = QtWidgets.QPushButton("Next ▶")
        controls.addWidget(self.prev_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.next_btn)
        controls.addSpacing(16)
        # Overlay controls
        self.overlay_chk = QtWidgets.QCheckBox("Show overlay (key @ 0,0)")
        self.sample_key_btn = QtWidgets.QPushButton("Pick key from 0,0")
        controls.addWidget(self.overlay_chk)
        controls.addWidget(self.sample_key_btn)
        controls.addSpacing(16)
        self.x_spin = QtWidgets.QSpinBox()
        self.x_spin.setRange(0, max(0, pm.width() - self._tile_w))
        self.x_spin.setValue(self._offset_x)
        self.y_spin = QtWidgets.QSpinBox()
        self.y_spin.setRange(0, max(0, pm.height() - self._tile_h))
        self.y_spin.setValue(self._offset_y)
        controls.addWidget(QtWidgets.QLabel("X:"))
        controls.addWidget(self.x_spin)
        controls.addSpacing(12)
        controls.addWidget(QtWidgets.QLabel("Y:"))
        controls.addWidget(self.y_spin)
        controls.addStretch(1)
        hint = QtWidgets.QLabel("Drag the blue box or adjust X/Y. The box is the tile area applied to all frames.")
        hint.setStyleSheet("color: #666;")
        controls.addWidget(hint)
        layout.addLayout(controls)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.x_spin.valueChanged.connect(self._on_spin_changed)
        self.y_spin.valueChanged.connect(self._on_spin_changed)
        self.scale_slider.valueChanged.connect(self._on_scale_changed)
        self.prev_btn.clicked.connect(self._on_prev)
        self.next_btn.clicked.connect(self._on_next)
        self.play_btn.clicked.connect(self._on_toggle_play)
        self.overlay_chk.toggled.connect(self._on_overlay_toggled)
        self.sample_key_btn.clicked.connect(self._on_pick_key)

        # Fit view
        self.view.setSceneRect(self._img_item.boundingRect())
        self.view.fitInView(self._img_item, QtCore.Qt.KeepAspectRatio)

    def _on_spin_changed(self, _):
        self._rect_item.setPos(self.x_spin.value(), self.y_spin.value())

    def _on_scene_changed(self, _rects):
        # Called when items move; clamp rect and reflect position in spins
        pm: QtGui.QPixmap = self._img_item.pixmap()
        x = int(self._rect_item.pos().x())
        y = int(self._rect_item.pos().y())
        max_x = max(0, pm.width() - self._tile_w)
        max_y = max(0, pm.height() - self._tile_h)
        cx = max(0, min(x, max_x))
        cy = max(0, min(y, max_y))
        if cx != x or cy != y:
            self._rect_item.setPos(cx, cy)
        if self.x_spin.value() != cx:
            self.x_spin.blockSignals(True)
            self.x_spin.setValue(cx)
            self.x_spin.blockSignals(False)
        if self.y_spin.value() != cy:
            self.y_spin.blockSignals(True)
            self.y_spin.setValue(cy)
            self.y_spin.blockSignals(False)

    def offsets(self):
        pos = self._rect_item.pos()
        return int(pos.x()), int(pos.y())

    def scale_percent(self) -> int:
        return int(self._scale_percent)

    def _on_scale_changed(self, val: int):
        self._scale_percent = max(10, min(400, int(val)))
        self.scale_label.setText(str(self._scale_percent))
        # Update pixmap to new scale while keeping rect within bounds
        new_pm = self._scaled_pixmap()
        self._img_item.setPixmap(new_pm)
        # Update spin ranges
        self.x_spin.setRange(0, max(0, new_pm.width() - self._tile_w))
        self.y_spin.setRange(0, max(0, new_pm.height() - self._tile_h))
        # Clamp current rect
        self._on_scene_changed(None)
        # Refit view to keep image visible
        self.view.setSceneRect(self._img_item.boundingRect())
        self.view.fitInView(self._img_item, QtCore.Qt.KeepAspectRatio)
        # Rebuild overlay if visible
        if self.overlay_chk.isChecked():
            self._rebuild_overlay()

    def _scaled_pixmap(self) -> QtGui.QPixmap:
        if self._base_pm.isNull():
            return self._base_pm
        if self._scale_percent == 100:
            return self._base_pm
        w = max(1, int(self._base_pm.width() * self._scale_percent / 100.0))
        h = max(1, int(self._base_pm.height() * self._scale_percent / 100.0))
        return self._base_pm.scaled(w, h, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)

    # --- Image cycling & overlay ---
    def _load_current_pm(self) -> QtGui.QPixmap:
        if not self._image_paths:
            return QtGui.QPixmap()
        path = self._image_paths[self._img_index % len(self._image_paths)]
        return QtGui.QPixmap(path)

    def _show_current(self):
        self._base_pm = self._load_current_pm()
        self._img_item.setPixmap(self._scaled_pixmap())
        self.view.setSceneRect(self._img_item.boundingRect())
        self.view.fitInView(self._img_item, QtCore.Qt.KeepAspectRatio)
        if self.overlay_chk.isChecked():
            self._rebuild_overlay()

    def _on_prev(self):
        if not self._image_paths:
            return
        self._img_index = (self._img_index - 1) % len(self._image_paths)
        self._show_current()

    def _on_next(self):
        if not self._image_paths:
            return
        self._img_index = (self._img_index + 1) % len(self._image_paths)
        self._show_current()

    def _on_toggle_play(self):
        if self._timer.isActive():
            self._timer.stop()
            self.play_btn.setText("▶ Play")
        else:
            self._timer.start()
            self.play_btn.setText("⏸ Pause")

    def _on_tick(self):
        self._on_next()

    def _on_pick_key(self):
        # Use current image's (0,0) pixel as color key
        img = self._base_pm.toImage()
        if img.isNull():
            return
        col = QtGui.QColor(img.pixel(0, 0))
        self._color_key = col
        if self.overlay_chk.isChecked():
            self._rebuild_overlay()

    def _on_overlay_toggled(self, on: bool):
        if on:
            self._rebuild_overlay()
        else:
            if self._overlay_item is not None:
                self.scene.removeItem(self._overlay_item)
                self._overlay_item = None

    def _rebuild_overlay(self):
        if not self._image_paths:
            return
        # Build a composited image where the color key is treated as transparent
        base = QtGui.QPixmap(self._image_paths[0])
        if base.isNull():
            return
        # Use base (scaled) size for overlay canvas to match display
        canvas = self._scaled_pixmap().toImage()
        canvas.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(canvas)
        key = self._color_key
        for p in self._image_paths:
            pm = QtGui.QPixmap(p)
            if pm.isNull():
                continue
            # scale to current scale percent
            spm = pm if self._scale_percent == 100 else pm.scaled(self._scaled_pixmap().size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
            img = spm.toImage().convertToFormat(QtGui.QImage.Format.Format_ARGB32)
            if key is not None:
                # apply color key: set alpha=0 for matching pixels
                target_rgb = key.rgb() & 0x00FFFFFF
                for y in range(img.height()):
                    scan = img.scanLine(y)
                    ptr = int(scan)
                    for x in range(img.width()):
                        c = QtGui.qRgb(QtGui.qRed(img.pixel(x, y)), QtGui.qGreen(img.pixel(x, y)), QtGui.qBlue(img.pixel(x, y))) & 0x00FFFFFF
                        if c == target_rgb:
                            img.setPixel(x, y, 0x00000000)
            painter.drawImage(0, 0, img)
        painter.end()
        over_pm = QtGui.QPixmap.fromImage(canvas)
        if self._overlay_item is None:
            self._overlay_item = self.scene.addPixmap(over_pm)
            self._overlay_item.setZValue(0.5)
        else:
            self._overlay_item.setPixmap(over_pm)
