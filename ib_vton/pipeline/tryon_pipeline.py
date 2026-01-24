"""Simplified Try-On Pipeline for FLUX 2 Klein."""

import base64
from datetime import datetime
from pathlib import Path

import httpx

from ..config import PipelineConfig
from ..models import TryOnSession, GarmentSpec
from ..agents.flux_prompt_generator import FluxPromptGeneratorAgent
from ..agents.garment_extractor import GarmentExtractor
from ..services import ComfyUIClient


class TryOnPipeline:
    """Simplified pipeline for FLUX 2 Klein virtual try-on.
    
    Flow:
    1. Extract garment attributes (from text AND image)
    2. Generate FLUX prompt using clean attributes
    3. Run ComfyUI FLUX 2 Klein workflow
    4. Return result
    
    No iterations, no critic, no pose estimation - FLUX handles it well!
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        
        # Initialize services
        self.comfyui = ComfyUIClient(
            config=config.comfyui,
            comfyui_input_dir=config.comfyui_input_dir,
        )
        
        # Initialize agents
        self.prompt_generator = FluxPromptGeneratorAgent()
        self.garment_extractor = GarmentExtractor()
    
    async def run(
        self,
        garment_image: Path,
        model_image: Path,
        description: str | None = None,
    ) -> TryOnSession:
        """Run the simplified try-on pipeline.
        
        Args:
            garment_image: Path to garment reference image
            model_image: Path to the model/person image
            description: Optional product description (from manufacturer)
            
        Returns:
            TryOnSession with result
        """
        # Create session
        session = self._create_session(garment_image, model_image)
        
        print()
        print("═" * 60)
        print(f"  🧥 IB-VTON")
        print(f"  Session: {session.session_id}")
        print("═" * 60)
        print()
        
        try:
            # Check ComfyUI connection
            if not await self.comfyui.check_connection():
                raise RuntimeError(
                    f"Cannot connect to ComfyUI at {self.config.comfyui.base_url}. "
                    "Please ensure ComfyUI is running."
                )
            print("✅ ComfyUI connected")
            
            # Step 1: Extract garment attributes from BOTH text and image
            print()
            print("🔍 Extracting garment attributes...")
            
            # Use manufacturer description if provided, otherwise just image
            raw_description = description if description and len(description.strip()) > 20 else None
            
            if raw_description:
                print(f"   📝 Text: {raw_description[:80]}...")
            
            # Extract clean attributes from both sources
            attributes = await self.garment_extractor.extract(
                description=raw_description,
                image_path=garment_image,
            )
            
            # Convert to clean description string
            garment_description = attributes.to_description()
            print(f"   ✨ Extracted: {garment_description}")
            
            # Save raw and extracted descriptions
            if raw_description:
                self._save_artifact(session, "raw_description.txt", raw_description)
            self._save_artifact(session, "description.txt", garment_description)
            
            # Step 2: Generate FLUX prompt using clean attributes
            print()
            print("✨ Building prompt...")
            prompt = self.prompt_generator.generate_from_attributes(attributes)
            self._save_artifact(session, "prompt.txt", prompt)
            print(f"   \"{prompt[:80]}...\"")
            
            # Step 3: Generate try-on image
            print()
            print("🎨 Generating try-on image with FLUX 2 Klein...")
            output_path = session.session_dir / "result.png"
            
            await self.comfyui.generate_tryon(
                model_image=model_image,
                garment_image=garment_image,
                prompt=prompt,
                output_path=output_path,
            )
            
            session.add_iteration(prompt, output_path)
            session.status = "completed"
            session.completed_at = datetime.now()
            
            print(f"   ✅ Saved: {output_path}")
            
        except Exception as e:
            session.status = "failed"
            session.final_message = str(e)
            raise
        
        finally:
            session.save()
            # Don't close comfyui client - keep it open for reuse across requests
        
        print()
        print("═" * 60)
        print(f"  🎉 COMPLETE! Result: {session.session_dir / 'result.png'}")
        print("═" * 60)
        print()
        
        return session
    
    async def run_from_base64(
        self,
        garment_photo_base64: str,
        model_photo_base64: str,
        description: str | None = None,
    ) -> bytes:
        """Run try-on from base64 image data (preferred API method).
        
        Args:
            garment_photo_base64: Base64-encoded garment image (data URL format)
            model_photo_base64: Base64-encoded model photo (data URL format)
            description: Optional product description
            
        Returns:
            PNG image bytes of the try-on result
        """
        import tempfile
        import io
        from PIL import Image
        
        def decode_and_convert_image(data: str) -> bytes:
            """Decode base64 data URL and convert to PNG bytes."""
            if data.startswith("data:"):
                # Remove data URL prefix (e.g., "data:image/png;base64,")
                _, encoded = data.split(",", 1)
                raw_bytes = base64.b64decode(encoded)
            else:
                raw_bytes = base64.b64decode(data)
            
            # Convert to PNG using PIL to ensure consistent format
            try:
                img = Image.open(io.BytesIO(raw_bytes))
                # Convert to RGB if needed (e.g., RGBA, P mode)
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                output = io.BytesIO()
                img.save(output, format='PNG')
                return output.getvalue()
            except Exception:
                # If conversion fails, return original bytes
                return raw_bytes
        
        # Decode and convert both images to PNG
        garment_bytes = decode_and_convert_image(garment_photo_base64)
        model_bytes = decode_and_convert_image(model_photo_base64)
        
        # Save to temp files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            garment_path = tmpdir / "garment.png"
            garment_path.write_bytes(garment_bytes)
            
            model_path = tmpdir / "model.png"
            model_path.write_bytes(model_bytes)
            
            # Run pipeline
            session = await self.run(
                garment_image=garment_path,
                model_image=model_path,
                description=description,
            )
            
            # Read result
            result_path = session.session_dir / "result.png"
            return result_path.read_bytes()

    async def run_simple(
        self,
        garment_url: str,
        model_photo_base64: str,
        description: str | None = None,
    ) -> bytes:
        """Run try-on from URL and base64 data (for API use).
        
        Args:
            garment_url: URL of the garment image
            model_photo_base64: Base64-encoded model photo (data URL format)
            description: Optional product description
            
        Returns:
            PNG image bytes of the try-on result
        """
        import tempfile
        from urllib.parse import urlparse
        
        # Extract the origin for Referer header (helps with hotlink protection)
        parsed = urlparse(garment_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        
        # Download garment image with browser-like headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": origin + "/",
            "Origin": origin,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(garment_url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            garment_bytes = response.content
        
        # Decode model photo from base64
        if model_photo_base64.startswith("data:"):
            # Remove data URL prefix
            header, encoded = model_photo_base64.split(",", 1)
            model_bytes = base64.b64decode(encoded)
        else:
            model_bytes = base64.b64decode(model_photo_base64)
        
        # Save to temp files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            garment_path = tmpdir / "garment.png"
            garment_path.write_bytes(garment_bytes)
            
            model_path = tmpdir / "model.png"
            model_path.write_bytes(model_bytes)
            
            # Run pipeline
            session = await self.run(
                garment_image=garment_path,
                model_image=model_path,
                description=description,
            )
            
            # Read result
            result_path = session.session_dir / "result.png"
            return result_path.read_bytes()
    
    def _spec_to_description(self, spec: GarmentSpec) -> str:
        """Convert GarmentSpec to a text description for prompt generation."""
        parts = []
        
        if spec.garment_type:
            parts.append(spec.garment_type)
        
        if spec.primary_color:
            parts.append(f"in {spec.primary_color}")
        
        if spec.pattern_type and spec.pattern_type.lower() != "solid":
            parts.append(f"with {spec.pattern_type} pattern")
        
        if spec.fabric_type:
            parts.append(f"made of {spec.fabric_type}")
        
        if spec.silhouette:
            parts.append(f"with {spec.silhouette} silhouette")
        
        if spec.neckline:
            parts.append(f"featuring {spec.neckline}")
        
        if spec.sleeves:
            parts.append(f"and {spec.sleeves}")
        
        if spec.hem_length:
            parts.append(f"at {spec.hem_length} length")
        
        return " ".join(parts) if parts else "garment"
    
    def _create_session(
        self,
        garment_image: Path,
        model_image: Path,
    ) -> TryOnSession:
        """Create a new session with output directory."""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self.config.output_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        return TryOnSession(
            session_id=session_id,
            session_dir=session_dir,
            garment_images=[garment_image],
            model_image=model_image,
        )
    
    def _save_artifact(self, session: TryOnSession, filename: str, content: str):
        """Save an artifact to the session directory."""
        path = session.session_dir / filename
        path.write_text(content, encoding="utf-8")
