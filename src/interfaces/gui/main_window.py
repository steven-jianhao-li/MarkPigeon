"""
MarkPigeon GUI Main Window

The main application window for the GUI interface.
"""

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ...core import __version__
from ...core.config import get_config, save_config
from ...core.converter import BatchResult, Converter, ExportMode
from ...core.i18n import get_i18n
from ...core.publisher import GitHubPublisher
from .components import (
    DropZone,
    ExportModeSelector,
    FileListWidget,
    ProgressWidget,
    ThemeSelector,
)
from .settings_dialog import SettingsDialog


class ConversionWorker(QThread):
    """Worker thread for file conversion."""

    progress = Signal(int, int, str)  # current, total, message
    finished = Signal(object)  # BatchResult
    error = Signal(str)

    def __init__(
        self,
        converter: Converter,
        files: list[Path],
        output_dir: Path,
        theme: str | None,
        export_mode: str,
    ):
        super().__init__()
        self.converter = converter
        self.files = files
        self.output_dir = output_dir
        self.theme = theme
        self.export_mode = export_mode

    def run(self):
        """Run the conversion."""
        try:
            self.converter.set_progress_callback(lambda c, t, m: self.progress.emit(c, t, m))

            result = self.converter.convert_batch(
                self.files, self.output_dir, self.theme, self.export_mode
            )

            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.i18n = get_i18n()
        self.converter = Converter()
        self.worker: ConversionWorker | None = None
        self.output_dir: Path | None = None

        self._setup_ui()
        self._setup_menu()
        self._connect_signals()
        self._apply_translations()

    def _setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("MarkPigeon")
        self.setMinimumSize(800, 600)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Top section: Drop zone and file list
        top_section = QSplitter(Qt.Orientation.Vertical)

        # Drop zone
        self.drop_zone = DropZone()
        top_section.addWidget(self.drop_zone)

        # File list
        self.file_list = FileListWidget()
        top_section.addWidget(self.file_list)

        top_section.setStretchFactor(0, 1)
        top_section.setStretchFactor(1, 2)

        # Options section
        options_frame = QFrame()
        options_frame.setObjectName("optionsFrame")
        options_layout = QHBoxLayout(options_frame)

        # Left: Output directory
        output_group = QVBoxLayout()
        self.output_label = QLabel("Output Directory:")
        self.output_display = QLabel("Same as input")
        self.output_display.setObjectName("outputPath")

        output_buttons = QHBoxLayout()
        self.output_choose_btn = QPushButton("Choose...")
        self.output_reset_btn = QPushButton("Reset")
        output_buttons.addWidget(self.output_choose_btn)
        output_buttons.addWidget(self.output_reset_btn)
        output_buttons.addStretch()

        output_group.addWidget(self.output_label)
        output_group.addWidget(self.output_display)
        output_group.addLayout(output_buttons)

        # Middle: Theme selector
        self.theme_selector = ThemeSelector()
        themes = self.converter.get_available_themes()
        self.theme_selector.set_themes(themes, self.i18n.t("main.no_theme"))

        # Right: Export mode
        self.export_mode_selector = ExportModeSelector()

        options_layout.addLayout(output_group, 1)
        options_layout.addWidget(self.theme_selector, 1)
        options_layout.addWidget(self.export_mode_selector, 1)

        # Progress section
        self.progress_widget = ProgressWidget()

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.convert_btn = QPushButton("Convert")
        self.convert_btn.setObjectName("convertButton")
        self.convert_btn.setMinimumWidth(150)
        self.convert_btn.setEnabled(False)

        self.share_btn = QPushButton("Convert & Share")
        self.share_btn.setObjectName("shareButton")
        self.share_btn.setMinimumWidth(150)
        self.share_btn.setEnabled(False)

        button_layout.addWidget(self.convert_btn)
        button_layout.addWidget(self.share_btn)

        # Add all sections to main layout
        main_layout.addWidget(top_section, 3)
        main_layout.addWidget(options_frame, 0)
        main_layout.addWidget(self.progress_widget, 0)
        main_layout.addLayout(button_layout)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        self._apply_styles()

    def _apply_styles(self):
        """Apply global styles."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            #optionsFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 16px;
            }
            #outputPath {
                color: #6c757d;
                font-style: italic;
            }
            #convertButton {
                padding: 12px 32px;
                background-color: #198754;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            #convertButton:hover {
                background-color: #157347;
            }
            #convertButton:disabled {
                background-color: #6c757d;
            }
            #shareButton {
                padding: 12px 32px;
                background-color: #0d6efd;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            #shareButton:hover {
                background-color: #0b5ed7;
            }
            #shareButton:disabled {
                background-color: #6c757d;
            }
            QPushButton {
                padding: 6px 16px;
            }
        """)

    def _setup_menu(self):
        """Set up the menu bar."""
        menubar = self.menuBar()

        # File menu
        self.file_menu = menubar.addMenu(self.i18n.t("menu.file"))

        self.action_open = QAction(self.i18n.t("dialog.select_files"), self)
        self.action_open.setShortcut("Ctrl+O")
        self.file_menu.addAction(self.action_open)

        self.action_open_folder = QAction(self.i18n.t("dialog.select_folder"), self)
        self.action_open_folder.setShortcut("Ctrl+Shift+O")
        self.file_menu.addAction(self.action_open_folder)

        self.file_menu.addSeparator()

        self.action_exit = QAction(self.i18n.t("menu.exit"), self)
        self.action_exit.setShortcut("Ctrl+Q")
        self.file_menu.addAction(self.action_exit)

        # View menu
        self.view_menu = menubar.addMenu(self.i18n.t("menu.view"))

        # Language submenu
        self.lang_menu = self.view_menu.addMenu(self.i18n.t("menu.language"))
        self.action_lang_en = QAction("English", self)
        self.action_lang_en.setCheckable(True)
        self.action_lang_zh = QAction("简体中文", self)
        self.action_lang_zh.setCheckable(True)

        self.lang_menu.addAction(self.action_lang_en)
        self.lang_menu.addAction(self.action_lang_zh)

        # Set current language checked
        if self.i18n.current_locale == "en":
            self.action_lang_en.setChecked(True)
        else:
            self.action_lang_zh.setChecked(True)

        # Settings menu (standalone)
        self.action_settings = QAction(self.i18n.t("menu.settings"), self)
        self.action_settings.setShortcut("Ctrl+,")
        menubar.addAction(self.action_settings)

        # Help menu
        self.help_menu = menubar.addMenu(self.i18n.t("menu.help"))

        self.action_about = QAction(self.i18n.t("menu.about"), self)
        self.help_menu.addAction(self.action_about)

    def _connect_signals(self):
        """Connect signals and slots."""
        # Drop zone
        self.drop_zone.files_dropped.connect(self._on_files_dropped)

        # File list
        self.file_list.files_cleared.connect(self._update_convert_button)

        # Output directory
        self.output_choose_btn.clicked.connect(self._choose_output_dir)
        self.output_reset_btn.clicked.connect(self._reset_output_dir)

        # Convert button
        self.convert_btn.clicked.connect(self._start_conversion)
        self.share_btn.clicked.connect(self._start_share)

        # Menu actions
        self.action_open.triggered.connect(self._open_files)
        self.action_open_folder.triggered.connect(self._open_folder)
        self.action_settings.triggered.connect(self._show_settings)
        self.action_exit.triggered.connect(self.close)
        self.action_lang_en.triggered.connect(lambda: self._change_language("en"))
        self.action_lang_zh.triggered.connect(lambda: self._change_language("zh_CN"))
        self.action_about.triggered.connect(self._show_about)

    def _apply_translations(self):
        """Apply translations to UI elements."""
        t = self.i18n.t

        self.setWindowTitle(t("app.title"))
        self.drop_zone.set_text(t("main.drop_hint"))
        self.drop_zone.set_button_text(t("main.browse_files"))
        self.output_label.setText(t("main.output_dir") + ":")
        self.output_display.setText(t("main.same_as_input"))
        self.output_choose_btn.setText(t("main.choose_output"))
        self.output_reset_btn.setText(t("main.reset"))
        self.theme_selector.set_label_text(t("main.theme") + ":")
        self.export_mode_selector.setTitle(t("main.export_mode"))
        self.export_mode_selector.set_mode_texts(
            t("main.mode_default"), t("main.mode_zip"), t("main.mode_batch")
        )
        self.convert_btn.setText(t("main.convert"))
        self.convert_btn.setToolTip(t("main.convert_tooltip"))
        self.share_btn.setText(t("cloud.convert_and_share"))
        self.share_btn.setToolTip(t("main.share_tooltip"))
        self.progress_widget.set_status(t("status.ready"))

        # Update file list header
        self.file_list.set_header_text(t("file_list.files") + " ({count})")
        self.file_list.set_clear_text(t("main.clear"))

        # Update menu items
        self.file_menu.setTitle(t("menu.file"))
        self.action_open.setText(t("dialog.select_files"))
        self.action_open_folder.setText(t("dialog.select_folder"))
        self.action_exit.setText(t("menu.exit"))
        self.view_menu.setTitle(t("menu.view"))
        self.lang_menu.setTitle(t("menu.language"))
        self.action_settings.setText(t("menu.settings"))
        self.help_menu.setTitle(t("menu.help"))
        self.action_about.setText(t("menu.about"))

    @Slot(list)
    def _on_files_dropped(self, files: list[Path]):
        """Handle dropped files."""
        self.file_list.add_files(files)
        self._update_convert_button()

    def _update_convert_button(self):
        """Update convert button state."""
        has_files = len(self.file_list.get_files()) > 0
        self.convert_btn.setEnabled(has_files)
        self.share_btn.setEnabled(has_files)

    def _choose_output_dir(self):
        """Choose output directory."""
        directory = QFileDialog.getExistingDirectory(
            self, self.i18n.t("dialog.select_output"), str(Path.home())
        )

        if directory:
            self.output_dir = Path(directory)
            self.output_display.setText(str(self.output_dir))
            self.output_display.setStyleSheet("color: #212529; font-style: normal;")

    def _reset_output_dir(self):
        """Reset output directory to default."""
        self.output_dir = None
        self.output_display.setText(self.i18n.t("main.same_as_input"))
        self.output_display.setStyleSheet("color: #6c757d; font-style: italic;")

    def _open_files(self):
        """Open files dialog."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.i18n.t("dialog.select_files"),
            "",
            "Markdown Files (*.md *.markdown);;All Files (*)",
        )

        if files:
            self._on_files_dropped([Path(f) for f in files])

    def _open_folder(self):
        """Open folder dialog."""
        folder = QFileDialog.getExistingDirectory(
            self, self.i18n.t("dialog.select_folder"), str(Path.home())
        )

        if folder:
            folder_path = Path(folder)
            files = list(folder_path.glob("*.md"))
            files.extend(folder_path.glob("*.markdown"))
            if files:
                self._on_files_dropped(files)

    def _change_language(self, locale: str):
        """Change application language."""
        self.i18n.load_locale(locale)
        self._apply_translations()

        # Update menu checkmarks
        self.action_lang_en.setChecked(locale == "en")
        self.action_lang_zh.setChecked(locale == "zh_CN")

        QMessageBox.information(
            self, "Language Changed", "Some changes may require restarting the application."
        )

    def _show_about(self):
        """Show about dialog."""
        t = self.i18n.t

        QMessageBox.about(
            self,
            t("about.title"),
            f"""
            <h2>MarkPigeon</h2>
            <p>{t("about.version", version=__version__)}</p>
            <p>{t("about.description")}</p>
            <p>{t("about.copyright")}</p>
            """,
        )

    def _start_conversion(self):
        """Start the conversion process."""
        files = self.file_list.get_files()

        if not files:
            QMessageBox.warning(self, "Warning", self.i18n.t("messages.no_files"))
            return

        # Determine output directory
        output_dir = self.output_dir
        if output_dir is None:
            output_dir = files[0].parent

        # Get options
        theme = self.theme_selector.get_selected_theme()
        export_mode = self.export_mode_selector.get_mode()

        # Map export mode
        mode_map = {
            "default": ExportMode.DEFAULT,
            "zip": ExportMode.INDIVIDUAL_ZIP,
            "batch": ExportMode.BATCH_ZIP,
        }
        export_mode = mode_map.get(export_mode, ExportMode.DEFAULT)

        # Disable UI during conversion
        self.convert_btn.setEnabled(False)
        self.convert_btn.setText(self.i18n.t("main.converting"))

        # Create and start worker
        self.worker = ConversionWorker(self.converter, files, output_dir, theme, export_mode)

        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_conversion_finished)
        self.worker.error.connect(self._on_conversion_error)

        self.worker.start()

    @Slot(int, int, str)
    def _on_progress(self, current: int, total: int, message: str):
        """Handle progress updates."""
        self.progress_widget.set_progress(current, total, message)
        self.status_bar.showMessage(message)

    @Slot(object)
    def _on_conversion_finished(self, result: BatchResult):
        """Handle conversion completion."""
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText(self.i18n.t("main.convert"))

        status = self.i18n.t("status.complete", success=result.successful, failed=result.failed)
        self.progress_widget.set_status(status)
        self.status_bar.showMessage(status)

        # Show result dialog
        if result.failed == 0:
            reply = QMessageBox.information(
                self,
                "Success",
                self.i18n.t("messages.conversion_success", count=result.successful)
                + "\n\n"
                + self.i18n.t("messages.open_output")
                + "?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Open output folder
                output_path = result.results[0].output_file.parent if result.results else None
                if output_path:
                    self._open_folder_in_explorer(output_path)
        else:
            QMessageBox.warning(
                self, "Warning", self.i18n.t("messages.conversion_failed", count=result.failed)
            )

    @Slot(str)
    def _on_conversion_error(self, error: str):
        """Handle conversion error."""
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText(self.i18n.t("main.convert"))

        self.progress_widget.set_status(self.i18n.t("status.error", message=error))

        QMessageBox.critical(self, "Error", f"Conversion failed: {error}")

    def _open_folder_in_explorer(self, path: Path):
        """Open folder in system file explorer."""
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)])
        else:
            subprocess.run(["xdg-open", str(path)])

    def _show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._apply_translations)
        dialog.settings_changed.connect(self._refresh_themes)
        dialog.exec()
        # Also refresh themes after dialog closes (in case user added new themes)
        self._refresh_themes()

    def _refresh_themes(self):
        """Refresh the theme list from disk."""
        current_theme = self.theme_selector.get_selected_theme()
        themes = self.converter.get_available_themes()
        self.theme_selector.set_themes(themes, self.i18n.t("main.no_theme"))
        # Try to restore selection
        if current_theme:
            index = self.theme_selector.combo.findData(current_theme)
            if index >= 0:
                self.theme_selector.combo.setCurrentIndex(index)

    def _start_share(self):
        """Start convert and share process for multiple files with batch commit."""
        import webbrowser

        from PySide6.QtWidgets import QCheckBox, QButtonGroup, QRadioButton

        config = get_config()

        # Check if token is configured
        if not config.github_token:
            QMessageBox.warning(
                self,
                self.i18n.t("cloud.upload_failed"),
                self.i18n.t("cloud.no_token"),
            )
            self._show_settings()
            return

        # Show privacy warning if enabled
        if config.privacy_warning_enabled:
            msg = QMessageBox(self)
            msg.setWindowTitle(self.i18n.t("cloud.privacy_warning_title"))
            msg.setText(self.i18n.t("cloud.privacy_warning_message"))
            msg.setIcon(QMessageBox.Icon.Warning)

            dont_show_cb = QCheckBox(self.i18n.t("cloud.dont_show_again"))
            msg.setCheckBox(dont_show_cb)

            msg.setStandardButtons(
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
            )
            msg.button(QMessageBox.StandardButton.Ok).setText(self.i18n.t("cloud.confirm_upload"))
            msg.button(QMessageBox.StandardButton.Cancel).setText(self.i18n.t("cloud.cancel"))

            result = msg.exec()

            if result != QMessageBox.StandardButton.Ok:
                return

            if dont_show_cb.isChecked():
                config.privacy_warning_enabled = False
                save_config()

        # Get all files
        files = self.file_list.get_files()
        if not files:
            QMessageBox.warning(self, "Warning", self.i18n.t("messages.no_files"))
            return

        # Disable buttons
        self.convert_btn.setEnabled(False)
        self.share_btn.setEnabled(False)
        self.share_btn.setText(self.i18n.t("cloud.sharing"))

        from PySide6.QtCore import QCoreApplication

        # Create publisher
        def progress_cb(curr, total, msg_text):
            self.progress_widget.set_progress(curr, total, msg_text)
            QCoreApplication.processEvents()

        publisher = GitHubPublisher(
            config.github_token, config.github_repo_name, progress_callback=progress_cb
        )

        # Convert all files first and check for conflicts
        theme = self.theme_selector.get_selected_theme()
        files_to_publish = []  # List of (html_path, assets_dir, original_name)
        errors = []
        total_files = len(files)
        
        # Track conflict handling preference for "apply to all"
        conflict_action_all = None  # None, 'rename', 'overwrite', 'skip'

        for i, file_to_share in enumerate(files, 1):
            QCoreApplication.processEvents()
            
            # Update progress
            self.progress_widget.set_status(
                f"{self.i18n.t('cloud.sharing')} ({i}/{total_files}): {file_to_share.name}"
            )
            QCoreApplication.processEvents()

            # Convert file
            output_dir = self.output_dir or file_to_share.parent
            result = self.converter.convert_file(file_to_share, output_dir, theme)

            if not result.success:
                errors.append(f"{file_to_share.name}: {result.error}")
                continue

            # Check if file already exists
            html_filename = result.output_file.name
            exists, _ = publisher.check_file_exists(html_filename)
            
            if exists:
                action = conflict_action_all
                
                if action is None:
                    # Show conflict dialog
                    action, apply_to_all = self._show_conflict_dialog(html_filename)
                    
                    if apply_to_all:
                        conflict_action_all = action
                
                if action == 'skip':
                    continue
                elif action == 'rename':
                    # Generate new filename with suffix
                    new_filename = self._generate_unique_filename(publisher, html_filename)
                    # Rename the file
                    new_path = result.output_file.parent / new_filename
                    result.output_file.rename(new_path)
                    result.output_file = new_path
                # 'overwrite' - just proceed, batch commit will overwrite

            files_to_publish.append((result.output_file, result.assets_dir, file_to_share.name))

        # Use batch publish to upload all files in a single commit
        if files_to_publish:
            self.progress_widget.set_status(self.i18n.t("cloud.sharing"))
            QCoreApplication.processEvents()
            
            # Prepare files for batch publish
            batch_files = [(html_path, assets_dir) for html_path, assets_dir, _ in files_to_publish]
            publish_result = publisher.publish_batch(batch_files)
            
            if publish_result.success:
                # Build URLs for each file
                base_url = publisher.get_pages_url()
                published_urls = [
                    (original_name, f"{base_url}{html_path.name}")
                    for html_path, _, original_name in files_to_publish
                ]
            else:
                errors.append(publish_result.message)
                published_urls = []
        else:
            published_urls = []

        self._reset_button_states()

        # Show results
        if published_urls:
            # Build success message
            url_list = "\n".join([f"• {name}: {url}" for name, url in published_urls])
            
            if len(published_urls) == 1:
                msg_text = (
                    f"{self.i18n.t('cloud.success_message')}\n\n"
                    f"{self.i18n.t('cloud.public_link')}\n{published_urls[0][1]}\n\n"
                    f"{self.i18n.t('cloud.first_time_hint')}"
                )
            else:
                msg_text = (
                    f"{self.i18n.t('cloud.multi_share_success', count=len(published_urls))}\n\n"
                    f"{self.i18n.t('cloud.published_files')}\n{url_list}\n\n"
                    f"{self.i18n.t('cloud.first_time_hint')}"
                )
            
            if errors:
                msg_text += f"\n\n⚠️ {len(errors)} file(s) failed:\n" + "\n".join(errors)

            msg = QMessageBox(self)
            msg.setWindowTitle(self.i18n.t("cloud.success_title"))
            msg.setText(msg_text)
            msg.setIcon(QMessageBox.Icon.Information)

            copy_btn = msg.addButton(
                self.i18n.t("cloud.copy_link"), QMessageBox.ButtonRole.ActionRole
            )
            open_btn = msg.addButton(
                self.i18n.t("cloud.open_in_browser"), QMessageBox.ButtonRole.ActionRole
            )
            msg.addButton(QMessageBox.StandardButton.Ok)

            msg.exec()

            # Copy all URLs or first URL
            if msg.clickedButton() == copy_btn:
                if len(published_urls) == 1:
                    QApplication.clipboard().setText(published_urls[0][1])
                else:
                    all_urls = "\n".join([f"{name}: {url}" for name, url in published_urls])
                    QApplication.clipboard().setText(all_urls)
                self.status_bar.showMessage(self.i18n.t("cloud.link_copied"))
            elif msg.clickedButton() == open_btn:
                # Open all URLs in browser
                for _, url in published_urls:
                    webbrowser.open(url)
        else:
            # All failed
            error_msg = "\n".join(errors) if errors else "Unknown error"
            QMessageBox.critical(self, self.i18n.t("cloud.upload_failed"), error_msg)

    def _show_conflict_dialog(self, filename: str) -> tuple[str, bool]:
        """
        Show a dialog for handling file conflicts.
        
        Returns:
            Tuple of (action, apply_to_all) where action is 'rename', 'overwrite', or 'skip'
        """
        from PySide6.QtWidgets import QCheckBox, QDialogButtonBox
        
        dialog = QMessageBox(self)
        dialog.setWindowTitle(self.i18n.t("conflict.title"))
        dialog.setText(self.i18n.t("conflict.message", filename=filename))
        dialog.setIcon(QMessageBox.Icon.Question)
        
        # Add buttons
        rename_btn = dialog.addButton(self.i18n.t("conflict.rename"), QMessageBox.ButtonRole.ActionRole)
        overwrite_btn = dialog.addButton(self.i18n.t("conflict.overwrite"), QMessageBox.ButtonRole.ActionRole)
        skip_btn = dialog.addButton(self.i18n.t("conflict.skip"), QMessageBox.ButtonRole.RejectRole)
        
        # Add checkbox for "apply to all"
        apply_all_cb = QCheckBox(self.i18n.t("conflict.apply_to_all"))
        dialog.setCheckBox(apply_all_cb)
        
        dialog.exec()
        
        clicked = dialog.clickedButton()
        apply_to_all = apply_all_cb.isChecked()
        
        if clicked == rename_btn:
            return 'rename', apply_to_all
        elif clicked == overwrite_btn:
            return 'overwrite', apply_to_all
        else:
            return 'skip', apply_to_all

    def _generate_unique_filename(self, publisher, filename: str) -> str:
        """Generate a unique filename by adding a numeric suffix."""
        import re
        
        base, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        
        # Check for existing suffix pattern like _1, _2, etc.
        match = re.match(r'^(.+)_(\d+)$', base)
        if match:
            base = match.group(1)
            counter = int(match.group(2)) + 1
        else:
            counter = 1
        
        while True:
            new_name = f"{base}_{counter}.{ext}" if ext else f"{base}_{counter}"
            exists, _ = publisher.check_file_exists(new_name)
            if not exists:
                return new_name
            counter += 1
            if counter > 100:  # Safety limit
                break
        
        return new_name

    def _reset_button_states(self):
        """Reset button states after share operation."""
        self.convert_btn.setEnabled(True)
        self.share_btn.setEnabled(True)
        self.convert_btn.setText(self.i18n.t("main.convert"))
        self.share_btn.setText(self.i18n.t("cloud.convert_and_share"))


def run_gui():
    """Run the GUI application."""
    from PySide6.QtGui import QIcon

    app = QApplication(sys.argv)
    app.setApplicationName("MarkPigeon")
    app.setApplicationVersion(__version__)

    # Set application icon
    icon_path = _get_icon_path()
    if icon_path and icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def _get_icon_path():
    """Get the path to the application icon."""
    from pathlib import Path

    # Check if running as frozen executable
    if getattr(sys, 'frozen', False):
        # Running as compiled
        base_path = Path(sys.executable).parent
    else:
        # Running as script - navigate from src/interfaces/gui/ to project root
        base_path = Path(__file__).parent.parent.parent.parent

    icon_path = base_path / "assets" / "icon.png"
    return icon_path if icon_path.exists() else None


if __name__ == "__main__":
    run_gui()
