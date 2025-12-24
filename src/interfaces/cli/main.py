"""
MarkPigeon CLI Interface

Command-line interface for the MarkPigeon converter.
"""

import argparse
import logging
import sys
from pathlib import Path

from ...core import __version__
from ...core.converter import Converter, ExportMode
from ...core.i18n import get_i18n

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class CLI:
    """Command-line interface for MarkPigeon."""

    def __init__(self):
        self.i18n = get_i18n()
        self.converter = Converter()

    def create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser."""
        t = self.i18n.t

        parser = argparse.ArgumentParser(
            prog="markpigeon",
            description=t("cli.description"),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  markpigeon document.md                    Convert single file
  markpigeon document.md --theme github     Convert with GitHub theme
  markpigeon docs/ --output dist/           Convert directory
  markpigeon *.md --zip                     Convert and create individual ZIPs
  markpigeon docs/ --batch --recursive      Convert all and create single ZIP
  markpigeon document.md --standalone       Convert to standalone HTML file
""",
        )

        # Positional arguments
        parser.add_argument("input", nargs="+", help=t("cli.input_help"))

        # Optional arguments
        parser.add_argument("-o", "--output", type=str, default=None, help=t("cli.output_help"))

        parser.add_argument("-t", "--theme", type=str, default=None, help=t("cli.theme_help"))

        parser.add_argument("-z", "--zip", action="store_true", help=t("cli.zip_help"))

        parser.add_argument("-b", "--batch", action="store_true", help=t("cli.batch_help"))

        parser.add_argument("-s", "--standalone", action="store_true", help=t("cli.standalone_help"))

        parser.add_argument("-r", "--recursive", action="store_true", help=t("cli.recursive_help"))

        parser.add_argument("--list-themes", action="store_true", help=t("cli.list_themes_help"))

        parser.add_argument(
            "--lang", type=str, choices=["en", "zh_CN"], default=None, help=t("cli.lang_help")
        )

        parser.add_argument("-v", "--verbose", action="store_true", help=t("cli.verbose_help"))

        parser.add_argument(
            "-V", "--version", action="version", version=f"MarkPigeon {__version__}"
        )

        return parser

    def run(self, args: list[str] | None = None) -> int:
        """
        Run the CLI with given arguments.

        Args:
            args: Command line arguments (defaults to sys.argv)

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        parser = self.create_parser()
        parsed = parser.parse_args(args)

        # Set language if specified
        if parsed.lang:
            self.i18n.load_locale(parsed.lang)

        # Set verbose logging
        if parsed.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        # List themes and exit
        if parsed.list_themes:
            return self._list_themes()

        # Determine export mode
        if parsed.standalone:
            export_mode = ExportMode.STANDALONE
        elif parsed.batch:
            export_mode = ExportMode.BATCH_ZIP
        elif parsed.zip:
            export_mode = ExportMode.INDIVIDUAL_ZIP
        else:
            export_mode = ExportMode.DEFAULT

        # Collect input files
        input_files = self._collect_input_files(parsed.input, parsed.recursive)

        if not input_files:
            print("Error: No Markdown files found in the specified input(s).")
            return 1

        # Determine output directory
        output_dir = Path(parsed.output) if parsed.output else None

        # Set up progress callback
        self.converter.set_progress_callback(self._progress_callback)

        # Convert files
        if len(input_files) == 1 and not parsed.batch:
            # Single file conversion
            result = self.converter.convert_file(
                input_files[0], output_dir, parsed.theme, export_mode
            )

            if result.success:
                self._print_success(result)
                return 0
            else:
                self._print_error(result)
                return 1
        else:
            # Batch conversion
            if output_dir is None:
                # Use first file's parent as output
                output_dir = input_files[0].parent

            batch_result = self.converter.convert_batch(
                input_files, output_dir, parsed.theme, export_mode
            )

            self._print_batch_result(batch_result)
            return 0 if batch_result.failed == 0 else 1

    def _collect_input_files(self, inputs: list[str], recursive: bool) -> list[Path]:
        """Collect all Markdown files from inputs."""
        files = []

        for input_path in inputs:
            path = Path(input_path)

            if path.is_file():
                if path.suffix.lower() in (".md", ".markdown"):
                    files.append(path)
                else:
                    logger.warning(f"Skipping non-Markdown file: {path}")
            elif path.is_dir():
                pattern = "**/*.md" if recursive else "*.md"
                files.extend(path.glob(pattern))
                pattern_alt = "**/*.markdown" if recursive else "*.markdown"
                files.extend(path.glob(pattern_alt))
            else:
                # Handle glob patterns
                import glob

                matched = glob.glob(input_path)
                for m in matched:
                    mp = Path(m)
                    if mp.is_file() and mp.suffix.lower() in (".md", ".markdown"):
                        files.append(mp)

        return sorted(set(files))

    def _progress_callback(self, current: int, total: int, message: str) -> None:
        """Display progress."""
        print(f"[{current}/{total}] {message}")

    def _list_themes(self) -> int:
        """List available themes."""
        themes = self.converter.get_available_themes()

        if themes:
            print("Available themes:")
            for theme in themes:
                print(f"  - {theme}")
        else:
            print("No themes found. Add .css files to the 'themes' directory.")

        return 0

    def _print_success(self, result) -> None:
        """Print success message for single file conversion."""
        print(f"✓ Converted: {result.input_file.name}")

        if result.output_file:
            print(f"  Output: {result.output_file}")

        if result.zip_file:
            print(f"  ZIP: {result.zip_file}")

        if result.warnings:
            print("  Warnings:")
            for warning in result.warnings:
                print(f"    - {warning}")

    def _print_error(self, result) -> None:
        """Print error message for failed conversion."""
        print(f"✗ Failed: {result.input_file.name}")
        if result.error:
            print(f"  Error: {result.error}")

    def _print_batch_result(self, batch_result) -> None:
        """Print batch conversion results."""
        print()
        print("=" * 50)
        print("Conversion Complete")
        print("=" * 50)
        print(f"Total:      {batch_result.total}")
        print(f"Successful: {batch_result.successful}")
        print(f"Failed:     {batch_result.failed}")

        if batch_result.batch_zip:
            print(f"\nBatch ZIP: {batch_result.batch_zip}")

        # Show failed files
        failed = [r for r in batch_result.results if not r.success]
        if failed:
            print("\nFailed files:")
            for result in failed:
                print(f"  - {result.input_file.name}: {result.error}")


def main(args: list[str] | None = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        args: Command line arguments

    Returns:
        Exit code
    """
    try:
        cli = CLI()
        return cli.run(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
