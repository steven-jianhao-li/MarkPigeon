"""
MarkPigeon HTML Renderer Module

Renders HTML with theme injection and smart asset isolation.
"""

import hashlib
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .parser import ImageInfo, ParseResult

logger = logging.getLogger(__name__)


@dataclass
class RenderResult:
    """Result of rendering HTML."""

    html: str  # Final HTML content
    output_file: Path | None = None  # Path to output HTML file
    assets_dir: Path | None = None  # Path to assets directory
    copied_images: list[Path] = field(default_factory=list)  # List of copied image paths
    warnings: list[str] = field(default_factory=list)  # Warning messages
    success: bool = True


class HtmlRenderer:
    """
    Renders parsed Markdown to styled HTML with asset management.

    Features:
    - Theme CSS injection (inline for portability)
    - Smart asset isolation (copies images to dedicated folder)
    - Placeholder image generation for missing files
    - Path conflict handling with hash suffixes
    """

    # HTML template
    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
{css}
    </style>
</head>
<body>
    <article class="markdown-body">
{content}
    </article>
</body>
</html>"""

    # Default CSS when no theme is specified
    DEFAULT_CSS = """
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    line-height: 1.6;
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem;
    color: #24292e;
}
.markdown-body { box-sizing: border-box; }
h1, h2, h3, h4, h5, h6 { margin-top: 24px; margin-bottom: 16px; font-weight: 600; }
h1 { font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
h2 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
code { background-color: rgba(27, 31, 35, 0.05); padding: 0.2em 0.4em; border-radius: 3px; font-size: 85%; }
pre { background-color: #f6f8fa; padding: 16px; overflow: auto; border-radius: 6px; }
pre code { background: none; padding: 0; }
blockquote { margin: 0; padding: 0 1em; color: #6a737d; border-left: 0.25em solid #dfe2e5; }
table { border-collapse: collapse; width: 100%; }
th, td { padding: 6px 13px; border: 1px solid #dfe2e5; }
tr:nth-child(2n) { background-color: #f6f8fa; }
img { max-width: 100%; height: auto; }
a { color: #0366d6; text-decoration: none; }
a:hover { text-decoration: underline; }
"""

    def __init__(self, themes_dir: Path | None = None, user_themes_dir: Path | None = None):
        """
        Initialize the renderer.

        Args:
            themes_dir: Directory containing bundled CSS theme files.
            user_themes_dir: Directory containing user CSS theme files.
                            User themes take priority over bundled themes.
        """
        if themes_dir is None:
            self.themes_dir = Path(__file__).parent.parent.parent.parent / "themes"
        else:
            self.themes_dir = Path(themes_dir)
        
        # User themes directory (optional)
        self.user_themes_dir = Path(user_themes_dir) if user_themes_dir else None

    def get_available_themes(self) -> list[str]:
        """Get list of available theme names (merged from bundled and user themes)."""
        themes = set()
        
        # Get bundled themes
        if self.themes_dir.exists():
            themes.update(f.stem for f in self.themes_dir.glob("*.css"))
        
        # Get user themes (these will appear in addition to bundled ones)
        if self.user_themes_dir and self.user_themes_dir.exists():
            themes.update(f.stem for f in self.user_themes_dir.glob("*.css"))
        
        return sorted(themes)

    def load_theme_css(self, theme_name: str | None = None) -> str:
        """
        Load CSS content for a theme.

        Args:
            theme_name: Name of the theme (without .css extension).
                       If None, returns default CSS.

        Returns:
            CSS content string.
        """
        if theme_name is None:
            return self.DEFAULT_CSS

        # Check user themes first (user themes have priority)
        if self.user_themes_dir:
            user_theme_file = self.user_themes_dir / f"{theme_name}.css"
            if user_theme_file.exists():
                try:
                    return user_theme_file.read_text(encoding="utf-8")
                except Exception as e:
                    logger.error(f"Failed to load user theme {theme_name}: {e}")
        
        # Fall back to bundled themes
        theme_file = self.themes_dir / f"{theme_name}.css"

        if not theme_file.exists():
            logger.warning(f"Theme not found: {theme_name}, using default")
            return self.DEFAULT_CSS

        try:
            return theme_file.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to load theme {theme_name}: {e}")
            return self.DEFAULT_CSS

    def render(
        self,
        parse_result: ParseResult,
        output_dir: Path,
        theme_name: str | None = None,
        title: str | None = None,
        lang: str = "en",
    ) -> RenderResult:
        """
        Render parsed Markdown to a complete HTML file with assets.

        Args:
            parse_result: Result from MarkdownParser
            output_dir: Directory to write output files
            theme_name: Optional theme name to use
            title: Optional document title (defaults to filename)
            lang: HTML lang attribute

        Returns:
            RenderResult with output information.
        """
        result = RenderResult(html="")
        output_dir = Path(output_dir)

        # Determine output filename
        if parse_result.source_file:
            base_name = parse_result.source_file.stem
        else:
            base_name = "document"

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create assets directory
        assets_dir_name = f"assets_{base_name}"
        assets_dir = output_dir / assets_dir_name

        # Process images and create path mapping
        path_mapping: dict[str, str] = {}

        if parse_result.local_images:
            assets_dir.mkdir(parents=True, exist_ok=True)
            result.assets_dir = assets_dir

            # Track used filenames to handle conflicts
            used_names: dict[str, int] = {}

            for img_info in parse_result.local_images:
                new_path = self._process_image(
                    img_info, assets_dir, assets_dir_name, used_names, result
                )
                if new_path:
                    path_mapping[img_info.original_src] = new_path

        # Update HTML with new image paths
        html_content = parse_result.html
        if path_mapping:
            from .parser import MarkdownParser

            parser = MarkdownParser()
            html_content = parser.update_image_paths(html_content, path_mapping)

        # Load theme CSS
        css = self.load_theme_css(theme_name)

        # Generate complete HTML
        doc_title = title or base_name
        result.html = self.HTML_TEMPLATE.format(
            lang=lang, title=doc_title, css=css, content=html_content
        )

        # Write output file
        output_file = output_dir / f"{base_name}.html"
        try:
            output_file.write_text(result.html, encoding="utf-8")
            result.output_file = output_file
            logger.info(f"Rendered HTML to: {output_file}")
        except Exception as e:
            result.success = False
            result.warnings.append(f"Failed to write output file: {e}")
            logger.error(f"Failed to write output file: {e}")

        # Merge warnings from parse result
        result.warnings.extend(parse_result.warnings)

        return result

    def _process_image(
        self,
        img_info: ImageInfo,
        assets_dir: Path,
        assets_dir_name: str,
        used_names: dict[str, int],
        result: RenderResult,
    ) -> str | None:
        """
        Process a single image: copy to assets dir or generate placeholder.

        Args:
            img_info: Image information
            assets_dir: Target assets directory
            assets_dir_name: Name of assets directory for relative paths
            used_names: Dict tracking used filenames
            result: RenderResult to update

        Returns:
            New relative path for the image, or None on failure.
        """
        if img_info.exists and img_info.local_path:
            # Copy existing image
            return self._copy_image(
                img_info.local_path, assets_dir, assets_dir_name, used_names, result
            )
        else:
            # Generate placeholder for missing image
            return self._generate_placeholder(
                img_info, assets_dir, assets_dir_name, used_names, result
            )

    def _copy_image(
        self,
        source_path: Path,
        assets_dir: Path,
        assets_dir_name: str,
        used_names: dict[str, int],
        result: RenderResult,
    ) -> str | None:
        """Copy an image to the assets directory."""
        filename = source_path.name
        target_filename = self._get_unique_filename(filename, source_path, used_names)
        target_path = assets_dir / target_filename

        try:
            shutil.copy2(source_path, target_path)
            result.copied_images.append(target_path)
            logger.debug(f"Copied image: {source_path} -> {target_path}")
            return f"./{assets_dir_name}/{target_filename}"
        except Exception as e:
            result.warnings.append(f"Failed to copy image {source_path}: {e}")
            logger.error(f"Failed to copy image: {e}")
            return None

    def _generate_placeholder(
        self,
        img_info: ImageInfo,
        assets_dir: Path,
        assets_dir_name: str,
        used_names: dict[str, int],
        result: RenderResult,
    ) -> str | None:
        """Generate a placeholder image for missing files."""
        # Create a simple placeholder image
        try:
            width, height = 400, 300
            img = Image.new("RGB", (width, height), color=(240, 240, 240))
            draw = ImageDraw.Draw(img)

            # Draw border
            draw.rectangle([0, 0, width - 1, height - 1], outline=(200, 200, 200), width=2)

            # Draw X
            draw.line([(50, 50), (width - 50, height - 50)], fill=(180, 180, 180), width=2)
            draw.line([(width - 50, 50), (50, height - 50)], fill=(180, 180, 180), width=2)

            # Draw text
            text = "Image Not Found"
            try:
                # Try to use a basic font
                font = ImageFont.load_default()
            except Exception:
                font = None

            # Get text bounding box
            bbox = draw.textbbox((0, 0), text, font=font) if font else (0, 0, 100, 20)
            text_width = bbox[2] - bbox[0]
            text_width = bbox[2] - bbox[0]
            # text_height = bbox[3] - bbox[1]

            x = (width - text_width) // 2
            y = height - 50
            draw.text((x, y), text, fill=(150, 150, 150), font=font)

            # Generate unique filename
            original_name = Path(img_info.original_src).stem or "missing"
            placeholder_name = f"placeholder_{original_name}.png"
            target_filename = self._get_unique_filename(placeholder_name, None, used_names)
            target_path = assets_dir / target_filename

            img.save(target_path, "PNG")
            result.copied_images.append(target_path)
            logger.info(f"Generated placeholder for: {img_info.original_src}")

            return f"./{assets_dir_name}/{target_filename}"
        except Exception as e:
            result.warnings.append(f"Failed to generate placeholder: {e}")
            logger.error(f"Failed to generate placeholder: {e}")
            return None

    def _get_unique_filename(
        self, filename: str, source_path: Path | None, used_names: dict[str, int]
    ) -> str:
        """
        Get a unique filename, adding hash suffix if there's a conflict.

        Args:
            filename: Original filename
            source_path: Source file path (for hash generation)
            used_names: Dict tracking used names

        Returns:
            Unique filename.
        """
        if filename not in used_names:
            used_names[filename] = 1
            return filename

        # Conflict - add hash suffix
        stem = Path(filename).stem
        suffix = Path(filename).suffix

        if source_path:
            # Use file content hash for consistency
            try:
                file_hash = hashlib.md5(source_path.read_bytes()).hexdigest()[:8]
            except Exception:
                file_hash = hashlib.md5(str(source_path).encode()).hexdigest()[:8]
        else:
            # Use counter for placeholders
            file_hash = f"{used_names[filename]:04d}"

        used_names[filename] += 1
        return f"{stem}_{file_hash}{suffix}"


def render_to_html(
    parse_result: ParseResult, output_dir: Path, theme_name: str | None = None
) -> RenderResult:
    """
    Convenience function to render parsed Markdown to HTML.

    Args:
        parse_result: Result from MarkdownParser
        output_dir: Output directory
        theme_name: Optional theme name

    Returns:
        RenderResult object.
    """
    renderer = HtmlRenderer()
    return renderer.render(parse_result, output_dir, theme_name)
