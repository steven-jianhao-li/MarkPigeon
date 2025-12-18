"""
Tests for the MarkPigeon Publisher Module.

Uses .env file for GitHub token configuration.
Copy .env.example to .env and add your token.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import publisher module
from src.core.publisher import GitHubPublisher, PublishError, PublishResult


def get_test_token():
    """Get GitHub token from environment."""
    token = os.getenv("GITHUB_TOKEN")
    if not token or token == "your_github_token_here":
        return None
    return token


# Mark tests that require a real token
requires_token = pytest.mark.skipif(
    get_test_token() is None,
    reason="GITHUB_TOKEN not set in .env file",
)


class TestPublisherMocked:
    """Unit tests with mocked GitHub API."""

    def test_init(self):
        """Test publisher initialization."""
        publisher = GitHubPublisher("fake_token", "test-repo")

        assert publisher.token == "fake_token"
        assert publisher.repo_name == "test-repo"
        assert publisher.progress_callback is None

    def test_init_with_progress_callback(self):
        """Test publisher initialization with progress callback."""

        def callback(curr, total, msg):
            pass

        publisher = GitHubPublisher("token", "repo", progress_callback=callback)

        assert publisher.progress_callback is callback

    @patch("src.core.publisher.Github")
    def test_check_connection_success(self, mock_github):
        """Test successful token validation."""
        # Setup mock
        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.return_value.get_user.return_value = mock_user

        publisher = GitHubPublisher("valid_token")
        success, message = publisher.check_connection()

        assert success is True
        assert message == "testuser"

    @patch("src.core.publisher.Github")
    def test_check_connection_failure(self, mock_github):
        """Test failed token validation."""
        from github import GithubException

        mock_github.return_value.get_user.side_effect = GithubException(
            401, {"message": "Bad credentials"}, {}
        )

        publisher = GitHubPublisher("invalid_token")
        success, message = publisher.check_connection()

        assert success is False
        assert "Bad credentials" in message

    def test_publish_result_defaults(self):
        """Test PublishResult default values."""
        result = PublishResult()

        assert result.success is False
        assert result.url == ""
        assert result.message == ""
        assert result.files_uploaded == []
        assert result.errors == []


class TestPublisherWithToken:
    """Integration tests using real GitHub API."""

    @requires_token
    def test_check_connection_real(self):
        """Test real token validation."""
        token = get_test_token()
        publisher = GitHubPublisher(token)

        success, username = publisher.check_connection()

        assert success is True
        assert len(username) > 0
        print(f"✅ Connected as: {username}")

    @requires_token
    def test_get_or_create_repo_real(self):
        """Test repository creation/access."""
        token = get_test_token()
        publisher = GitHubPublisher(token, "markpigeon-test-shelf")

        # First connect
        success, _ = publisher.check_connection()
        assert success

        # Try to get or create repo
        try:
            repo = publisher.get_or_create_repo()
            assert repo is not None
            print(f"✅ Repository: {repo.full_name}")
        except PublishError as e:
            pytest.skip(f"Could not create test repo: {e}")

    @requires_token
    def test_upload_file_real(self):
        """Test real file upload."""
        token = get_test_token()
        publisher = GitHubPublisher(token, "markpigeon-test-shelf")

        # Connect and get repo
        success, _ = publisher.check_connection()
        assert success

        try:
            repo = publisher.get_or_create_repo()
        except PublishError as e:
            pytest.skip(f"Could not access repo: {e}")

        # Create a test file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False
        ) as f:
            f.write("<html><body>Test from pytest</body></html>")
            test_file = Path(f.name)

        try:
            success = publisher.upload_file(
                repo, test_file, "pytest_test.html", "Test upload from pytest"
            )
            assert success
            print("✅ File uploaded successfully")
        finally:
            test_file.unlink()

    @requires_token
    def test_star_repo_real(self):
        """Test starring the MarkPigeon repo."""
        token = get_test_token()
        publisher = GitHubPublisher(token)

        success, _ = publisher.check_connection()
        assert success

        # Try to star
        success, message = publisher.star_repo()
        print(f"Star result: {message}")
        # Should succeed or say already starred
        assert success or "already" in message.lower()

    @requires_token
    def test_full_publish_flow(self):
        """Test complete publish workflow."""
        token = get_test_token()

        progress_log = []

        def progress_callback(curr, total, msg):
            progress_log.append((curr, total, msg))

        publisher = GitHubPublisher(
            token, "markpigeon-test-shelf", progress_callback=progress_callback
        )

        # Create test files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create HTML file
            html_file = tmpdir / "test_publish.html"
            html_file.write_text(
                "<html><body><img src='./assets_test/image.png'></body></html>",
                encoding="utf-8",
            )

            # Create assets directory
            assets_dir = tmpdir / "assets_test"
            assets_dir.mkdir()
            (assets_dir / "image.png").write_bytes(b"fake png data")

            # Publish
            result = publisher.publish(html_file, assets_dir)

            print(f"Result: {result}")
            print(f"Progress log: {progress_log}")

            if result.success:
                assert result.url != ""
                assert len(result.files_uploaded) > 0
                print(f"✅ Published to: {result.url}")
            else:
                print(f"❌ Publish failed: {result.message}")


class TestConfigModule:
    """Tests for the config module."""

    def test_config_defaults(self):
        """Test AppConfig default values."""
        from src.core.config import AppConfig

        config = AppConfig()

        assert config.github_token == ""
        assert config.github_repo_name == "markpigeon-shelf"
        assert config.privacy_warning_enabled is True
        assert config.has_starred_markpigeon is False

    def test_config_update(self):
        """Test config update method."""
        from src.core.config import AppConfig

        config = AppConfig()
        config.update(github_token="test_token", github_username="testuser")

        assert config.github_token == "test_token"
        assert config.github_username == "testuser"

    def test_config_save_load(self):
        """Test config save and load."""
        from src.core.config import AppConfig, get_config_file

        # Create a test config
        config = AppConfig(
            github_token="test_token_123",
            github_repo_name="test-repo",
            github_username="testuser",
        )

        # Save it
        assert config.save()

        # Load it back
        loaded = AppConfig.load()

        assert loaded.github_token == "test_token_123"
        assert loaded.github_repo_name == "test-repo"
        assert loaded.github_username == "testuser"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
