"""Critique and scoring models."""

from pydantic import BaseModel, Field, computed_field


class ScoreBreakdown(BaseModel):
    """Detailed scoring across evaluation dimensions."""
    
    pose_preservation: int = Field(ge=1, le=10, description="CRITICAL: Was the original pose, background, and camera angle preserved? 1-3 if pose changed")
    silhouette_accuracy: int = Field(ge=1, le=10, description="How well the silhouette matches")
    fabric_appearance: int = Field(ge=1, le=10, description="Fabric texture/drape accuracy")
    color_fidelity: int = Field(ge=1, le=10, description="Color matching accuracy")
    pattern_accuracy: int = Field(ge=1, le=10, description="Pattern reproduction accuracy - CRITICAL: must match source garment exactly")
    fit_and_drape: int = Field(ge=1, le=10, description="How naturally it fits the model")
    detail_preservation: int = Field(ge=1, le=10, description="Small details preserved")
    overall_realism: int = Field(ge=1, le=10, description="Overall photo-realism")
    editorial_quality: int = Field(ge=1, le=10, description="Vogue-worthy presentation")
    
    @computed_field
    @property
    def average(self) -> float:
        """Calculate weighted average score."""
        scores = [
            self.pose_preservation,
            self.silhouette_accuracy,
            self.fabric_appearance,
            self.color_fidelity,
            self.pattern_accuracy,
            self.fit_and_drape,
            self.detail_preservation,
            self.overall_realism,
            self.editorial_quality,
        ]
        return round(sum(scores) / len(scores), 1)


class CritiqueResult(BaseModel):
    """Full critique output from the adversarial critic."""
    
    scores: ScoreBreakdown
    
    # Pose preservation is absolutely critical - any change is a failure
    pose_preserved: bool = Field(
        default=True,
        description="Whether the original pose, background, and camera angle are preserved"
    )
    pose_issues: str | None = Field(
        default=None,
        description="Description of pose/background changes if any"
    )
    
    # Pattern fidelity is critical - flag explicitly when pattern doesn't match
    pattern_matches_source: bool = Field(
        default=True, 
        description="Whether the generated pattern matches the source garment"
    )
    pattern_issues: str | None = Field(
        default=None, 
        description="Description of pattern mismatch if any (e.g., 'generated stripes instead of florals')"
    )
    
    strengths: list[str] = Field(default_factory=list, description="What's working well")
    weaknesses: list[str] = Field(default_factory=list, description="What needs improvement")
    specific_fixes: list[str] = Field(default_factory=list, description="Actionable prompt adjustments")
    
    should_continue: bool = Field(description="Whether another iteration would help")
    reasoning: str = Field(description="Explanation for the recommendation")
    
    @computed_field
    @property
    def overall_score(self) -> float:
        """The main score to track. Pose/pattern failures heavily penalize."""
        base_score = self.scores.average
        # If pose changed, cap score at 4.0 - this is a critical failure
        if not self.pose_preserved:
            return min(base_score, 4.0)
        # If pattern doesn't match source, cap score at 5.0
        if not self.pattern_matches_source:
            return min(base_score, 5.0)
        return base_score
