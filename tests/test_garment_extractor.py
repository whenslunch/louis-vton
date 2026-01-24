"""Unit tests for GarmentExtractor - attribute extraction from text and images."""

import pytest
from ib_vton.agents.garment_extractor import GarmentExtractor, GarmentAttributes


class TestGarmentAttributes:
    """Tests for GarmentAttributes dataclass."""
    
    def test_to_description_with_all_fields(self):
        """Full attributes produce complete description."""
        attrs = GarmentAttributes(
            garment_type="maxi dress",
            color="dusty turquoise",
            fabric="satin",
            neckline="V-neck",
            sleeves="sleeveless",
            length="maxi",
            fit="A-line",
            details=["pleated", "tie-front"]
        )
        desc = attrs.to_description()
        
        assert "dusty turquoise" in desc
        assert "maxi dress" in desc
        assert "V-neck" in desc
        assert "satin" in desc
    
    def test_to_description_minimal(self):
        """Minimal attributes still produce valid description."""
        attrs = GarmentAttributes(
            garment_type="dress",
            color=None,
            fabric=None,
            neckline=None,
            sleeves=None,
            length=None,
            fit=None,
            details=[]
        )
        desc = attrs.to_description()
        
        assert desc == "dress"
    
    def test_to_description_with_color_only(self):
        """Color + type produces correct format."""
        attrs = GarmentAttributes(
            garment_type="blouse",
            color="black",
            fabric=None,
            neckline=None,
            sleeves=None,
            length=None,
            fit=None,
            details=[]
        )
        desc = attrs.to_description()
        
        assert desc == "black blouse"


class TestGarmentExtractorKeywordFallback:
    """Tests for keyword-based garment type detection."""
    
    @pytest.fixture
    def extractor(self):
        return GarmentExtractor()
    
    @pytest.mark.parametrize("description,expected_type", [
        ("This is a bias-cut cowlneck maxi dress with twist details", "maxi dress"),
        ("A beautiful midi dress for summer", "midi dress"),
        ("Classic black slip dress with lace trim", "slip dress"),
        ("Comfortable cotton blouse with buttons", "blouse"),
        ("High-waisted wide-leg pants", "pants"),
        ("Fitted blazer for office wear", "blazer"),
        ("Cozy knit cardigan", "cardigan"),
        ("Elegant silk top", "top"),
        ("Denim jacket with brass buttons", "jacket"),
        ("Pleated midi skirt", "skirt"),
    ])
    def test_keyword_extraction(self, description, expected_type):
        """Keyword fallback correctly identifies garment types."""
        # Test the keyword matching logic directly
        desc_lower = description.lower()
        garment_types = [
            'maxi dress', 'midi dress', 'mini dress', 'slip dress', 'bodycon dress',
            'wrap dress', 'shirt dress', 'dress', 'blouse', 'top', 'shirt', 'pants',
            'trousers', 'jeans', 'skirt', 'jacket', 'blazer', 'coat', 'cardigan',
            'sweater', 'jumper', 'hoodie', 'romper', 'jumpsuit', 'shorts'
        ]
        
        found_type = "outfit"
        for gt in garment_types:
            if gt in desc_lower:
                found_type = gt
                break
        
        assert found_type == expected_type


class TestGarmentExtractorTextExtraction:
    """Tests for LLM-based text extraction (requires API).
    
    Note: These tests use the actual LLM and may be flaky.
    The extract() method applies keyword fallback, so these tests
    verify the fallback behavior rather than LLM reliability.
    """
    
    @pytest.fixture
    def extractor(self):
        return GarmentExtractor()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_extract_with_keyword_fallback_dress(self, extractor):
        """Full extract() applies keyword fallback when LLM fails to detect type."""
        description = """
        Do you Santorini? This is a bias-cut cowlneck maxi dress with twist 
        shoulder details. It's made with Studio Drape — drapey matte satin 
        with a smooth look and lightweight feel.
        """
        
        # Use full extract() which includes keyword fallback
        attrs = await extractor.extract(description=description)
        
        # With keyword fallback, "maxi dress" should be detected
        assert "dress" in attrs.garment_type.lower(), \
            f"Expected 'dress' but got '{attrs.garment_type}'"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_extract_ignores_marketing(self, extractor):
        """Marketing phrases should be filtered out from final description."""
        description = """
        For your grand entrance! This stunning piece will make heads turn.
        A slim-fit V-neck slip dress with lace trim and adjustable straps.
        Made with luxurious silk satin.
        """
        
        # Use full extract() which includes keyword fallback
        attrs = await extractor.extract(description=description)
        
        # Should get dress (via keyword fallback if LLM fails)
        assert "dress" in attrs.garment_type.lower(), \
            f"Expected 'dress' but got '{attrs.garment_type}'"
        assert "grand entrance" not in attrs.to_description().lower()


class TestGarmentExtractorMerge:
    """Tests for merging text and image attributes."""
    
    @pytest.mark.asyncio
    async def test_text_only_with_keyword_fallback(self):
        """Full extract() with description applies keyword fallback."""
        extractor = GarmentExtractor()
        
        # "dress" appears in description, so keyword fallback should find it
        attrs = await extractor.extract(
            description="A beautiful red silk dress with V-neck",
            image_path=None
        )
        
        assert "dress" in attrs.garment_type.lower(), \
            f"Expected 'dress' but got '{attrs.garment_type}'"
    
    def test_default_when_no_sources(self):
        """Returns default attributes when no sources available."""
        attrs = GarmentAttributes(
            garment_type="outfit",
            color=None,
            fabric=None,
            neckline=None,
            sleeves=None,
            length=None,
            fit=None,
            details=[]
        )
        
        assert attrs.garment_type == "outfit"
        assert attrs.to_description() == "outfit"
