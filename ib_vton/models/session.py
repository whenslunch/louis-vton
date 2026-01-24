"""Session and iteration tracking models."""

from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field, computed_field

from .garment import GarmentSpec
from .critique import CritiqueResult


class IterationResult(BaseModel):
    """Result of a single refinement iteration."""
    
    iteration: int
    prompt: str
    image_path: Path
    critique: CritiqueResult | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @computed_field
    @property
    def score(self) -> float | None:
        """Convenience accessor for the score."""
        return self.critique.overall_score if self.critique else None


class TryOnSession(BaseModel):
    """Complete session state for a try-on run."""
    
    session_id: str
    session_dir: Path
    
    # Inputs
    garment_images: list[Path]
    model_image: Path
    
    # Analysis
    garment_spec: GarmentSpec | None = None
    
    # Iterations
    iterations: list[IterationResult] = Field(default_factory=list)
    
    # Status
    status: str = "initialized"  # initialized, running, completed, failed
    final_message: str | None = None
    
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    
    @computed_field
    @property
    def best_iteration(self) -> IterationResult | None:
        """Get the iteration with the highest score."""
        scored = [i for i in self.iterations if i.score is not None]
        if not scored:
            return self.iterations[-1] if self.iterations else None
        return max(scored, key=lambda i: i.score)  # type: ignore
    
    @computed_field
    @property
    def best_score(self) -> float | None:
        """Get the best score achieved."""
        best = self.best_iteration
        return best.score if best else None
    
    def add_iteration(self, prompt: str, image_path: Path) -> IterationResult:
        """Add a new iteration result."""
        result = IterationResult(
            iteration=len(self.iterations) + 1,
            prompt=prompt,
            image_path=image_path,
        )
        self.iterations.append(result)
        return result
    
    def save(self) -> Path:
        """Save session state to JSON."""
        path = self.session_dir / "session.json"
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return path
