"""
MarkPigeon Settings Dialog

Settings dialog for configuring GitHub integration and app preferences.
"""

import os
import subprocess
import sys
import webbrowser

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.config import get_config, get_themes_dir, save_config
from ...core.i18n import t
from ...core.publisher import MARKPIGEON_REPO, GitHubPublisher

# Token creation URL with pre-filled scope
GITHUB_TOKEN_URL = "https://github.com/settings/tokens/new?description=MarkPigeon-Pages&scopes=repo"


class SettingsDialog(QDialog):
    """Settings dialog with Cloud/Sharing configuration."""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = get_config()
        self._setup_ui()
        self._load_settings()
        self._apply_styles()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(t("settings.title"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)

        # Tab widget
        self.tabs = QTabWidget()

        # Themes tab
        themes_tab = self._create_themes_tab()
        self.tabs.addTab(themes_tab, t("settings.themes_tab"))

        # Cloud tab
        cloud_tab = self._create_cloud_tab()
        self.tabs.addTab(cloud_tab, t("settings.cloud_tab"))

        # Published Pages tab
        pages_tab = self._create_pages_tab()
        self.tabs.addTab(pages_tab, t("pages_manager.tab"))

        layout.addWidget(self.tabs)

        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._save_and_close)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)

    def _create_cloud_tab(self) -> QWidget:
        """Create the Cloud/Sharing settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # GitHub Token Group
        token_group = QGroupBox(t("settings.github_token"))
        token_layout = QVBoxLayout(token_group)

        # Token input row
        token_row = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText(t("settings.token_placeholder"))

        self.verify_btn = QPushButton(t("settings.verify"))
        self.verify_btn.clicked.connect(self._verify_token)

        token_row.addWidget(self.token_input)
        token_row.addWidget(self.verify_btn)
        token_layout.addLayout(token_row)

        # Token status
        self.token_status = QLabel("")
        self.token_status.setObjectName("tokenStatus")
        token_layout.addWidget(self.token_status)

        # Help text with link
        help_layout = QHBoxLayout()
        help_label = QLabel(t("settings.token_help"))
        help_label.setObjectName("helpText")

        self.get_token_btn = QPushButton(t("settings.get_token"))
        self.get_token_btn.setObjectName("linkButton")
        self.get_token_btn.clicked.connect(self._open_token_page)

        help_layout.addWidget(help_label)
        help_layout.addWidget(self.get_token_btn)
        help_layout.addStretch()
        token_layout.addLayout(help_layout)

        # Token instructions
        instructions = QLabel(t("settings.token_instructions"))
        instructions.setObjectName("instructions")
        instructions.setWordWrap(True)
        token_layout.addWidget(instructions)

        layout.addWidget(token_group)

        # Repository Settings Group
        repo_group = QGroupBox(t("settings.repository"))
        repo_layout = QVBoxLayout(repo_group)

        repo_row = QHBoxLayout()
        repo_label = QLabel(t("settings.repo_name"))
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("markpigeon-shelf")

        repo_row.addWidget(repo_label)
        repo_row.addWidget(self.repo_input)
        repo_layout.addLayout(repo_row)

        repo_hint = QLabel(t("settings.repo_hint"))
        repo_hint.setObjectName("helpText")
        repo_layout.addWidget(repo_hint)

        layout.addWidget(repo_group)

        # Privacy Settings Group
        privacy_group = QGroupBox(t("settings.privacy"))
        privacy_layout = QVBoxLayout(privacy_group)

        self.privacy_warning_cb = QCheckBox(t("settings.show_privacy_warning"))
        privacy_layout.addWidget(self.privacy_warning_cb)

        layout.addWidget(privacy_group)

        # Star MarkPigeon Section
        star_group = QGroupBox("💖 " + t("settings.support"))
        star_layout = QVBoxLayout(star_group)

        star_message = QLabel(t("settings.star_message"))
        star_message.setWordWrap(True)
        star_message.setObjectName("starMessage")
        star_layout.addWidget(star_message)

        star_row = QHBoxLayout()
        self.star_btn = QPushButton("⭐ " + t("settings.star_button"))
        self.star_btn.setObjectName("starButton")
        self.star_btn.clicked.connect(self._star_markpigeon)

        self.star_status = QLabel("")
        self.star_status.setObjectName("starStatus")

        star_row.addWidget(self.star_btn)
        star_row.addWidget(self.star_status)
        star_row.addStretch()
        star_layout.addLayout(star_row)

        layout.addWidget(star_group)

        layout.addStretch()

        return tab

    def _create_themes_tab(self) -> QWidget:
        """Create the Themes settings tab."""
        from pathlib import Path

        from ...core.converter import Converter

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # User Themes Group
        user_themes_group = QGroupBox(t("settings.themes_user"))
        user_themes_layout = QVBoxLayout(user_themes_group)

        # User themes location
        user_themes_dir = get_themes_dir()
        location_label = QLabel(f"📁 {user_themes_dir}")
        location_label.setObjectName("helpText")
        location_label.setWordWrap(True)
        user_themes_layout.addWidget(location_label)

        # Open folder button
        open_folder_btn = QPushButton(t("settings.open_themes_folder"))
        open_folder_btn.clicked.connect(lambda: self._open_themes_folder(user_themes_dir))
        user_themes_layout.addWidget(open_folder_btn)

        # Help text
        help_label = QLabel(t("settings.themes_help"))
        help_label.setObjectName("helpText")
        help_label.setWordWrap(True)
        user_themes_layout.addWidget(help_label)

        # User theme list
        user_themes = []
        if user_themes_dir.exists():
            user_themes = [f.stem for f in user_themes_dir.glob("*.css")]

        if user_themes:
            themes_list = QLabel("• " + "\n• ".join(sorted(user_themes)))
            themes_list.setObjectName("themesList")
        else:
            themes_list = QLabel(t("settings.no_user_themes"))
            themes_list.setObjectName("helpText")
        user_themes_layout.addWidget(themes_list)

        layout.addWidget(user_themes_group)

        # Bundled Themes Group
        bundled_group = QGroupBox(t("settings.themes_bundled"))
        bundled_layout = QVBoxLayout(bundled_group)

        # Get bundled themes (from project_root/themes/)
        # Path: src/interfaces/gui/settings_dialog.py -> project_root
        bundled_dir = Path(__file__).parent.parent.parent.parent / "themes"
        bundled_themes = []
        if bundled_dir.exists():
            bundled_themes = [f.stem for f in bundled_dir.glob("*.css")]

        if bundled_themes:
            bundled_list = QLabel("• " + "\n• ".join(sorted(bundled_themes)))
            bundled_list.setObjectName("themesList")
        else:
            bundled_list = QLabel("No bundled themes found")
            bundled_list.setObjectName("helpText")
        bundled_layout.addWidget(bundled_list)

        layout.addWidget(bundled_group)

        layout.addStretch()

        return tab

    def _create_pages_tab(self) -> QWidget:
        """Create the Published Pages management tab."""
        from PySide6.QtCore import Qt

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # Header with description
        header_layout = QHBoxLayout()
        title_label = QLabel(f"<b>{t('pages_manager.title')}</b>")
        title_label.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Refresh button
        self.refresh_pages_btn = QPushButton(f"🔄 {t('pages_manager.refresh')}")
        self.refresh_pages_btn.clicked.connect(self._load_published_pages)
        header_layout.addWidget(self.refresh_pages_btn)
        layout.addLayout(header_layout)

        # Description
        desc_label = QLabel(t("pages_manager.description"))
        desc_label.setObjectName("helpText")
        layout.addWidget(desc_label)

        # Table for published pages
        self.pages_table = QTableWidget()
        self.pages_table.setColumnCount(3)
        self.pages_table.setHorizontalHeaderLabels([
            t("pages_manager.filename"),
            t("pages_manager.url"),
            t("pages_manager.actions"),
        ])
        self.pages_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.pages_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.pages_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.pages_table.setAlternatingRowColors(True)
        self.pages_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.pages_table.verticalHeader().setVisible(False)
        layout.addWidget(self.pages_table)

        # Status label for empty state or loading
        self.pages_status = QLabel("")
        self.pages_status.setObjectName("helpText")
        self.pages_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.pages_status)

        return tab

    def _load_published_pages(self):
        """Load the list of published pages from GitHub."""
        from PySide6.QtCore import QCoreApplication, Qt

        token = self.config.github_token
        if not token:
            self.pages_table.setRowCount(0)
            self.pages_status.setText(t("pages_manager.no_token"))
            return

        self.refresh_pages_btn.setEnabled(False)
        self.pages_status.setText(t("pages_manager.loading"))
        QCoreApplication.processEvents()

        try:
            publisher = GitHubPublisher(token, self.config.github_repo_name or "markpigeon-shelf")
            files = publisher.list_published_files()

            self.pages_table.setRowCount(len(files))

            if not files:
                self.pages_status.setText(t("pages_manager.no_pages"))
            else:
                self.pages_status.setText("")

            for row, file_info in enumerate(files):
                # Filename
                name_item = QTableWidgetItem(file_info["name"])
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.pages_table.setItem(row, 0, name_item)

                # URL  
                url_item = QTableWidgetItem(file_info["url"])
                url_item.setFlags(url_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                url_item.setToolTip(file_info["url"])
                self.pages_table.setItem(row, 1, url_item)

                # Action buttons
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(4)

                copy_btn = QPushButton(t("pages_manager.copy"))
                copy_btn.setProperty("url", file_info["url"])
                copy_btn.clicked.connect(lambda checked, url=file_info["url"]: self._copy_page_url(url))
                copy_btn.setMaximumWidth(60)

                delete_btn = QPushButton(t("pages_manager.delete"))
                delete_btn.setProperty("filename", file_info["name"])
                delete_btn.clicked.connect(lambda checked, name=file_info["name"]: self._delete_page(name))
                delete_btn.setMaximumWidth(60)
                delete_btn.setStyleSheet("color: #dc3545;")

                actions_layout.addWidget(copy_btn)
                actions_layout.addWidget(delete_btn)
                self.pages_table.setCellWidget(row, 2, actions_widget)

        except Exception as e:
            self.pages_status.setText(f"Error: {str(e)}")
        finally:
            self.refresh_pages_btn.setEnabled(True)

    def _copy_page_url(self, url: str):
        """Copy a page URL to clipboard."""
        QApplication.clipboard().setText(url)
        # Show brief feedback
        self.pages_status.setText(f"✅ {t('pages_manager.link_copied')}")

    def _delete_page(self, filename: str):
        """Delete a published page."""
        from PySide6.QtCore import QCoreApplication

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            t("pages_manager.confirm_delete"),
            t("pages_manager.confirm_delete_message", filename=filename),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        token = self.config.github_token
        if not token:
            return

        self.pages_status.setText(t("pages_manager.loading"))
        QCoreApplication.processEvents()

        try:
            publisher = GitHubPublisher(token, self.config.github_repo_name or "markpigeon-shelf")
            success, message = publisher.delete_file(filename)

            if success:
                self.pages_status.setText(f"✅ {t('pages_manager.deleted')}")
                self._load_published_pages()  # Refresh the list
            else:
                QMessageBox.warning(
                    self,
                    t("pages_manager.delete_failed"),
                    message,
                )
        except Exception as e:
            QMessageBox.warning(
                self,
                t("pages_manager.delete_failed"),
                str(e),
            )

    def _open_themes_folder(self, folder_path):
        """Open the themes folder in file explorer."""
        from pathlib import Path

        folder_path = Path(folder_path)
        folder_path.mkdir(parents=True, exist_ok=True)

        if sys.platform == "win32":
            os.startfile(str(folder_path))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(folder_path)])
        else:
            subprocess.run(["xdg-open", str(folder_path)])

    def _apply_styles(self):
        """Apply styles to the dialog."""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            #helpText {
                color: #6c757d;
                font-size: 12px;
            }
            #instructions {
                color: #6c757d;
                font-size: 11px;
                background-color: #f8f9fa;
                padding: 8px;
                border-radius: 4px;
            }
            #linkButton {
                background: none;
                border: none;
                color: #0d6efd;
                text-decoration: underline;
                padding: 0;
            }
            #linkButton:hover {
                color: #0a58ca;
            }
            #tokenStatus {
                font-size: 12px;
            }
            #starMessage {
                color: #495057;
                font-size: 13px;
            }
            #starButton {
                background-color: #ffc107;
                color: #212529;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            #starButton:hover {
                background-color: #ffca2c;
            }
            #starStatus {
                font-size: 12px;
                color: #198754;
            }
        """)

    def _load_settings(self):
        """Load current settings into UI."""
        self.token_input.setText(self.config.github_token)
        self.repo_input.setText(self.config.github_repo_name or "markpigeon-shelf")
        self.privacy_warning_cb.setChecked(self.config.privacy_warning_enabled)

        # Show token status if token exists
        if self.config.github_token and self.config.github_username:
            self.token_status.setText(
                f"✅ {t('settings.connected_as')} {self.config.github_username}"
            )
            self.token_status.setStyleSheet("color: #198754;")

        # Update star button if already starred
        if self.config.has_starred_markpigeon:
            self.star_status.setText(t("settings.already_starred"))

    def _verify_token(self):
        """Verify the GitHub token."""
        token = self.token_input.text().strip()
        if not token:
            self.token_status.setText(t("settings.token_empty"))
            self.token_status.setStyleSheet("color: #dc3545;")
            return

        self.verify_btn.setEnabled(False)
        self.token_status.setText(t("settings.verifying"))
        self.token_status.setStyleSheet("color: #6c757d;")

        # Force UI update
        from PySide6.QtCore import QCoreApplication

        QCoreApplication.processEvents()

        publisher = GitHubPublisher(token)
        success, message = publisher.check_connection()

        self.verify_btn.setEnabled(True)

        if success:
            self.token_status.setText(f"✅ {t('settings.connected_as')} {message}")
            self.token_status.setStyleSheet("color: #198754;")
            self.config.github_username = message
        else:
            self.token_status.setText(f"❌ {message}")
            self.token_status.setStyleSheet("color: #dc3545;")

    def _open_token_page(self):
        """Open GitHub token creation page."""
        webbrowser.open(GITHUB_TOKEN_URL)

    def _star_markpigeon(self):
        """Star the MarkPigeon repository."""
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, t("settings.error"), t("settings.token_required_for_star"))
            return

        self.star_btn.setEnabled(False)
        self.star_status.setText(t("settings.starring"))

        from PySide6.QtCore import QCoreApplication

        QCoreApplication.processEvents()

        publisher = GitHubPublisher(token)
        success, message = publisher.star_repo(MARKPIGEON_REPO)

        self.star_btn.setEnabled(True)

        if success:
            self.star_status.setText(message)
            self.config.has_starred_markpigeon = True
        else:
            self.star_status.setText(message)

    def _save_and_close(self):
        """Save settings and close dialog."""
        self.config.github_token = self.token_input.text().strip()
        self.config.github_repo_name = self.repo_input.text().strip() or "markpigeon-shelf"
        self.config.privacy_warning_enabled = self.privacy_warning_cb.isChecked()

        save_config()
        self.settings_changed.emit()
        self.accept()
