"""Configuration management for Fashion Try-On pipeline."""

from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ComfyUIConfig(BaseModel):
    """ComfyUI connection settings."""
    host: str = "127.0.0.1"
    port: int = 8188
    
    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class GenerationConfig(BaseModel):
    """Image generation settings."""
    model: str = "qwen"  # "qwen", "flux_kontext", or "inpaint"
    steps: int = 4  # Lightning LoRA optimized
    cfg: float = 1.0
    seed: int | None = None  # None = random


class RefinementConfig(BaseModel):
    """Refinement loop settings."""
    max_iterations: int = 5
    target_score: float = 9.5
    decline_threshold: int = 2  # Stop if score declines this many times


class PipelineConfig(BaseSettings):
    """Main pipeline configuration."""
    
    # Paths
    output_dir: Path = Path("output/sessions")
    comfyui_input_dir: Path = Path(r"C:\Users\tzong\Src\ComfyUI\input")
    
    # Sub-configs
    comfyui: ComfyUIConfig = Field(default_factory=ComfyUIConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    refinement: RefinementConfig = Field(default_factory=RefinementConfig)
    
    # Azure OpenAI (loaded from .env)
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None
    
    class Config:
        env_file = ".env"
        env_prefix = ""
        extra = "ignore"


def load_config() -> PipelineConfig:
    """Load configuration from environment and defaults."""
    return PipelineConfig()
