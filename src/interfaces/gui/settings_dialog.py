"""
MarkPigeon Settings Dialog

Settings dialog for configuring GitHub integration and app preferences.
"""

import webbrowser

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.config import get_config, save_config
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

        # Cloud tab
        cloud_tab = self._create_cloud_tab()
        self.tabs.addTab(cloud_tab, t("settings.cloud_tab"))

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
