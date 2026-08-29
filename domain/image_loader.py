"""
Image Loader Module.

Handles loading image files of various formats (JPG, PNG, WEBP, HEIC, HEIF, TIFF, RAW),
applying EXIF orientation transpose, and handling corrupted or unsupported files gracefully.
Never modifies original files.
"""

import logging
from pathlib import Path

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# Register pillow-heif if available
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pillow_heif = None

# Check rawpy availability
try:
    import rawpy
except ImportError:
    rawpy = None

# Check tifffile availability
try:
    import tifffile
except ImportError:
    tifffile = None

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp",
    ".heic", ".heif",
    ".tif", ".tiff",
    ".cr2", ".nef", ".arw", ".dng", ".orf", ".rw2", ".pef", ".raf"
}


def is_supported_image(file_path: Path) -> bool:
    """Check if the file extension is in the supported set."""
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS


def _load_raw_image(path: Path) -> Image.Image | None:
    """
    Robust RAW image loader (.ARW, .CR2, .NEF, .DNG, etc.).
    Uses rawpy thumbnail extraction, rawpy postprocessing, or binary JPEG header extraction.
    """
    if rawpy is not None:
        try:
            with rawpy.imread(str(path)) as raw:
                try:
                    thumb = raw.extract_thumb()
                    if thumb.format == rawpy.ThumbFormat.JPEG:
                        import io
                        img = Image.open(io.BytesIO(thumb.data))
                        img.load()
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        return ImageOps.exif_transpose(img)
                    elif thumb.format == rawpy.ThumbFormat.BITMAP:
                        img = Image.fromarray(thumb.data)
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        return ImageOps.exif_transpose(img)
                except Exception:
                    pass
                # Postprocess RAW image
                rgb = raw.postprocess(use_camera_wb=True, half_size=True)
                img = Image.fromarray(rgb)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                return ImageOps.exif_transpose(img)
        except Exception as e:
            logger.warning(f"rawpy load failed for {path}: {e}")

    # Fallback: Extract embedded JPEG bytes directly from RAW file container
    try:
        data = path.read_bytes()
        start_idx = data.find(b"\xff\xd8\xff")
        if start_idx != -1:
            end_idx = data.rfind(b"\xff\xd9")
            if end_idx != -1 and end_idx > start_idx:
                jpeg_bytes = data[start_idx : end_idx + 2]
                import io
                img = Image.open(io.BytesIO(jpeg_bytes))
                img.load()
                if img.mode != "RGB":
                    img = img.convert("RGB")
                return ImageOps.exif_transpose(img)
    except Exception as e:
        logger.warning(f"Binary JPEG extraction failed for RAW file {path}: {e}")

    return None


def load_image(file_path: Path) -> tuple[Image.Image | None, str | None]:
    """
    Loads an image file, applies EXIF transpose, and returns (PIL.Image, error_message).
    If loading fails or file is corrupted, returns (None, error_str).
    Original file is NEVER modified.
    """
    path = Path(file_path)
    if not path.exists():
        return None, f"File not found: {path}"

    ext = path.suffix.lower()

    try:
        # 1. RAW formats handling (.ARW, .CR2, .NEF, .DNG, etc.)
        if ext in {".cr2", ".nef", ".arw", ".dng", ".orf", ".rw2", ".pef", ".raf"}:
            raw_img = _load_raw_image(path)
            if raw_img is not None:
                return raw_img, None

        # 2. TIFF handling via tifffile if standard Pillow fails or for tifffile priority
        if ext in {".tif", ".tiff"} and tifffile is not None:
            try:
                arr = tifffile.imread(str(path))
                img = Image.fromarray(arr)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                return ImageOps.exif_transpose(img), None
            except Exception:
                pass  # Fall through to Pillow

        # 3. Standard Pillow opening (including HEIF/HEIC if registered)
        with Image.open(path) as img:
            img.load()  # Verify image integrity
            # Apply EXIF transpose so phone photos are oriented upright for face detection
            transposed = ImageOps.exif_transpose(img)
            # Convert to RGB if needed (e.g. RGBA, CMYK, P, L)
            if transposed.mode != "RGB":
                transposed = transposed.convert("RGB")
            return transposed, None

    except Exception as e:
        logger.warning(f"Failed to load image {path}: {e}")
        return None, f"Corrupted or unreadable image: {e!s}"
