# Test fixtures and configuration
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_descriptions():
    """Sample product descriptions from various retailers."""
    return {
        "aritzia_maxi": (
            "Do you Santorini? This is a bias-cut cowlneck maxi dress with "
            "twist shoulder details. It's made with Studio Drape — drapey "
            "matte satin with a smooth look and lightweight feel."
        ),
        "hm_slip": (
            "Slip into something satin. This is a slim-fit V-neck slip dress "
            "with lace trim and adjustable spaghetti straps. Made with "
            "recycled polyester."
        ),
        "zara_minimal": (
            "FITTED DRESS. Straight neckline. Thin straps. Side slit at hem."
        ),
        "gap_blouse": (
            "Modern fit. Cotton blend. Button-front blouse with chest pocket. "
            "Long sleeves with button cuffs."
        ),
        "nordstrom_jacket": (
            "A classic blazer updated with modern tailoring. Single-breasted "
            "with notch lapels. Two-button closure. Fully lined."
        ),
    }


@pytest.fixture
def minimal_png_bytes():
    """Minimal valid PNG image bytes."""
    return bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
        0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x05, 0xFE,
        0xD4, 0xAA, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45,  # IEND chunk
        0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
    ])


@pytest.fixture
def temp_image_file(tmp_path, minimal_png_bytes):
    """Create a temporary PNG file."""
    img_path = tmp_path / "test_image.png"
    img_path.write_bytes(minimal_png_bytes)
    return img_path
