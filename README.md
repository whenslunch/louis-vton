# Louis-VTON: Virtual Try-On

A browser extension that lets you virtually try on clothing from fashion retail websites using AI-powered image generation.

![Demo](https://img.shields.io/badge/Status-Alpha-yellow) ![Python](https://img.shields.io/badge/Python-3.13-blue) ![License](https://img.shields.io/badge/License-MIT-green)

## Features

- 🛍️ **One-click try-on** from supported fashion websites (H&M, Zara, Aritzia, Gap, Nordstrom, etc.)
- 📸 **Upload your photo** once and it persists across sessions
- 🎨 **FLUX 2 Klein** with Reference Conditioning for high-quality, identity-preserving image generation
- 🧠 **Smart description cleaning** extracts key garment features from product text
- ⚡ **Fast generation** (~30 seconds per try-on, no LLM calls in the pipeline)

## Prerequisites

- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Anaconda
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) with FLUX 2 Klein model
- Azure CLI authenticated (`az login`) for Azure OpenAI access
- Chrome or Edge browser

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/whenslunch/louis-vton.git
cd louis-vton
```

### 2. Create conda environment

```bash
conda create -n louis-vton python=3.13 -y
conda activate louis-vton
pip install -r requirements.txt
```

### 3. Configure environment

Create a `.env` file in the project root:

```env
# Azure OpenAI (for garment attribute extraction)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# ComfyUI
COMFYUI_URL=http://127.0.0.1:8188
COMFYUI_INPUT_DIR=C:/Users/YourName/Src/ComfyUI/input
```

### 4. Set up ComfyUI

1. Install ComfyUI following their [installation guide](https://github.com/comfyanonymous/ComfyUI)
2. Download the FLUX 2 Klein model and place in `ComfyUI/models/unet/`
3. Install required custom nodes:
   - ComfyUI-GGUF (for quantized models)
4. Load the workflow from `comfyui_workflow.json`

### 5. Install browser extension

1. Open Chrome/Edge and navigate to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `extension-scraper/` folder

## Running

### Start ComfyUI

```bash
cd /path/to/ComfyUI
python main.py
```

### Start the API server

```bash
conda activate louis-vton
python -m uvicorn api.server:app --host 0.0.0.0 --port 8001
```

### Use the extension

1. Navigate to a supported fashion website (e.g., hm.com, zara.com)
2. Open a product page
3. Click the Louis-VTON extension icon
4. Upload your reference photo (first time only)
5. Click "Try It On"
6. Wait ~30 seconds for the result

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Browser Extension                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Product Page │→ │  Popup UI    │→ │ Background Worker    │   │
│  │  Scraping    │  │ (2 screens)  │  │ (API Communication)  │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP POST /api/tryon
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Server                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    TryOnPipeline                          │   │
│  │  ┌────────────────┐  ┌──────────────────────────────┐    │   │
│  │  │ Description    │→ │ ComfyUI Client               │    │   │
│  │  │ Cleaner (Regex)│  │ (FLUX 2 Klein Workflow)      │    │   │
│  │  └────────────────┘  └──────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ WebSocket API
┌─────────────────────────────────────────────────────────────────┐
│                         ComfyUI                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              FLUX 2 Klein Workflow                        │   │
│  │  ┌─────────┐  ┌─────────────┐  ┌─────────────────────┐   │   │
│  │  │ Encode  │→ │ Reference   │→ │ Generate & Decode   │   │   │
│  │  │ Images  │  │ Latent Merge│  │ (KSampler + VAE)    │   │   │
│  │  └─────────┘  └─────────────┘  └─────────────────────────┘   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Technical Design

### Pipeline Flow

1. **Image Reception**: Browser extension sends base64-encoded garment image, model photo, and product description to the API

2. **Description Cleaning** (`build_tryon_prompt`):
   - **Regex-based cleaning**: Removes marketing noise, size guides, SKUs, and irrelevant text
   - **Feature extraction**: Identifies key garment features (neckline, sleeves, fabric, fit)
   - **Template interpolation**: Builds FLUX-optimized prompt with extracted features
   - No LLM calls - fast and reliable string processing

3. **Image Generation** (`ComfyUIClient`):
   - Uploads person and garment images to ComfyUI input directory
   - Builds FLUX 2 Klein workflow with Reference Conditioning (two images)
   - Queues workflow via WebSocket API
   - Polls for completion and retrieves result

5. **Result Delivery**: PNG image returned as base64 to extension

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| `TryOnPipeline` | `louis_vton/pipeline/tryon_pipeline.py` | Orchestrates the full try-on flow |
| `build_tryon_prompt` | `louis_vton/utils/description_cleaner.py` | Cleans descriptions and builds prompts |
| `ComfyUIClient` | `louis_vton/services/comfyui_client.py` | Interfaces with ComfyUI API |
| `PipelineConfig` | `louis_vton/config.py` | Configuration management |

### Data Models

```python
@dataclass
class GarmentAttributes:
    garment_type: str      # "maxi dress", "blouse", etc.
    color: str | None      # "dusty turquoise"
    fabric: str | None     # "satin", "cotton"
    neckline: str | None   # "V-neck", "cowlneck"
    sleeves: str | None    # "sleeveless", "cap sleeve"
    length: str | None     # "maxi", "midi", "mini"
    fit: str | None        # "fitted", "relaxed"
    details: list[str]     # ["pleated", "tie-front"]
```

### Extension Architecture

- **Manifest V3** Chrome extension
- **Two-screen flow**: Selection → Generating → Result
- **Photo persistence**: Uses `chrome.storage.local`
- **Content script injection**: Scrapes product data from page

## Project Structure

```
louis-vton/
├── api/
│   └── server.py              # FastAPI server
├── extension-scraper/
│   ├── manifest.json          # Extension manifest
│   ├── background.js          # Service worker
│   ├── popup/                 # Extension UI
│   └── icons/                 # Extension icons
├── louis_vton/
│   ├── agents/                # LLM agents (legacy, not used in main flow)
│   ├── models/                # Data models
│   ├── pipeline/              # Main pipeline
│   ├── services/              # External services (ComfyUI client)
│   └── utils/                 # Description cleaner, prompt builder
├── tests/                     # Test suite (48 tests)
├── comfyui_workflow.json      # FLUX workflow reference
├── requirements.txt           # Python dependencies
└── pytest.ini                 # Test configuration
```

## Testing

```bash
# Run all tests
conda activate louis-vton
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=louis_vton --cov=api --cov-report=term-missing
```

## Supported Retailers

- H&M (hm.com)
- Zara (zara.com)
- Aritzia (aritzia.com)
- Gap (gap.com)
- Nordstrom (nordstrom.com)
- ASOS (asos.com)
- Uniqlo (uniqlo.com)
- Anthropologie (anthropologie.com)
- Free People (freepeople.com)

## Limitations

- Requires local ComfyUI installation with FLUX model (~12GB VRAM)
- Best results with clear, well-lit reference photos
- Currently optimized for dresses, tops, and outerwear
- Generation takes ~30 seconds per image

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [FLUX](https://blackforestlabs.ai/) by Black Forest Labs
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) by comfyanonymous
- [agent-framework](https://pypi.org/project/agent-framework/) for LLM orchestration
