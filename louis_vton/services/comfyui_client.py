"""ComfyUI API client for FLUX 2 Klein virtual try-on image generation."""

import asyncio
import shutil
import uuid
from pathlib import Path
from typing import Any

import httpx

from ..config import ComfyUIConfig, GenerationConfig


class ComfyUIClient:
    """Client for interacting with ComfyUI's API using FLUX 2 Klein workflow."""
    
    def __init__(
        self,
        config: ComfyUIConfig,
        comfyui_input_dir: Path,
    ):
        self.config = config
        self.input_dir = comfyui_input_dir
        self._client: httpx.AsyncClient | None = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=300.0)  # 5 min timeout for generation
        return self._client
    
    async def check_connection(self) -> bool:
        """Verify ComfyUI is running and accessible."""
        try:
            response = await self.client.get(f"{self.config.base_url}/system_stats")
            return response.status_code == 200
        except httpx.ConnectError:
            return False
    
    def copy_image_to_input(self, image_path: Path, name: str | None = None) -> str:
        """Copy an image to ComfyUI's input directory.
        
        Returns the filename (not full path) for use in workflow.
        """
        if name is None:
            name = f"tryon_{uuid.uuid4().hex[:8]}{image_path.suffix}"
        
        dest = self.input_dir / name
        shutil.copy2(image_path, dest)
        return name
    
    async def generate_tryon(
        self,
        model_image: Path,
        garment_image: Path,
        prompt: str,
        generation_config: GenerationConfig | None = None,
        output_path: Path | None = None,
    ) -> Path | bytes:
        """Generate a try-on image using FLUX 2 Klein.
        
        Args:
            model_image: Path to the model/person image
            garment_image: Path to the garment reference image
            prompt: The FLUX prompt (e.g., "Replace the clothing of the woman...")
            generation_config: Optional generation settings
            output_path: Optional path to save the generated image
            
        Returns:
            Path to the generated image, or bytes if no output_path specified
        """
        # Copy images to ComfyUI input directory
        model_filename = self.copy_image_to_input(model_image, "tryon_model.png")
        garment_filename = self.copy_image_to_input(garment_image, "tryon_garment.png")
        
        # Get generation config or use defaults
        seed = self._random_seed()
        if generation_config:
            seed = generation_config.seed or seed
        
        # Build FLUX 2 Klein workflow
        workflow = self._build_flux2_klein_workflow(
            model_filename=model_filename,
            garment_filename=garment_filename,
            prompt=prompt,
            seed=seed,
        )
        
        # Queue the prompt
        prompt_id = await self._queue_prompt(workflow)
        
        # Wait for completion
        output_images = await self._wait_for_completion(prompt_id)
        
        if not output_images:
            raise RuntimeError("No images generated")
        
        # Get the output image
        image_data = await self._get_image(output_images[0])
        
        # Save to output path if specified
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(image_data)
            return output_path
        
        return image_data
    
    def _build_flux2_klein_workflow(
        self,
        model_filename: str,
        garment_filename: str,
        prompt: str,
        seed: int,
    ) -> dict[str, Any]:
        """Build FLUX 2 Klein 9B workflow for virtual try-on.
        
        This workflow uses two reference images:
        - Reference image 1 (node 76): Model/person photo  
        - Reference image 2 (node 81): Garment to wear
        
        Uses Reference Conditioning subgraphs to condition on both images.
        """
        return {
            # Models
            "110": {
                "class_type": "UNETLoader",
                "inputs": {
                    "unet_name": "flux-2-klein-9b-fp8.safetensors",
                    "weight_dtype": "default",
                }
            },
            "111": {
                "class_type": "CLIPLoader",
                "inputs": {
                    "clip_name": "qwen_3_8b_fp8mixed.safetensors",
                    "type": "flux2",
                    "device": "default",
                }
            },
            "113": {
                "class_type": "VAELoader",
                "inputs": {
                    "vae_name": "flux2-vae.safetensors",
                }
            },
            # Load person image (reference image 1)
            "76": {
                "class_type": "LoadImage",
                "inputs": {
                    "image": model_filename,
                }
            },
            # Load garment image (reference image 2)
            "81": {
                "class_type": "LoadImage",
                "inputs": {
                    "image": garment_filename,
                }
            },
            # Scale person image
            "114": {
                "class_type": "ImageScaleToTotalPixels",
                "inputs": {
                    "image": ["76", 0],
                    "upscale_method": "nearest-exact",
                    "megapixels": 1.0,
                    "resolution_steps": 1,
                }
            },
            # Scale garment image
            "115": {
                "class_type": "ImageScaleToTotalPixels",
                "inputs": {
                    "image": ["81", 0],
                    "upscale_method": "nearest-exact",
                    "megapixels": 1.0,
                    "resolution_steps": 1,
                }
            },
            # Get image size from person image
            "120": {
                "class_type": "GetImageSize",
                "inputs": {
                    "image": ["114", 0],
                }
            },
            # Text encode positive prompt
            "112": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["111", 0],
                    "text": prompt,
                }
            },
            # Zero out conditioning for negative
            "118": {
                "class_type": "ConditioningZeroOut",
                "inputs": {
                    "conditioning": ["112", 0],
                }
            },
            # VAE Encode person image
            "vae_encode_person": {
                "class_type": "VAEEncode",
                "inputs": {
                    "pixels": ["114", 0],
                    "vae": ["113", 0],
                }
            },
            # Reference Latent for positive (person image)
            "ref_positive_person": {
                "class_type": "ReferenceLatent",
                "inputs": {
                    "conditioning": ["112", 0],
                    "latent": ["vae_encode_person", 0],
                }
            },
            # Reference Latent for negative (person image)
            "ref_negative_person": {
                "class_type": "ReferenceLatent",
                "inputs": {
                    "conditioning": ["118", 0],
                    "latent": ["vae_encode_person", 0],
                }
            },
            # VAE Encode garment image
            "vae_encode_garment": {
                "class_type": "VAEEncode",
                "inputs": {
                    "pixels": ["115", 0],
                    "vae": ["113", 0],
                }
            },
            # Reference Latent for positive (garment - chained after person)
            "ref_positive_garment": {
                "class_type": "ReferenceLatent",
                "inputs": {
                    "conditioning": ["ref_positive_person", 0],
                    "latent": ["vae_encode_garment", 0],
                }
            },
            # Reference Latent for negative (garment - chained after person)
            "ref_negative_garment": {
                "class_type": "ReferenceLatent",
                "inputs": {
                    "conditioning": ["ref_negative_person", 0],
                    "latent": ["vae_encode_garment", 0],
                }
            },
            # Empty latent for generation (uses person image dimensions)
            "119": {
                "class_type": "EmptyFlux2LatentImage",
                "inputs": {
                    "width": ["120", 0],
                    "height": ["120", 1],
                    "batch_size": 1,
                }
            },
            # Random noise
            "109": {
                "class_type": "RandomNoise",
                "inputs": {
                    "noise_seed": seed,
                }
            },
            # Sampler
            "104": {
                "class_type": "KSamplerSelect",
                "inputs": {
                    "sampler_name": "euler",
                }
            },
            # Scheduler (4 steps for distilled model)
            "105": {
                "class_type": "Flux2Scheduler",
                "inputs": {
                    "steps": 4,
                    "width": ["120", 0],
                    "height": ["120", 1],
                }
            },
            # CFG Guider with both reference conditionings
            "106": {
                "class_type": "CFGGuider",
                "inputs": {
                    "model": ["110", 0],
                    "positive": ["ref_positive_garment", 0],
                    "negative": ["ref_negative_garment", 0],
                    "cfg": 1.0,
                }
            },
            # Custom sampler
            "107": {
                "class_type": "SamplerCustomAdvanced",
                "inputs": {
                    "noise": ["109", 0],
                    "guider": ["106", 0],
                    "sampler": ["104", 0],
                    "sigmas": ["105", 0],
                    "latent_image": ["119", 0],
                }
            },
            # VAE Decode
            "108": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["107", 0],
                    "vae": ["113", 0],
                }
            },
            # Save output
            "save": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["108", 0],
                    "filename_prefix": "tryon_output",
                }
            }
        }
    
    async def _queue_prompt(self, workflow: dict[str, Any]) -> str:
        """Queue a prompt and return the prompt ID."""
        payload = {
            "prompt": workflow,
            "client_id": str(uuid.uuid4()),
        }
        
        response = await self.client.post(
            f"{self.config.base_url}/prompt",
            json=payload,
        )
        
        if response.status_code != 200:
            error_text = response.text
            raise RuntimeError(f"ComfyUI rejected workflow: {error_text[:500]}")
        
        result = response.json()
        return result["prompt_id"]
    
    async def _wait_for_completion(
        self,
        prompt_id: str,
        poll_interval: float = 0.5,
        timeout: float = 300.0,
    ) -> list[dict[str, Any]]:
        """Poll until the prompt completes, return output image info."""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = await self.client.get(f"{self.config.base_url}/history/{prompt_id}")
            
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    # Find SaveImage node outputs
                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            return node_output["images"]
            
            await asyncio.sleep(poll_interval)
        
        raise TimeoutError(f"Generation timed out after {timeout}s")
    
    async def _get_image(self, image_info: dict[str, Any]) -> bytes:
        """Retrieve a generated image from ComfyUI."""
        params = {
            "filename": image_info["filename"],
            "subfolder": image_info.get("subfolder", ""),
            "type": image_info.get("type", "output"),
        }
        
        response = await self.client.get(
            f"{self.config.base_url}/view",
            params=params,
        )
        response.raise_for_status()
        
        return response.content
    
    def _random_seed(self) -> int:
        """Generate a random seed."""
        import random
        return random.randint(0, 2**32 - 1)
    
    async def close(self):
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
