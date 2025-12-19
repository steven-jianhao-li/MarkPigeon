"""
MarkPigeon GUI Components

Reusable UI components for the GUI interface.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


class DropZone(QFrame):
    """
    A drop zone widget for dragging and dropping files.

    Signals:
        files_dropped: Emitted when files are dropped, with list of file paths.
    """

    files_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        self.setObjectName("dropZone")
        self.setMinimumHeight(150)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Sunken)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon/hint label
        self.hint_label = QLabel("📁")
        self.hint_label.setObjectName("dropZoneIcon")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_label = QLabel("Drop Markdown files here")
        self.text_label.setObjectName("dropZoneText")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Browse button
        self.browse_btn = QPushButton("Browse Files")
        self.browse_btn.setObjectName("browseButton")
        self.browse_btn.clicked.connect(self._browse_files)

        layout.addWidget(self.hint_label)
        layout.addWidget(self.text_label)
        layout.addSpacing(10)
        layout.addWidget(self.browse_btn)

        self._apply_styles()

    def _apply_styles(self):
        """Apply styles."""
        self.setStyleSheet("""
            #dropZone {
                background-color: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 8px;
            }
            #dropZone:hover {
                background-color: #e9ecef;
                border-color: #0d6efd;
            }
            #dropZoneIcon {
                font-size: 48px;
            }
            #dropZoneText {
                color: #6c757d;
                font-size: 14px;
            }
            #browseButton {
                padding: 8px 24px;
                background-color: #0d6efd;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            #browseButton:hover {
                background-color: #0b5ed7;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):  # noqa: N802
        """Handle drag enter."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(
                self.styleSheet().replace("background-color: #f8f9fa", "background-color: #e3f2fd")
            )

    def dragLeaveEvent(self, event):  # noqa: N802
        """Handle drag leave."""
        self._apply_styles()

    def dropEvent(self, event: QDropEvent):  # noqa: N802
        """Handle drop event."""
        self._apply_styles()

        files = []
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.exists():
                if path.is_file() and path.suffix.lower() in (".md", ".markdown"):
                    files.append(path)
                elif path.is_dir():
                    # Collect MD files from directory
                    files.extend(path.glob("*.md"))
                    files.extend(path.glob("*.markdown"))

        if files:
            self.files_dropped.emit(files)

        event.acceptProposedAction()

    def _browse_files(self):
        """Open file browser dialog."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Markdown Files", "", "Markdown Files (*.md *.markdown);;All Files (*)"
        )

        if files:
            self.files_dropped.emit([Path(f) for f in files])

    def set_text(self, text: str):
        """Set the hint text."""
        self.text_label.setText(text)

    def set_button_text(self, text: str):
        """Set the browse button text."""
        self.browse_btn.setText(text)


class FileItemWidget(QWidget):
    """Custom widget for a file item with delete button."""

    delete_clicked = Signal(Path)

    def __init__(self, file_path: Path, parent: QWidget | None = None):
        super().__init__(parent)
        self.file_path = file_path
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # File icon and name
        self.name_label = QLabel(f"📄 {self.file_path.name}")
        self.name_label.setToolTip(str(self.file_path))
        layout.addWidget(self.name_label, 1)

        # Delete button
        self.delete_btn = QPushButton("✕")
        self.delete_btn.setObjectName("deleteItemBtn")
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.setToolTip("Remove this file")
        self.delete_btn.clicked.connect(self._on_delete)
        layout.addWidget(self.delete_btn)

        self._apply_styles()

    def _apply_styles(self):
        """Apply styles."""
        self.setStyleSheet("""
            #deleteItemBtn {
                background-color: transparent;
                border: none;
                color: #6c757d;
                font-size: 14px;
                font-weight: bold;
                border-radius: 12px;
            }
            #deleteItemBtn:hover {
                background-color: #dc3545;
                color: white;
            }
        """)

    def _on_delete(self):
        """Handle delete button click."""
        self.delete_clicked.emit(self.file_path)


class FileListWidget(QWidget):
    """
    Widget displaying a list of files to be converted.

    Signals:
        file_removed: Emitted when a file is removed, with the file path.
        files_cleared: Emitted when all files are cleared.
    """

    file_removed = Signal(Path)
    files_cleared = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._files: list[Path] = []
        self._header_format: str = "Files ({count})"
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QHBoxLayout()
        self.count_label = QLabel("Files (0)")
        self.count_label.setObjectName("fileListHeader")

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setObjectName("clearButton")
        self.clear_btn.clicked.connect(self._clear_files)
        self.clear_btn.setEnabled(False)

        header.addWidget(self.count_label)
        header.addStretch()
        header.addWidget(self.clear_btn)

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("fileList")
        self.list_widget.setAlternatingRowColors(True)

        layout.addLayout(header)
        layout.addWidget(self.list_widget)

        self._apply_styles()

    def _apply_styles(self):
        """Apply styles."""
        self.setStyleSheet("""
            #fileListHeader {
                font-weight: bold;
                font-size: 14px;
            }
            #clearButton {
                padding: 4px 12px;
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
            }
            #clearButton:hover {
                background-color: #bb2d3b;
            }
            #clearButton:disabled {
                background-color: #6c757d;
            }
            #fileList {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            #fileList::item {
                padding: 0px;
                border-bottom: 1px solid #f0f0f0;
            }
            #fileList::item:alternate {
                background-color: #f8f9fa;
            }
            #fileList::item:selected {
                background-color: #0d6efd;
            }
            #fileList::item:hover {
                background-color: #e9ecef;
            }
            #fileList::item:selected:hover {
                background-color: #0b5ed7;
            }
        """)

    def add_files(self, files: list[Path]):
        """Add files to the list."""
        for file_path in files:
            if file_path not in self._files:
                self._files.append(file_path)

                # Create list item
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, file_path)
                item.setSizeHint(QLabel("").sizeHint())  # Will be sized by widget

                # Create custom widget
                item_widget = FileItemWidget(file_path)
                item_widget.delete_clicked.connect(self._remove_file)
                item.setSizeHint(item_widget.sizeHint())

                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, item_widget)

        self._update_count()

    def _remove_file(self, file_path: Path):
        """Remove a single file from the list."""
        if file_path in self._files:
            self._files.remove(file_path)

            # Find and remove the item
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole) == file_path:
                    self.list_widget.takeItem(i)
                    break

            self._update_count()
            self.file_removed.emit(file_path)

    def get_files(self) -> list[Path]:
        """Get list of files."""
        return self._files.copy()

    def _clear_files(self):
        """Clear all files."""
        self._files.clear()
        self.list_widget.clear()
        self._update_count()
        self.files_cleared.emit()

    def _update_count(self):
        """Update the file count label."""
        count = len(self._files)
        self.count_label.setText(self._header_format.format(count=count))
        self.clear_btn.setEnabled(count > 0)

    def set_header_text(self, text: str):
        """Set the header text template (use {count} for count)."""
        self._header_format = text
        self._update_count()

    def set_clear_text(self, text: str):
        """Set the clear button text."""
        self.clear_btn.setText(text)



class ThemeSelector(QWidget):
    """
    Widget for selecting a theme.

    Signals:
        theme_changed: Emitted when theme selection changes.
    """

    theme_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel("Theme:")
        self.combo = QComboBox()
        self.combo.setMinimumWidth(200)
        self.combo.currentTextChanged.connect(self._on_theme_changed)

        layout.addWidget(self.label)
        layout.addWidget(self.combo)
        layout.addStretch()

    def set_themes(self, themes: list[str], no_theme_text: str = "No Theme"):
        """Set available themes."""
        self.combo.clear()
        self.combo.addItem(no_theme_text, None)
        for theme in themes:
            self.combo.addItem(theme, theme)

    def get_selected_theme(self) -> str | None:
        """Get the selected theme name."""
        return self.combo.currentData()

    def _on_theme_changed(self, text: str):
        """Handle theme change."""
        theme = self.combo.currentData()
        self.theme_changed.emit(theme if theme else "")

    def set_label_text(self, text: str):
        """Set the label text."""
        self.label.setText(text)


class ExportModeSelector(QGroupBox):
    """
    Widget for selecting export mode.

    Signals:
        mode_changed: Emitted when mode changes, with mode string.
    """

    mode_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        self.setTitle("Export Mode")

        layout = QVBoxLayout(self)

        self.button_group = QButtonGroup(self)

        self.mode_default = QRadioButton("HTML + Assets Folder")
        self.mode_default.setChecked(True)
        self.button_group.addButton(self.mode_default, 0)

        self.mode_zip = QRadioButton("Individual ZIP per File")
        self.button_group.addButton(self.mode_zip, 1)

        self.mode_batch = QRadioButton("Single Batch ZIP")
        self.button_group.addButton(self.mode_batch, 2)

        layout.addWidget(self.mode_default)
        layout.addWidget(self.mode_zip)
        layout.addWidget(self.mode_batch)

        self.button_group.idClicked.connect(self._on_mode_changed)

    def get_mode(self) -> str:
        """Get the selected export mode."""
        checked_id = self.button_group.checkedId()
        modes = ["default", "zip", "batch"]
        return modes[checked_id] if 0 <= checked_id < len(modes) else "default"

    def _on_mode_changed(self, id: int):
        """Handle mode change."""
        self.mode_changed.emit(self.get_mode())

    def set_mode_texts(self, default: str, zip_mode: str, batch: str):
        """Set the mode radio button texts."""
        self.mode_default.setText(default)
        self.mode_zip.setText(zip_mode)
        self.mode_batch.setText(batch)


class ProgressWidget(QWidget):
    """Widget showing conversion progress."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)

        self._apply_styles()

    def _apply_styles(self):
        """Apply styles."""
        self.setStyleSheet("""
            #statusLabel {
                font-size: 13px;
                color: #6c757d;
                margin-bottom: 4px;
            }
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0d6efd;
                border-radius: 3px;
            }
        """)

    def set_progress(self, current: int, total: int, message: str = ""):
        """Set the progress."""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)

        if message:
            self.status_label.setText(message)

    def set_status(self, text: str):
        """Set the status text."""
        self.status_label.setText(text)

    def reset(self):
        """Reset the progress."""
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
