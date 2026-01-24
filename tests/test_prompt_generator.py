"""Unit tests for FluxPromptGeneratorAgent - prompt generation."""

import pytest
from louis_vton.agents.flux_prompt_generator import FluxPromptGeneratorAgent
from louis_vton.agents.garment_extractor import GarmentAttributes


class TestPromptGeneratorSimple:
    """Tests for simple/template-based prompt generation."""
    
    @pytest.fixture
    def generator(self):
        return FluxPromptGeneratorAgent()
    
    def test_generate_simple_with_dress(self, generator):
        """Simple prompt includes dress type."""
        prompt = generator.generate_simple(
            garment_description="A dusty turquoise pleated maxi dress with V-neckline",
            person_description="person"
        )
        
        assert "maxi dress" in prompt.lower()
        assert "person" in prompt.lower()
        assert "reference image 1" in prompt.lower()
        assert "reference image 2" in prompt.lower()
    
    def test_generate_simple_with_color(self, generator):
        """Simple prompt extracts and includes color."""
        prompt = generator.generate_simple(
            garment_description="Black satin slip dress",
            person_description="person"
        )
        
        assert "black" in prompt.lower()
        assert "dress" in prompt.lower()
    
    def test_generate_simple_preserves_identity(self, generator):
        """Prompt includes identity preservation language."""
        prompt = generator.generate_simple(
            garment_description="Red dress",
            person_description="person"
        )
        
        assert "face" in prompt.lower()
        assert "hair" in prompt.lower()
        assert "background" in prompt.lower()
        assert "preserve" in prompt.lower() or "keep" in prompt.lower()
    
    def test_generate_simple_no_generic_garment(self, generator):
        """Should not use generic 'garment' when type is known."""
        prompt = generator.generate_simple(
            garment_description="A beautiful silk blouse with pearl buttons",
            person_description="person"
        )
        
        # Should use specific type, not generic "garment"
        assert "blouse" in prompt.lower()
    
    @pytest.mark.parametrize("desc,expected_type", [
        ("Maxi dress with pleats", "maxi dress"),
        ("Silk blouse", "blouse"),
        ("Denim jacket", "jacket"),
        ("Wide-leg pants", "pants"),
        ("Pleated skirt", "skirt"),
    ])
    def test_generate_simple_detects_types(self, generator, desc, expected_type):
        """Various garment types are correctly detected."""
        prompt = generator.generate_simple(desc, "person")
        assert expected_type in prompt.lower()


class TestPromptGeneratorFromAttributes:
    """Tests for attribute-based prompt generation."""
    
    @pytest.fixture
    def generator(self):
        return FluxPromptGeneratorAgent()
    
    def test_from_attributes_full(self, generator):
        """Full attributes produce detailed prompt."""
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
        
        prompt = generator.generate_from_attributes(attrs)
        
        assert "dusty turquoise" in prompt.lower()
        assert "maxi dress" in prompt.lower()
        assert "v-neck" in prompt.lower()
        assert "satin" in prompt.lower()
    
    def test_from_attributes_minimal(self, generator):
        """Minimal attributes still produce valid prompt."""
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
        
        prompt = generator.generate_from_attributes(attrs)
        
        assert "dress" in prompt.lower()
        assert "reference image 1" in prompt.lower()
        assert "reference image 2" in prompt.lower()
    
    def test_from_attributes_identity_preservation(self, generator):
        """Attribute-based prompt preserves identity."""
        attrs = GarmentAttributes(
            garment_type="blouse",
            color="white",
            fabric="cotton",
            neckline=None,
            sleeves=None,
            length=None,
            fit=None,
            details=[]
        )
        
        prompt = generator.generate_from_attributes(attrs)
        
        assert "face" in prompt.lower()
        assert "hair" in prompt.lower()
        assert "pose" in prompt.lower()
        assert "background" in prompt.lower()


class TestPromptQuality:
    """Tests for overall prompt quality."""
    
    @pytest.fixture
    def generator(self):
        return FluxPromptGeneratorAgent()
    
    def test_prompt_not_too_long(self, generator):
        """Prompts should be reasonable length."""
        attrs = GarmentAttributes(
            garment_type="maxi dress",
            color="black",
            fabric="silk",
            neckline="V-neck",
            sleeves="long sleeves",
            length="maxi",
            fit="fitted",
            details=["lace trim", "buttons", "embroidery", "ruching"]
        )
        
        prompt = generator.generate_from_attributes(attrs)
        
        # Should be under 1000 characters
        assert len(prompt) < 1000
    
    def test_prompt_no_markdown(self, generator):
        """Prompts should not contain markdown."""
        prompt = generator.generate_simple("Black dress", "person")
        
        assert "**" not in prompt
        assert "```" not in prompt
        assert "#" not in prompt
    
    def test_prompt_no_questions(self, generator):
        """Prompts should not contain questions."""
        prompt = generator.generate_simple("Silk blouse", "person")
        
        assert "?" not in prompt
