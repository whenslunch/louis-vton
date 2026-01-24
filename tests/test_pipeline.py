"""Integration tests for full pipeline execution."""

import pytest
import base64
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from louis_vton.pipeline import TryOnPipeline
from louis_vton.config import PipelineConfig


class TestPipelineInitialization:
    """Tests for pipeline initialization."""
    
    def test_pipeline_creates_with_config(self):
        """Pipeline initializes with config."""
        config = PipelineConfig()
        pipeline = TryOnPipeline(config)
        
        assert pipeline.config is not None
        assert pipeline.comfyui is not None
        assert pipeline.prompt_generator is not None
        assert pipeline.garment_extractor is not None
    
    def test_pipeline_has_required_methods(self):
        """Pipeline exposes required methods."""
        config = PipelineConfig()
        pipeline = TryOnPipeline(config)
        
        assert hasattr(pipeline, 'run')
        assert hasattr(pipeline, 'run_from_base64')
        assert callable(pipeline.run)
        assert callable(pipeline.run_from_base64)


class TestPipelineImageConversion:
    """Tests for image format handling."""
    
    def test_decode_base64_with_data_url(self):
        """Base64 data URLs are correctly decoded."""
        # Minimal PNG header
        png_bytes = b'\x89PNG\r\n\x1a\n'
        b64 = base64.b64encode(png_bytes).decode()
        data_url = f"data:image/png;base64,{b64}"
        
        # Test the decoding logic
        if data_url.startswith("data:"):
            _, encoded = data_url.split(",", 1)
            decoded = base64.b64decode(encoded)
        
        assert decoded == png_bytes
    
    def test_decode_base64_raw(self):
        """Raw base64 is correctly decoded."""
        png_bytes = b'\x89PNG\r\n\x1a\n'
        b64 = base64.b64encode(png_bytes).decode()
        
        decoded = base64.b64decode(b64)
        
        assert decoded == png_bytes


class TestPipelineWithMocks:
    """Tests for pipeline with mocked dependencies."""
    
    @pytest.fixture
    def mock_pipeline(self):
        """Create pipeline with mocked ComfyUI."""
        config = PipelineConfig()
        pipeline = TryOnPipeline(config)
        
        # Mock ComfyUI client
        pipeline.comfyui.check_connection = AsyncMock(return_value=True)
        pipeline.comfyui.generate_tryon = AsyncMock(return_value=None)
        
        return pipeline
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_run_creates_session(self, mock_pipeline, tmp_path):
        """Pipeline run creates a session."""
        # Create test images
        garment_img = tmp_path / "garment.png"
        model_img = tmp_path / "model.png"
        
        # Minimal PNG
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        garment_img.write_bytes(png_data)
        model_img.write_bytes(png_data)
        
        # Mock the output creation
        async def mock_generate(*args, **kwargs):
            output_path = kwargs.get('output_path') or args[3]
            output_path.write_bytes(png_data)
        
        mock_pipeline.comfyui.generate_tryon = AsyncMock(side_effect=mock_generate)
        
        session = await mock_pipeline.run(
            garment_image=garment_img,
            model_image=model_img,
            description="Test black dress"
        )
        
        assert session is not None
        assert session.status == "completed"


class TestRetailerDescriptions:
    """Tests for various retailer description formats."""
    
    @pytest.mark.parametrize("description,should_contain", [
        # Aritzia style
        (
            "Do you Santorini? This is a bias-cut cowlneck maxi dress with twist shoulder details.",
            "dress"
        ),
        # H&M style  
        (
            "Slip into something satin. This is a slim-fit V-neck slip dress with lace trim.",
            "dress"
        ),
        # Zara style (minimal)
        (
            "FITTED DRESS. Straight neckline. Thin straps.",
            "dress"
        ),
        # Gap style
        (
            "Modern fit. Cotton blend. Button-front blouse with chest pocket.",
            "blouse"
        ),
    ])
    def test_description_parsing(self, description, should_contain):
        """Various retailer descriptions are handled."""
        from louis_vton.agents.flux_prompt_generator import FluxPromptGeneratorAgent
        
        generator = FluxPromptGeneratorAgent()
        prompt = generator.generate_simple(description, "person")
        
        assert should_contain in prompt.lower()
