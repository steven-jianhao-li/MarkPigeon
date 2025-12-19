"""
MarkPigeon Converter Module

Orchestrates the complete conversion workflow from Markdown to HTML.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .packer import ExportMode, ZipPacker
from .parser import MarkdownParser
from .renderer import HtmlRenderer

logger = logging.getLogger(__name__)


@dataclass
class ConversionTask:
    """Represents a single conversion task."""

    input_file: Path
    output_dir: Path | None = None
    theme: str | None = None
    title: str | None = None


@dataclass
class ConversionResult:
    """Result of a single file conversion."""

    input_file: Path
    output_file: Path | None = None
    assets_dir: Path | None = None
    zip_file: Path | None = None
    success: bool = True
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class BatchResult:
    """Result of a batch conversion."""

    results: list[ConversionResult] = field(default_factory=list)
    total: int = 0
    successful: int = 0
    failed: int = 0
    batch_zip: Path | None = None


# Progress callback type
ProgressCallback = Callable[[int, int, str], None]  # (current, total, message)


class Converter:
    """
    Main converter class that orchestrates the complete workflow.

    Workflow:
    1. Parse Markdown files
    2. Render to HTML with theme
    3. Copy/manage assets
    4. Optionally pack to ZIP
    """

    def __init__(
        self,
        themes_dir: Path | None = None,
        default_theme: str | None = None,
        user_themes_dir: Path | None = None,
    ):
        """
        Initialize the converter.

        Args:
            themes_dir: Custom bundled themes directory
            default_theme: Default theme to use
            user_themes_dir: User themes directory (user themes have priority)
        """
        # Import here to avoid circular imports
        from .config import get_themes_dir

        # Use user themes dir from config if not specified
        if user_themes_dir is None:
            user_themes_dir = get_themes_dir()
        
        self.parser = MarkdownParser()
        self.renderer = HtmlRenderer(themes_dir, user_themes_dir)
        self.default_theme = default_theme
        self._progress_callback: ProgressCallback | None = None

    def set_progress_callback(self, callback: ProgressCallback) -> None:
        """Set a callback for progress updates."""
        self._progress_callback = callback

    def _report_progress(self, current: int, total: int, message: str) -> None:
        """Report progress if callback is set."""
        if self._progress_callback:
            try:
                self._progress_callback(current, total, message)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    def convert_file(
        self,
        input_file: Path,
        output_dir: Path | None = None,
        theme: str | None = None,
        export_mode: str = ExportMode.DEFAULT,
        cleanup_after_zip: bool = False,
    ) -> ConversionResult:
        """
        Convert a single Markdown file to HTML.

        Args:
            input_file: Path to the Markdown file
            output_dir: Output directory (defaults to same as input)
            theme: Theme name to use
            export_mode: Export mode (default, zip, batch)
            cleanup_after_zip: Remove HTML/assets after zipping

        Returns:
            ConversionResult with output information.
        """
        input_file = Path(input_file)
        result = ConversionResult(input_file=input_file)

        # Validate input
        if not input_file.exists():
            result.success = False
            result.error = f"File not found: {input_file}"
            return result

        if input_file.suffix.lower() not in (".md", ".markdown"):
            result.success = False
            result.error = f"Not a Markdown file: {input_file}"
            return result

        # Determine output directory
        if output_dir is None:
            output_dir = input_file.parent
        else:
            output_dir = Path(output_dir)

        # Use default theme if none specified
        if theme is None:
            theme = self.default_theme

        try:
            # Step 1: Parse Markdown
            logger.info(f"Parsing: {input_file}")
            parse_result = self.parser.parse_file(input_file)

            if not parse_result.html:
                result.success = False
                result.error = "Failed to parse Markdown"
                result.warnings.extend(parse_result.warnings)
                return result

            # Step 2: Render HTML with assets
            logger.info(f"Rendering: {input_file.name}")
            render_result = self.renderer.render(parse_result, output_dir, theme_name=theme)

            result.output_file = render_result.output_file
            result.assets_dir = render_result.assets_dir
            result.warnings.extend(render_result.warnings)

            if not render_result.success:
                result.success = False
                result.error = "Failed to render HTML"
                return result

            # Step 3: Pack to ZIP if requested
            if export_mode == ExportMode.INDIVIDUAL_ZIP:
                packer = ZipPacker(output_dir)
                pack_result = packer.pack_individual(
                    render_result.output_file, render_result.assets_dir
                )

                if pack_result.success:
                    result.zip_file = pack_result.zip_file

                    if cleanup_after_zip:
                        packer.cleanup_after_zip(
                            render_result.output_file, render_result.assets_dir
                        )
                        result.output_file = None
                        result.assets_dir = None
                else:
                    result.warnings.append(f"ZIP creation failed: {pack_result.error}")

            logger.info(f"Conversion complete: {input_file.name}")

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"Conversion failed for {input_file}: {e}")

        return result

    def convert_batch(
        self,
        input_files: list[Path],
        output_dir: Path,
        theme: str | None = None,
        export_mode: str = ExportMode.DEFAULT,
        cleanup_after_zip: bool = False,
    ) -> BatchResult:
        """
        Convert multiple Markdown files.

        Args:
            input_files: List of Markdown file paths
            output_dir: Output directory
            theme: Theme name to use
            export_mode: Export mode
            cleanup_after_zip: Remove HTML/assets after zipping

        Returns:
            BatchResult with all conversion results.
        """
        batch_result = BatchResult(total=len(input_files))
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Collect items for batch ZIP
        zip_items = []

        for i, input_file in enumerate(input_files):
            self._report_progress(i + 1, len(input_files), f"Converting: {input_file.name}")

            # For batch mode, don't zip individual files
            file_export_mode = (
                ExportMode.DEFAULT if export_mode == ExportMode.BATCH_ZIP else export_mode
            )

            result = self.convert_file(
                input_file,
                output_dir,
                theme,
                file_export_mode,
                cleanup_after_zip and export_mode != ExportMode.BATCH_ZIP,
            )

            batch_result.results.append(result)

            if result.success:
                batch_result.successful += 1
                if export_mode == ExportMode.BATCH_ZIP:
                    zip_items.append((result.output_file, result.assets_dir))
            else:
                batch_result.failed += 1

        # Create batch ZIP if requested
        if export_mode == ExportMode.BATCH_ZIP and zip_items:
            self._report_progress(len(input_files), len(input_files), "Creating batch ZIP...")
            packer = ZipPacker(output_dir)
            pack_result = packer.pack_batch(zip_items)

            if pack_result.success:
                batch_result.batch_zip = pack_result.zip_file

                # Cleanup if requested
                if cleanup_after_zip:
                    for html_file, assets_dir in zip_items:
                        packer.cleanup_after_zip(html_file, assets_dir)

        self._report_progress(len(input_files), len(input_files), "Complete!")
        return batch_result

    def convert_directory(
        self,
        input_dir: Path,
        output_dir: Path | None = None,
        theme: str | None = None,
        export_mode: str = ExportMode.DEFAULT,
        recursive: bool = False,
        cleanup_after_zip: bool = False,
    ) -> BatchResult:
        """
        Convert all Markdown files in a directory.

        Args:
            input_dir: Input directory
            output_dir: Output directory (defaults to input_dir)
            theme: Theme name
            export_mode: Export mode
            recursive: Search subdirectories
            cleanup_after_zip: Remove HTML/assets after zipping

        Returns:
            BatchResult with all conversion results.
        """
        input_dir = Path(input_dir)

        if not input_dir.exists() or not input_dir.is_dir():
            return BatchResult()

        # Find Markdown files
        pattern = "**/*.md" if recursive else "*.md"
        md_files = list(input_dir.glob(pattern))

        # Also include .markdown extension
        pattern_alt = "**/*.markdown" if recursive else "*.markdown"
        md_files.extend(input_dir.glob(pattern_alt))

        if not md_files:
            logger.warning(f"No Markdown files found in {input_dir}")
            return BatchResult()

        if output_dir is None:
            output_dir = input_dir

        return self.convert_batch(md_files, output_dir, theme, export_mode, cleanup_after_zip)

    def get_available_themes(self) -> list[str]:
        """Get list of available themes."""
        return self.renderer.get_available_themes()


def convert(
    input_path: Path,
    output_dir: Path | None = None,
    theme: str | None = None,
    export_mode: str = ExportMode.DEFAULT,
) -> ConversionResult:
    """
    Convenience function to convert a single file.

    Args:
        input_path: Path to Markdown file
        output_dir: Output directory
        theme: Theme name
        export_mode: Export mode

    Returns:
        ConversionResult object.
    """
    converter = Converter()
    return converter.convert_file(input_path, output_dir, theme, export_mode)
