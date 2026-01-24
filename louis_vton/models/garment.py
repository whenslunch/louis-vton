"""Garment specification models."""

from pydantic import BaseModel, Field


class GarmentSpec(BaseModel):
    """Structured representation of an analyzed garment."""
    
    # Basic info
    garment_type: str = Field(description="e.g., 'maxi dress', 'blazer', 'blouse'")
    silhouette: str = Field(description="e.g., 'A-line', 'fitted', 'oversized'")
    
    # Fabric characteristics
    fabric_type: str = Field(description="e.g., 'cotton', 'silk', 'polyester blend'")
    fabric_weight: str = Field(description="'lightweight', 'medium', or 'heavy'")
    fabric_texture: str = Field(description="e.g., 'smooth', 'textured', 'ribbed'")
    fabric_drape: str = Field(description="e.g., 'fluid', 'structured', 'stiff'")
    fabric_sheen: str = Field(description="e.g., 'matte', 'subtle sheen', 'glossy'")
    
    # Color and pattern
    primary_color: str = Field(description="Main color of the garment")
    secondary_colors: list[str] = Field(default_factory=list)
    pattern_type: str | None = Field(default=None, description="e.g., 'solid', 'floral', 'striped'")
    pattern_description: str | None = Field(default=None)
    
    # Construction details
    neckline: str = Field(description="e.g., 'V-neck', 'crew neck', 'off-shoulder'")
    sleeves: str = Field(description="e.g., 'sleeveless', 'short', 'long', 'spaghetti straps'")
    waistline: str = Field(description="e.g., 'natural', 'empire', 'drop waist'")
    hem_length: str = Field(description="e.g., 'mini', 'midi', 'maxi', 'floor-length'")
    closure_type: str = Field(description="e.g., 'zipper', 'buttons', 'pull-on', 'tie-back'")
    
    # Notable details
    notable_details: list[str] = Field(default_factory=list)
    styling_notes: str = Field(default="", description="How it should look when worn")
    
    # Metadata
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)
    analyzed_views: list[str] = Field(default_factory=lambda: ["front"])
    
    def to_prompt_description(self) -> str:
        """Generate a text description suitable for the prompt generator."""
        parts = [
            f"a {self.fabric_weight}, {self.pattern_type or 'solid'}-print" if self.pattern_type else f"a {self.fabric_weight}",
            f"{self.silhouette} {self.garment_type}",
            f"with a {self.fabric_drape} drape",
            f"featuring a {self.neckline}",
        ]
        
        if self.sleeves != "sleeveless":
            parts.append(f"and {self.sleeves} sleeves")
        else:
            parts.append(f"and {self.sleeves} design")
            
        if self.notable_details:
            parts.append(f"; notable details include {', '.join(self.notable_details)}")
            
        return " ".join(parts)
