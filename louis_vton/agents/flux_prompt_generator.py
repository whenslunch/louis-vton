"""FLUX Prompt Generator Agent - creates optimized prompts for FLUX 2 Klein image editing."""

from azure.identity import AzureCliCredential
from agent_framework import ChatMessage, Content
from agent_framework.azure import AzureOpenAIResponsesClient


FLUX_PROMPT_SYSTEM = """You are an expert prompt engineer for FLUX 2 Klein, a state-of-the-art image editing model. Your task is to create precise, effective prompts that will make the model generate accurate virtual try-on images.

## CRITICAL REQUIREMENT - IDENTITY PRESERVATION:
The user's photo (reference image 1) contains THEIR face, hair, body, and environment. These MUST be preserved EXACTLY. Only the clothing should change. The output should look like a photo of THE SAME PERSON wearing different clothes.

## How FLUX 2 Klein Works:
FLUX 2 Klein takes TWO reference images:
- Reference Image 1: The USER'S PHOTO (their face, hair, body, pose, and environment - ALL must be preserved)
- Reference Image 2: The GARMENT photo (the clothing item to put on the person)

The model should ONLY replace the clothing, keeping everything else identical.

## ABSOLUTE PRESERVATION REQUIREMENTS:
These elements from reference image 1 MUST remain UNCHANGED:
1. **Face** - exact facial features, skin tone, expression, makeup
2. **Hair** - exact hairstyle, color, length, styling
3. **Body** - exact body shape, proportions, skin tone
4. **Pose** - exact position, angle, stance, hand positions
5. **Background** - exact environment, setting, colors, objects
6. **Lighting** - exact lighting direction, shadows, highlights
7. **Image quality** - same resolution, style, photographic quality

## What SHOULD Change:
ONLY the clothing on the person's torso/body should be replaced with the garment from reference image 2.

## CRITICAL - USE SPECIFIC GARMENT DETAILS:
You will be given the manufacturer's description of the garment. EXTRACT and USE these details in your prompt:
1. **Garment type** - dress, blouse, jacket, pants, skirt, top, etc. (NEVER use the generic word "garment")
2. **Color** - the specific color (dusty turquoise, powder pink, navy blue, etc.)
3. **Style features** - neckline (V-neck, square neck, off-shoulder), sleeves, length, etc.
4. **Fabric/texture** - satin, pleated, textured, jersey, poplin, etc.
5. **Special details** - tie details, buttons, cutouts, draping, etc.

## Key Prompt Engineering Principles:

1. **Emphasize identity preservation FIRST:**
   - Start with "Keep the exact same person..."
   - Explicitly mention preserving face, hair, body
   - Stress that ONLY clothing changes

2. **Describe the garment specifically using manufacturer details:**
   - Use the EXACT garment type (dress, blouse, etc.) - never say "garment"
   - Include the color from the description
   - Mention 2-3 key visual features (neckline, sleeves, fabric)
   - Keep it focused and clear

3. **Keep it focused:**
   - FLUX responds well to clear, direct instructions
   - Prioritize preservation language over extensive garment details
   - The garment is shown in reference image 2, so highlight key distinguishing features

## Examples:

Input description: "Dusty turquoise Pleated Dress with V-neckline and thin straps, accordion pleats"
GOOD OUTPUT: "Keep the exact same person from reference image 1 — preserve their face, hair, skin tone, body shape, pose, and the background environment exactly. ONLY change their clothing to the dusty turquoise pleated maxi dress shown in reference image 2. The dress has a V-neckline, thin straps, and flowing accordion pleats. The person should look identical except for wearing this elegant pleated dress."

Input description: "Powder pink Tie-Detail Satin Slip Dress with adjustable straps"
GOOD OUTPUT: "Preserve the exact identity of the person in reference image 1 including their face, hairstyle, body, pose, and surroundings. Replace ONLY their current outfit with the powder pink satin slip dress from reference image 2. The dress features a lustrous satin finish with delicate tie details. Keep everything else about the photo unchanged."

Input description: "Black textured bodycon dress with square neckline"
GOOD OUTPUT: "Keep the exact same person from reference image 1 — preserve their face, hair, body, pose, and background exactly. ONLY replace their clothing with the black textured bodycon dress shown in reference image 2. The dress has a square neckline and figure-hugging textured fabric. The person should look identical except for wearing this black dress."

BAD: "A woman wearing a dress" (loses the person's identity entirely)
BAD: "Replace the garment of the woman" (too generic, doesn't use specific garment type)
BAD: "Change the clothing to the garment in reference image 2" (never use the word "garment")

## CRITICAL OUTPUT RULES:
1. Return ONLY the prompt text - nothing else
2. Do NOT ask questions or request clarification
3. Do NOT include explanations or commentary
4. Do NOT use markdown formatting
5. Work with whatever description is provided - extract what you can
6. If the description is minimal, still generate a valid prompt using "dress", "top", or "outfit" as the garment type
7. ALWAYS output a complete, usable prompt - never refuse or ask for more info"""


class FluxPromptGeneratorAgent:
    """Generates optimized prompts for FLUX 2 Klein virtual try-on.
    
    Creates prompts that effectively instruct FLUX to transfer a garment
    from one image onto a person in another image.
    """
    
    def __init__(self):
        """Initialize the generator with Azure OpenAI client."""
        self.client = AzureOpenAIResponsesClient(
            credential=AzureCliCredential(),
        )
        self._agent = None
    
    def _get_agent(self):
        """Lazy initialization of the agent."""
        if self._agent is None:
            self._agent = self.client.as_agent(
                name="FluxPromptGenerator",
                instructions=FLUX_PROMPT_SYSTEM,
            )
        return self._agent
    
    async def generate(
        self,
        garment_description: str,
        person_description: str = "woman",
    ) -> str:
        """Generate optimized FLUX prompt for virtual try-on.
        
        Args:
            garment_description: Description of the garment (from manufacturer or vision analysis)
            person_description: Brief description of the person (default: "woman")
            
        Returns:
            Optimized prompt string for FLUX 2 Klein
        """
        agent = self._get_agent()
        
        # Build the request - emphasize extracting specific garment details
        user_message = f"""Create a FLUX 2 Klein prompt for a virtual try-on.

Person in reference image 1: {person_description}

Manufacturer's garment description (reference image 2):
{garment_description}

IMPORTANT: Extract the specific garment type (dress, blouse, jacket, etc.), color, and key features from the description above. Never use the generic word "garment" - always use the specific type. Include 2-3 notable features (fabric, neckline, details) in your prompt.

Generate the optimal prompt."""

        messages = [
            ChatMessage(
                role="user",
                content=[Content.from_text(user_message)],
            )
        ]
        
        response = await agent.run(messages)
        
        # Extract text from response - iterate through messages and their contents
        prompt = ""
        for msg in response.messages:
            for content in msg.contents:
                if hasattr(content, 'text'):
                    prompt += content.text
        
        return prompt.strip()
    
    def generate_simple(
        self,
        garment_description: str,
        person_description: str = "person",
    ) -> str:
        """Generate a simple prompt without LLM (for fast/fallback use).
        
        Args:
            garment_description: Description of the garment
            person_description: Brief description of the person
            
        Returns:
            Simple prompt string for FLUX 2 Klein
        """
        desc_lower = garment_description.lower()
        
        # Determine garment type (more comprehensive list)
        garment_types = [
            'maxi dress', 'midi dress', 'mini dress', 'slip dress', 'bodycon dress', 'wrap dress',
            'dress', 'blouse', 'top', 'shirt', 'pants', 'trousers', 'jeans', 'skirt', 
            'jacket', 'blazer', 'coat', 'cardigan', 'sweater', 'jumper', 'hoodie',
            'romper', 'jumpsuit', 'shorts', 'vest', 'tank top', 'camisole', 'bodysuit'
        ]
        garment_type = 'outfit'  # fallback, but avoid "garment"
        for gt in garment_types:
            if gt in desc_lower:
                garment_type = gt
                break
        
        # Extract color (look for common color words in first 100 chars typically)
        colors = [
            'black', 'white', 'navy', 'blue', 'red', 'pink', 'powder pink', 'dusty pink',
            'green', 'olive', 'khaki', 'beige', 'cream', 'ivory', 'grey', 'gray',
            'burgundy', 'maroon', 'purple', 'lavender', 'turquoise', 'dusty turquoise',
            'coral', 'orange', 'yellow', 'gold', 'silver', 'brown', 'tan', 'camel'
        ]
        color = ''
        for c in colors:
            if c in desc_lower:
                color = c + ' '
                break
        
        # Extract notable features
        features = []
        feature_keywords = {
            'v-neck': 'V-neckline',
            'v neck': 'V-neckline', 
            'square neck': 'square neckline',
            'off-shoulder': 'off-shoulder design',
            'off shoulder': 'off-shoulder design',
            'pleated': 'pleated fabric',
            'satin': 'satin finish',
            'silk': 'silk fabric',
            'lace': 'lace details',
            'textured': 'textured fabric',
            'ribbed': 'ribbed texture',
            'tie detail': 'tie details',
            'button': 'button details',
            'ruched': 'ruched detailing',
            'draped': 'draped silhouette',
            'floral': 'floral pattern',
            'striped': 'striped pattern',
            'fitted': 'fitted silhouette',
            'flowy': 'flowy silhouette',
            'sleeveless': 'sleeveless design',
            'long sleeve': 'long sleeves',
            'short sleeve': 'short sleeves',
        }
        for keyword, feature in feature_keywords.items():
            if keyword in desc_lower and len(features) < 2:
                features.append(feature)
        
        feature_text = ''
        if features:
            feature_text = f" with {' and '.join(features)}"
        
        # Get a short summary of key description details (first 150 chars, trim to sentence)
        short_desc = garment_description[:150]
        if '.' in short_desc:
            short_desc = short_desc[:short_desc.rfind('.') + 1]
        
        # Build a specific prompt with the description included
        prompt = (
            f"Keep the exact same {person_description} from reference image 1 — "
            f"preserve their face, hair, skin tone, body shape, pose, and background environment exactly. "
            f"ONLY change their clothing to the {color}{garment_type} shown in reference image 2{feature_text}. "
            f"{short_desc} "
            f"The person should look identical except for wearing this {color}{garment_type}."
        )
        
        return prompt    
    def generate_from_attributes(self, attributes) -> str:
        """Generate FLUX prompt from structured GarmentAttributes.
        
        This is the preferred method - uses clean extracted attributes
        rather than raw marketing text.
        
        Args:
            attributes: GarmentAttributes dataclass with clean garment info
            
        Returns:
            FLUX prompt string
        """
        # Build the garment description from attributes
        garment_desc = attributes.to_description()
        
        # Build feature list for extra clarity
        features = []
        if attributes.neckline:
            features.append(attributes.neckline)
        if attributes.fabric:
            features.append(f"{attributes.fabric} fabric")
        if attributes.sleeves:
            features.append(attributes.sleeves)
        for detail in attributes.details[:2]:
            features.append(detail)
        
        feature_text = ""
        if features:
            feature_text = f" The {attributes.garment_type} features {', '.join(features[:3])}."
        
        # Build the final prompt
        prompt = (
            f"Keep the exact same person from reference image 1 — "
            f"preserve their face, hair, skin tone, body shape, pose, and background environment exactly. "
            f"ONLY change their clothing to the {garment_desc} shown in reference image 2."
            f"{feature_text} "
            f"The person should look identical except for wearing this {attributes.garment_type}."
        )
        
        return prompt