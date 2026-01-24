/**
 * Virtual Try-On Extension - Popup Script
 * Clean two-screen flow: Selection → Result
 */

const API_BASE_URL = 'http://localhost:8000';
const STORAGE_KEY = 'virtualTryOnState';
const PHOTO_STORAGE_KEY = 'virtualTryOnPhoto';

// State
let selectedGarmentUrl = null;
let uploadedPhoto = null;  // base64 data URL
let productDescription = '';
let scrapedImages = [];

// ============================================
// PHOTO PERSISTENCE
// ============================================

async function savePhoto() {
  if (uploadedPhoto) {
    try {
      await chrome.storage.local.set({ [PHOTO_STORAGE_KEY]: uploadedPhoto });
      console.log('[Popup] Photo saved');
    } catch (e) {
      console.error('[Popup] Failed to save photo:', e);
    }
  }
}

async function loadPhoto() {
  try {
    const data = await chrome.storage.local.get(PHOTO_STORAGE_KEY);
    return data[PHOTO_STORAGE_KEY] || null;
  } catch (e) {
    console.error('[Popup] Failed to load photo:', e);
    return null;
  }
}

async function clearSavedPhoto() {
  try {
    await chrome.storage.local.remove(PHOTO_STORAGE_KEY);
    console.log('[Popup] Saved photo cleared');
  } catch (e) {
    console.error('[Popup] Failed to clear photo:', e);
  }
}

// DOM Elements
const elements = {
  // Screens
  screenSelection: document.getElementById('screen-selection'),
  screenGenerating: document.getElementById('screen-generating'),
  screenResult: document.getElementById('screen-result'),
  
  // Selection screen
  loading: document.getElementById('loading'),
  selectionContent: document.getElementById('selection-content'),
  noImages: document.getElementById('no-images'),
  pageUrl: document.getElementById('page-url'),
  imageCount: document.getElementById('image-count'),
  garmentImages: document.getElementById('garment-images'),
  refreshBtn: document.getElementById('refresh-btn'),
  retryBtn: document.getElementById('retry-btn'),
  
  // Upload
  uploadArea: document.getElementById('upload-area'),
  modelUpload: document.getElementById('model-upload'),
  uploadPlaceholder: document.getElementById('upload-placeholder'),
  uploadPreview: document.getElementById('upload-preview'),
  previewImage: document.getElementById('preview-image'),
  removePhoto: document.getElementById('remove-photo'),
  
  // Generate
  generateBtn: document.getElementById('generate-btn'),
  generateHint: document.getElementById('generate-hint'),
  
  // Result screen
  resultImage: document.getElementById('result-image'),
  downloadBtn: document.getElementById('download-btn'),
  tryAnotherBtn: document.getElementById('try-another-btn'),
};

// ============================================
// SCREEN NAVIGATION
// ============================================

function showScreen(screenName) {
  elements.screenSelection.classList.add('hidden');
  elements.screenGenerating.classList.add('hidden');
  elements.screenResult.classList.add('hidden');
  
  if (screenName === 'selection') {
    elements.screenSelection.classList.remove('hidden');
  } else if (screenName === 'generating') {
    elements.screenGenerating.classList.remove('hidden');
  } else if (screenName === 'result') {
    elements.screenResult.classList.remove('hidden');
  }
}

// ============================================
// BACKGROUND SERVICE WORKER COMMUNICATION
// ============================================

async function checkGenerationStatus() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: 'GET_STATUS' }, (response) => {
      resolve(response || { status: 'idle' });
    });
  });
}

async function startBackgroundGeneration(request) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: 'START_GENERATION', request }, (response) => {
      resolve(response);
    });
  });
}

async function clearGenerationResult() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: 'CLEAR_RESULT' }, (response) => {
      resolve(response);
    });
  });
}

// Listen for messages from background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[Popup] Received message:', message.type);
  
  if (message.type === 'GENERATION_COMPLETE') {
    showResult(message.result.result);
  } else if (message.type === 'GENERATION_ERROR') {
    alert(`Error: ${message.error}`);
    showScreen('selection');
  }
});

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  
  // Restore saved photo first
  const savedPhoto = await loadPhoto();
  if (savedPhoto) {
    uploadedPhoto = savedPhoto;
    elements.previewImage.src = uploadedPhoto;
    elements.uploadPlaceholder.classList.add('hidden');
    elements.uploadPreview.classList.remove('hidden');
    console.log('[Popup] Restored saved photo');
  }
  
  // Check if there's a generation in progress or completed
  const genStatus = await checkGenerationStatus();
  console.log('[Popup] Generation status:', genStatus.status);
  
  if (genStatus.status === 'generating') {
    showScreen('generating');
    pollForCompletion();
    return;
  }
  
  if (genStatus.status === 'complete' && genStatus.result) {
    showResult(genStatus.result);
    return;
  }
  
  if (genStatus.status === 'error' && genStatus.error) {
    alert(`Previous generation failed: ${genStatus.error}`);
    await clearGenerationResult();
  }
  
  // Normal flow: scrape page
  await scrapePageData();
});

async function pollForCompletion() {
  const checkInterval = setInterval(async () => {
    const status = await checkGenerationStatus();
    
    if (status.status === 'complete') {
      clearInterval(checkInterval);
      showResult(status.result);
    } else if (status.status === 'error') {
      clearInterval(checkInterval);
      alert(`Error: ${status.error}`);
      await clearGenerationResult();
      showScreen('selection');
    } else if (status.status === 'idle') {
      clearInterval(checkInterval);
      await scrapePageData();
    }
  }, 1000);
}

// ============================================
// EVENT LISTENERS
// ============================================

function setupEventListeners() {
  elements.refreshBtn.addEventListener('click', scrapePageData);
  elements.retryBtn?.addEventListener('click', scrapePageData);
  
  elements.uploadArea.addEventListener('click', () => elements.modelUpload.click());
  elements.modelUpload.addEventListener('change', handleFileSelect);
  elements.removePhoto.addEventListener('click', (e) => {
    e.stopPropagation();
    removeUploadedPhoto();
  });
  
  elements.generateBtn.addEventListener('click', handleGenerate);
  elements.downloadBtn.addEventListener('click', downloadResult);
  elements.tryAnotherBtn.addEventListener('click', handleTryAnother);
}

// ============================================
// PAGE SCRAPING
// ============================================

async function scrapePageData() {
  elements.loading.classList.remove('hidden');
  elements.selectionContent.classList.add('hidden');
  elements.noImages.classList.add('hidden');
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab?.id) {
      throw new Error('No active tab');
    }
    
    elements.pageUrl.textContent = new URL(tab.url).hostname;
    
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: scrapeGarmentData,
    });
    
    const data = results[0]?.result;
    
    if (!data || data.images.length === 0) {
      elements.loading.classList.add('hidden');
      elements.noImages.classList.remove('hidden');
      return;
    }
    
    scrapedImages = data.images;
    productDescription = data.description || '';
    
    displayImages(scrapedImages);
    
    elements.loading.classList.add('hidden');
    elements.selectionContent.classList.remove('hidden');
    
  } catch (error) {
    console.error('[Popup] Scrape error:', error);
    elements.loading.classList.add('hidden');
    elements.noImages.classList.remove('hidden');
  }
}

function scrapeGarmentData() {
  const images = [];
  const seen = new Set();
  
  // Get all images
  document.querySelectorAll('img').forEach(img => {
    let url = img.src || img.dataset.src || img.dataset.lazySrc;
    if (!url || !url.startsWith('http')) return;
    
    // Skip tiny images
    if (img.naturalWidth < 100 || img.naturalHeight < 100) return;
    
    // Skip common non-product images
    if (url.includes('logo') || url.includes('icon') || url.includes('sprite')) return;
    
    // Get high-res version if available
    if (img.srcset) {
      const srcsetParts = img.srcset.split(',');
      const lastPart = srcsetParts[srcsetParts.length - 1].trim().split(' ')[0];
      if (lastPart.startsWith('http')) url = lastPart;
    }
    
    // Dedupe
    const key = url.split('?')[0];
    if (seen.has(key)) return;
    seen.add(key);
    
    images.push(url);
  });
  
  // ========================================
  // INTELLIGENT PRODUCT DESCRIPTION SCRAPING
  // ========================================
  
  const descriptionParts = [];
  
  // 1. Get product title (h1)
  const titleEl = document.querySelector('h1');
  if (titleEl?.textContent?.trim()) {
    descriptionParts.push(titleEl.textContent.trim());
  }
  
  // 2. Look for JSON-LD structured data (most reliable)
  document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
    try {
      let data = JSON.parse(script.textContent);
      // Handle arrays (some sites wrap in array)
      if (Array.isArray(data)) data = data[0];
      // Look for Product schema
      if (data['@type'] === 'Product' || data.name) {
        if (data.description && !descriptionParts.includes(data.description)) {
          descriptionParts.push(data.description);
        }
        if (data.material) {
          descriptionParts.push('Material: ' + data.material);
        }
        if (data.color) {
          descriptionParts.push('Color: ' + data.color);
        }
      }
    } catch (e) {}
  });
  
  // 3. Look for expandable sections (Description, Fit, Materials, etc.)
  const expandableSectionKeywords = [
    'description', 'fit', 'material', 'fabric', 'composition',
    'details', 'product info', 'about', 'specifications'
  ];
  
  // Find buttons/headers that might expand sections
  const expandableSelectors = [
    'button', '[role="button"]', '[data-accordion]', '[data-toggle]',
    '.accordion-header', '.accordion-title', '.collapsible-header',
    '[class*="accordion"]', '[class*="expand"]', '[class*="toggle"]',
    'summary', '.tab-title', '[role="tab"]'
  ];
  
  expandableSelectors.forEach(selector => {
    document.querySelectorAll(selector).forEach(el => {
      const text = el.textContent?.toLowerCase() || '';
      if (expandableSectionKeywords.some(kw => text.includes(kw))) {
        // Found a matching section header - get its content
        // Try to find associated content panel
        const contentSelectors = [
          el.nextElementSibling,
          el.parentElement?.querySelector('[class*="content"]'),
          el.parentElement?.querySelector('[class*="panel"]'),
          el.parentElement?.querySelector('[class*="body"]'),
          document.querySelector(`#${el.getAttribute('aria-controls')}`),
          el.closest('[class*="accordion"]')?.querySelector('[class*="content"]'),
        ];
        
        for (const content of contentSelectors) {
          if (content?.textContent?.trim() && content.textContent.trim().length > 20) {
            const contentText = content.textContent.trim()
              .replace(/\s+/g, ' ')  // Normalize whitespace
              .substring(0, 300);
            if (!descriptionParts.some(p => p.includes(contentText.substring(0, 50)))) {
              descriptionParts.push(contentText);
            }
            break;
          }
        }
      }
    });
  });
  
  // 4. Look for common description containers
  const descSelectors = [
    // Generic
    '[class*="product-description"]',
    '[class*="productDescription"]', 
    '[class*="ProductDescription"]',
    '[data-testid*="description"]',
    '[class*="product-detail"]',
    // H&M specific
    '.product-description',
    '[class*="DescriptionAndFit"]',
    '[class*="Materials"]',
    '[class*="pdp-description"]',
    // Common patterns
    '.description-text',
    '.product-info',
    '[itemprop="description"]',
  ];
  
  descSelectors.forEach(sel => {
    const el = document.querySelector(sel);
    if (el?.textContent?.trim() && el.textContent.trim().length > 20) {
      const text = el.textContent.trim()
        .replace(/\s+/g, ' ')
        .substring(0, 300);
      // Avoid duplicates
      if (!descriptionParts.some(p => p.includes(text.substring(0, 50)))) {
        descriptionParts.push(text);
      }
    }
  });
  
  // 5. Look for meta tags
  const metaDesc = document.querySelector('meta[name="description"]');
  if (metaDesc?.content && !descriptionParts.length) {
    descriptionParts.push(metaDesc.content);
  }
  
  // 6. Look for Open Graph data
  const ogTitle = document.querySelector('meta[property="og:title"]');
  const ogDesc = document.querySelector('meta[property="og:description"]');
  if (ogDesc?.content && !descriptionParts.some(p => p.includes(ogDesc.content.substring(0, 30)))) {
    descriptionParts.push(ogDesc.content);
  }
  
  // Combine and clean up
  let description = descriptionParts
    .filter(p => p && p.length > 5)
    .join(' | ')
    .substring(0, 800);  // Reasonable limit
  
  // Remove common noise words
  description = description
    .replace(/read more|show more|view details|expand|collapse/gi, '')
    .replace(/\s+/g, ' ')
    .trim();
  
  console.log('[Scraper] Found description:', description?.substring(0, 150));
  console.log('[Scraper] Description parts:', descriptionParts.length);
  
  return { images, description };
}

function displayImages(images) {
  elements.garmentImages.innerHTML = '';
  elements.imageCount.textContent = `${images.length} images found`;
  
  images.forEach((url, index) => {
    const item = document.createElement('div');
    item.className = 'image-item';
    item.innerHTML = `<img src="${url}" alt="Garment ${index + 1}">`;
    
    item.addEventListener('click', () => selectGarmentImage(url, item));
    
    elements.garmentImages.appendChild(item);
  });
}

function selectGarmentImage(url, element) {
  // Clear previous selection
  document.querySelectorAll('.image-item.selected').forEach(el => {
    el.classList.remove('selected');
  });
  
  // Select this one
  element.classList.add('selected');
  selectedGarmentUrl = url;
  
  updateGenerateButton();
}

// ============================================
// PHOTO UPLOAD
// ============================================

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = async (e) => {
    uploadedPhoto = e.target.result;
    elements.previewImage.src = uploadedPhoto;
    elements.uploadPlaceholder.classList.add('hidden');
    elements.uploadPreview.classList.remove('hidden');
    updateGenerateButton();
    
    // Persist the photo for future sessions
    await savePhoto();
  };
  reader.readAsDataURL(file);
}

async function removeUploadedPhoto() {
  uploadedPhoto = null;
  elements.modelUpload.value = '';
  elements.uploadPlaceholder.classList.remove('hidden');
  elements.uploadPreview.classList.add('hidden');
  updateGenerateButton();
  
  // Clear saved photo
  await clearSavedPhoto();
}

// ============================================
// GENERATE
// ============================================

function updateGenerateButton() {
  const canGenerate = selectedGarmentUrl && uploadedPhoto;
  elements.generateBtn.disabled = !canGenerate;
  
  if (!selectedGarmentUrl && !uploadedPhoto) {
    elements.generateHint.textContent = 'Select a garment and upload your photo';
  } else if (!selectedGarmentUrl) {
    elements.generateHint.textContent = 'Select a garment image above';
  } else if (!uploadedPhoto) {
    elements.generateHint.textContent = 'Upload your photo';
  } else {
    elements.generateHint.textContent = 'Ready to generate!';
  }
}

async function handleGenerate() {
  if (!selectedGarmentUrl || !uploadedPhoto) return;
  
  showScreen('generating');
  
  const request = {
    garment_url: selectedGarmentUrl,
    model_photo: uploadedPhoto,
    description: productDescription,
  };
  
  await startBackgroundGeneration(request);
  pollForCompletion();
}

// ============================================
// RESULT
// ============================================

function showResult(imageData) {
  // Handle both URL and base64
  let finalSrc;
  if (imageData.startsWith('data:') || imageData.startsWith('http')) {
    finalSrc = imageData;
  } else {
    finalSrc = `data:image/png;base64,${imageData}`;
  }
  
  elements.resultImage.src = finalSrc;
  showScreen('result');
  
  // Clear generation state
  clearGenerationResult();
}

function downloadResult() {
  const link = document.createElement('a');
  link.download = 'tryon-result.png';
  link.href = elements.resultImage.src;
  link.click();
}

async function handleTryAnother() {
  // Go back to selection screen
  showScreen('selection');
  await clearGenerationResult();
  
  // Keep selections if they exist, just show the screen
  if (scrapedImages.length === 0) {
    await scrapePageData();
  }
}

console.log('[Popup] Script loaded');
