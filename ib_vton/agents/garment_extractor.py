"""Garment Attribute Extractor - extracts clean garment attributes from text and images."""

import base64
from pathlib import Path
from dataclasses import dataclass
from azure.identity import AzureCliCredential
from agent_framework import ChatMessage, TextContent, DataContent
from agent_framework.azure import AzureOpenAIResponsesClient


@dataclass
class GarmentAttributes:
    """Structured garment attributes extracted from description and/or image."""
    garment_type: str  # e.g., "maxi dress", "blouse", "jacket"
    color: str | None  # e.g., "dusty turquoise", "black"
    fabric: str | None  # e.g., "satin", "cotton", "linen"
    neckline: str | None  # e.g., "V-neck", "cowlneck", "off-shoulder"
    sleeves: str | None  # e.g., "sleeveless", "long sleeve", "cap sleeve"
    length: str | None  # e.g., "maxi", "midi", "mini", "cropped"
    fit: str | None  # e.g., "fitted", "relaxed", "A-line"
    details: list[str]  # e.g., ["pleated", "tie-front", "ruched"]
    
    def to_description(self) -> str:
        """Convert attributes to a clean description string for FLUX."""
        parts = []
        
        # Color + type (e.g., "dusty turquoise maxi dress")
        if self.color:
            parts.append(f"{self.color} {self.garment_type}")
        else:
            parts.append(self.garment_type)
        
        # Key features
        features = []
        if self.neckline:
            features.append(self.neckline)
        if self.fabric:
            features.append(f"{self.fabric} fabric")
        if self.sleeves:
            features.append(self.sleeves)
        if self.fit:
            features.append(f"{self.fit} fit")
        
        # Add top details
        for detail in self.details[:2]:
            if detail not in features:
                features.append(detail)
        
        if features:
            parts.append(f"with {', '.join(features[:3])}")
        
        return " ".join(parts)


TEXT_EXTRACTION_PROMPT = """Extract garment attributes from this product description. Ignore marketing phrases and focus only on factual garment details.

Return a JSON object with these fields (use null if not mentioned):
{
  "garment_type": "the type of clothing (dress, blouse, pants, jacket, etc.)",
  "color": "the color if mentioned",
  "fabric": "the fabric/material (satin, cotton, silk, etc.)",
  "neckline": "neckline style if mentioned (V-neck, cowlneck, square, etc.)",
  "sleeves": "sleeve style if mentioned",
  "length": "garment length if mentioned (maxi, midi, mini, etc.)",
  "fit": "fit style if mentioned (fitted, relaxed, A-line, etc.)",
  "details": ["list", "of", "special", "details"]
}

Return ONLY the JSON object, no explanation."""


VISION_EXTRACTION_PROMPT = """Analyze this garment image and describe its key visual attributes.

Return a JSON object with these fields (use null if you can't determine):
{
  "garment_type": "the type of clothing you see",
  "color": "the primary color",
  "fabric": "the apparent fabric/material",
  "neckline": "neckline style",
  "sleeves": "sleeve style",
  "length": "garment length",
  "fit": "how it fits (fitted, loose, etc.)",
  "details": ["list", "of", "notable", "visual", "details"]
}

Return ONLY the JSON object, no explanation."""


class GarmentExtractor:
    """Extracts clean garment attributes from text descriptions and/or images."""
    
    def __init__(self):
        """Initialize with Azure OpenAI client."""
        self.client = AzureOpenAIResponsesClient(
            credential=AzureCliCredential(),
        )
        self._text_agent = None
        self._vision_agent = None
    
    def _get_text_agent(self):
        """Lazy init for text extraction agent."""
        if self._text_agent is None:
            self._text_agent = self.client.as_agent(
                name="GarmentTextExtractor",
                instructions=TEXT_EXTRACTION_PROMPT,
            )
        return self._text_agent
    
    def _get_vision_agent(self):
        """Lazy init for vision extraction agent."""
        if self._vision_agent is None:
            self._vision_agent = self.client.as_agent(
                name="GarmentVisionExtractor",
                instructions=VISION_EXTRACTION_PROMPT,
            )
        return self._vision_agent
    
    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        import json
        
        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (```json and ```)
            text = "\n".join(lines[1:-1])
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}
    
    def _dict_to_attributes(self, data: dict) -> GarmentAttributes:
        """Convert parsed dict to GarmentAttributes."""
        return GarmentAttributes(
            garment_type=data.get("garment_type") or "outfit",
            color=data.get("color"),
            fabric=data.get("fabric"),
            neckline=data.get("neckline"),
            sleeves=data.get("sleeves"),
            length=data.get("length"),
            fit=data.get("fit"),
            details=data.get("details") or [],
        )
    
    async def extract_from_text(self, description: str) -> GarmentAttributes:
        """Extract attributes from text description only."""
        agent = self._get_text_agent()
        
        messages = [
            ChatMessage(
                role="user",
                content=[TextContent(text=f"Product description:\n{description}")],
            )
        ]
        
        response = await agent.run(messages)
        
        # Extract response text
        response_text = ""
        for msg in response.messages:
            for content in msg.contents:
                if hasattr(content, 'text'):
                    response_text += content.text
        
        data = self._parse_json_response(response_text)
        return self._dict_to_attributes(data)
    
    async def extract_from_image(self, image_path: Path) -> GarmentAttributes:
        """Extract attributes from garment image only."""
        agent = self._get_vision_agent()
        
        # Read image as bytes
        image_bytes = image_path.read_bytes()
        
        # Detect actual image format from magic bytes (more reliable than extension)
        if image_bytes[:3] == b'\xff\xd8\xff':
            mime_type = "image/jpeg"
        elif image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            mime_type = "image/png"
        elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
            mime_type = "image/webp"
        elif image_bytes[:6] in (b'GIF87a', b'GIF89a'):
            mime_type = "image/gif"
        else:
            # Fallback to extension
            suffix = image_path.suffix.lower()
            mime_type = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
                ".gif": "image/gif",
            }.get(suffix, "image/png")
        
        # Use DataContent with raw bytes (like garment_analyzer does)
        message = ChatMessage(
            role="user",
            contents=[
                TextContent(text="Analyze this garment:"),
                DataContent(data=image_bytes, media_type=mime_type),
            ],
        )
        
        response = await agent.run(message)
        
        # Extract response text
        response_text = ""
        for msg in response.messages:
            for content in msg.contents:
                if hasattr(content, 'text'):
                    response_text += content.text
        
        data = self._parse_json_response(response_text)
        return self._dict_to_attributes(data)
    
    async def extract(
        self,
        description: str | None = None,
        image_path: Path | None = None,
    ) -> GarmentAttributes:
        """Extract attributes from both text and image, merging results.
        
        Image analysis takes precedence for visual attributes (color, fabric).
        Text extraction takes precedence for named details.
        """
        text_attrs = None
        image_attrs = None
        
        # Extract from text (required)
        if description:
            text_attrs = await self.extract_from_text(description)
        
        # Extract from image (optional - may fail for some image formats)
        if image_path and image_path.exists():
            try:
                image_attrs = await self.extract_from_image(image_path)
            except Exception as e:
                print(f"   ⚠️ Vision extraction failed: {e}")
                image_attrs = None
        
        # Keyword fallback for garment type detection
        def apply_keyword_fallback(attrs: GarmentAttributes, desc: str) -> GarmentAttributes:
            """Apply keyword matching if LLM returned generic 'outfit'."""
            if attrs.garment_type == "outfit" and desc:
                desc_lower = desc.lower()
                for gt in ['maxi dress', 'midi dress', 'mini dress', 'slip dress', 'bodycon dress', 
                           'wrap dress', 'shirt dress', 'dress', 'blouse', 'top', 'shirt', 'pants', 
                           'trousers', 'jeans', 'skirt', 'jacket', 'blazer', 'coat', 'cardigan', 
                           'sweater', 'jumper', 'hoodie', 'romper', 'jumpsuit', 'shorts']:
                    if gt in desc_lower:
                        return GarmentAttributes(
                            garment_type=gt,
                            color=attrs.color,
                            fabric=attrs.fabric,
                            neckline=attrs.neckline,
                            sleeves=attrs.sleeves,
                            length=attrs.length,
                            fit=attrs.fit,
                            details=attrs.details,
                        )
            return attrs
        
        # If only one source, apply keyword fallback and return
        if text_attrs and not image_attrs:
            return apply_keyword_fallback(text_attrs, description)
        if image_attrs and not text_attrs:
            return image_attrs
        if not text_attrs and not image_attrs:
            return GarmentAttributes(
                garment_type="outfit",
                color=None, fabric=None, neckline=None,
                sleeves=None, length=None, fit=None, details=[]
            )
        
        # Merge: prefer text for garment type, image for visual attributes
        final_garment_type = text_attrs.garment_type
        
        # If text extraction failed to get specific type, try keyword matching
        if final_garment_type == "outfit" and description:
            desc_lower = description.lower()
            for gt in ['maxi dress', 'midi dress', 'mini dress', 'slip dress', 'bodycon dress', 
                       'wrap dress', 'shirt dress', 'dress', 'blouse', 'top', 'shirt', 'pants', 
                       'trousers', 'jeans', 'skirt', 'jacket', 'blazer', 'coat', 'cardigan', 
                       'sweater', 'jumper', 'hoodie', 'romper', 'jumpsuit', 'shorts']:
                if gt in desc_lower:
                    final_garment_type = gt
                    break
        
        # If still outfit, try image result
        if final_garment_type == "outfit" and image_attrs.garment_type != "outfit":
            final_garment_type = image_attrs.garment_type
        
        return GarmentAttributes(
            garment_type=final_garment_type,
            color=image_attrs.color or text_attrs.color,  # Image color more accurate
            fabric=text_attrs.fabric or image_attrs.fabric,  # Text usually has fabric name
            neckline=image_attrs.neckline or text_attrs.neckline,
            sleeves=image_attrs.sleeves or text_attrs.sleeves,
            length=text_attrs.length or image_attrs.length,
            fit=image_attrs.fit or text_attrs.fit,
            details=list(set(text_attrs.details + image_attrs.details))[:4],
        )
