"""API endpoint tests using FastAPI TestClient."""

import pytest
import base64
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from api.server import app


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Root endpoint returns OK status."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "version" in data
    
    def test_health_endpoint(self, client):
        """Health endpoint returns status info."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "comfyui" in data


class TestTryOnEndpoint:
    """Tests for the main try-on endpoint."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def sample_image_base64(self):
        """Create a minimal valid PNG image as base64."""
        # Minimal 1x1 red PNG
        png_data = bytes([
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
        return f"data:image/png;base64,{base64.b64encode(png_data).decode()}"
    
    def test_tryon_missing_garment_photo(self, client):
        """Request without garment_photo returns error."""
        response = client.post("/api/tryon", json={
            "model_photo": "data:image/png;base64,abc123",
            "description": "Test dress"
        })
        
        # Should fail validation
        assert response.status_code == 422
    
    def test_tryon_missing_model_photo(self, client):
        """Request without model_photo returns error."""
        response = client.post("/api/tryon", json={
            "garment_photo": "data:image/png;base64,abc123",
            "description": "Test dress"
        })
        
        # Should fail validation
        assert response.status_code == 422
    
    def test_tryon_request_format(self, client, sample_image_base64):
        """Valid request format is accepted (may fail at pipeline level)."""
        with patch('api.server.get_pipeline') as mock_pipeline:
            # Mock the pipeline
            mock_instance = MagicMock()
            mock_instance.run_from_base64 = AsyncMock(
                return_value=b'\x89PNG\r\n\x1a\n...'  # Fake PNG bytes
            )
            mock_pipeline.return_value = mock_instance
            
            response = client.post("/api/tryon", json={
                "garment_photo": sample_image_base64,
                "model_photo": sample_image_base64,
                "description": "Black slip dress"
            })
            
            # Should accept the request
            assert response.status_code == 200
            data = response.json()
            assert "success" in data


class TestAPIResponseFormat:
    """Tests for API response format consistency."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_success_response_format(self, client):
        """Successful response has expected fields."""
        with patch('api.server.get_pipeline') as mock_pipeline:
            mock_instance = MagicMock()
            mock_instance.run_from_base64 = AsyncMock(
                return_value=b'\x89PNG\r\n\x1a\n'
            )
            mock_pipeline.return_value = mock_instance
            
            # Minimal valid PNG
            png_b64 = base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()
            
            response = client.post("/api/tryon", json={
                "garment_photo": f"data:image/png;base64,{png_b64}",
                "model_photo": f"data:image/png;base64,{png_b64}",
                "description": "Test"
            })
            
            data = response.json()
            assert "success" in data
            if data["success"]:
                assert "image_base64" in data
    
    def test_error_response_format(self, client):
        """Error response has expected fields."""
        with patch('api.server.get_pipeline') as mock_pipeline:
            mock_instance = MagicMock()
            mock_instance.run_from_base64 = AsyncMock(
                side_effect=Exception("Test error")
            )
            mock_pipeline.return_value = mock_instance
            
            png_b64 = base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()
            
            response = client.post("/api/tryon", json={
                "garment_photo": f"data:image/png;base64,{png_b64}",
                "model_photo": f"data:image/png;base64,{png_b64}",
            })
            
            data = response.json()
            assert "success" in data
            assert data["success"] == False
            assert "error" in data
