"""FastAPI server for Virtual Try-On.

Receives requests from browser extension with:
- garment_url: URL of the garment image
- model_photo: Base64-encoded photo of the user
- description: Optional product description from the website
"""

import base64
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ib_vton.config import PipelineConfig
from ib_vton.pipeline import TryOnPipeline


app = FastAPI(
    title="IB-VTON API",
    description="In-Browser Virtual Try-On using FLUX 2 Klein",
    version="2.0.0",
)

# Enable CORS for browser extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for extension
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TryOnRequest(BaseModel):
    """Request body for try-on generation."""
    garment_photo: str  # Base64 data URL (preferred) - fetched by extension
    garment_url: str | None = None  # Deprecated - kept for backwards compatibility
    model_photo: str  # Base64 data URL
    description: str | None = None


class TryOnResponse(BaseModel):
    """Response with generated image."""
    success: bool
    image_base64: str | None = None
    error: str | None = None
    session_id: str | None = None


# Initialize pipeline (will be done on first request)
_pipeline: TryOnPipeline | None = None


def get_pipeline() -> TryOnPipeline:
    """Get or create the pipeline instance."""
    global _pipeline
    if _pipeline is None:
        config = PipelineConfig()  # Loads from .env automatically via pydantic-settings
        _pipeline = TryOnPipeline(config)
    return _pipeline


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Virtual Try-On API", "version": "2.0.0"}


@app.get("/health")
async def health():
    """Detailed health check."""
    pipeline = get_pipeline()
    comfyui_ok = await pipeline.comfyui.check_connection()
    
    return {
        "status": "ok" if comfyui_ok else "degraded",
        "comfyui": "connected" if comfyui_ok else "disconnected",
    }


@app.post("/api/tryon", response_model=TryOnResponse)
async def generate_tryon(request: TryOnRequest):
    """Generate a virtual try-on image.
    
    Args:
        request: Contains garment photo (base64), model photo (base64), and optional description
        
    Returns:
        Base64-encoded PNG image of the try-on result
    """
    try:
        pipeline = get_pipeline()
        
        # Run the pipeline with base64 images
        result_bytes = await pipeline.run_from_base64(
            garment_photo_base64=request.garment_photo,
            model_photo_base64=request.model_photo,
            description=request.description,
        )
        
        # Encode result as base64
        result_base64 = base64.b64encode(result_bytes).decode("utf-8")
        
        return TryOnResponse(
            success=True,
            image_base64=result_base64,
        )
        
    except Exception as e:
        return TryOnResponse(
            success=False,
            error=str(e),
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
