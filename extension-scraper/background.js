/**
 * Virtual Try-On Extension - Background Service Worker
 * Handles generation requests so they persist even when popup is closed
 */

const API_BASE_URL = 'http://localhost:8001';
const GENERATION_STATE_KEY = 'generationState';

// Generation state: 'idle' | 'generating' | 'complete' | 'error'
let generationState = {
  status: 'idle',
  request: null,
  result: null,
  error: null,
  startTime: null,
};

// Restore state on service worker startup
chrome.storage.local.get(GENERATION_STATE_KEY, (data) => {
  if (data[GENERATION_STATE_KEY]) {
    generationState = data[GENERATION_STATE_KEY];
    console.log('[Background] Restored state:', generationState.status);
    
    // If we were generating when the service worker stopped, mark as error
    if (generationState.status === 'generating') {
      // Check if it's been more than 5 minutes (generation probably failed)
      const elapsed = Date.now() - generationState.startTime;
      if (elapsed > 5 * 60 * 1000) {
        generationState.status = 'error';
        generationState.error = 'Generation timed out. Please try again.';
        saveState();
      }
    }
  }
});

function saveState() {
  chrome.storage.local.set({ [GENERATION_STATE_KEY]: generationState });
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[Background] Received message:', message.type);
  
  switch (message.type) {
    case 'GET_STATUS':
      sendResponse({ ...generationState });
      break;
      
    case 'START_GENERATION':
      startGeneration(message.request);
      sendResponse({ started: true });
      break;
      
    case 'CLEAR_RESULT':
      generationState = {
        status: 'idle',
        request: null,
        result: null,
        error: null,
        startTime: null,
      };
      saveState();
      sendResponse({ cleared: true });
      break;
      
    default:
      sendResponse({ error: 'Unknown message type' });
  }
  
  return true; // Keep channel open for async response
});

async function startGeneration(request) {
  console.log('[Background] Starting generation...');
  
  // Update state to generating
  generationState = {
    status: 'generating',
    request: request,
    result: null,
    error: null,
    startTime: Date.now(),
  };
  saveState();
  
  try {
    // Fetch the garment image and convert to base64
    // This avoids hotlink protection issues since the browser can access the image
    let garmentBase64 = request.garment_photo; // May already be base64 from popup
    
    if (!garmentBase64 && request.garment_url) {
      console.log('[Background] Fetching garment image from URL...');
      garmentBase64 = await fetchImageAsBase64(request.garment_url);
    }
    
    if (!garmentBase64) {
      throw new Error('Could not load garment image');
    }
    
    const response = await fetch(`${API_BASE_URL}/api/tryon`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        garment_photo: garmentBase64,  // Send base64 instead of URL
        model_photo: request.model_photo,
        description: request.description,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }
    
    const result = await response.json();
    
    if (result.error) {
      throw new Error(result.error);
    }
    
    // Success!
    console.log('[Background] Generation complete!');
    generationState = {
      status: 'complete',
      request: request,
      result: result.image_base64,
      error: null,
      startTime: generationState.startTime,
    };
    saveState();
    
    // Notify any open popup
    try {
      chrome.runtime.sendMessage({ type: 'GENERATION_COMPLETE', result: generationState });
    } catch (e) {
      // Popup might be closed, that's ok
    }
    
  } catch (error) {
    console.error('[Background] Generation error:', error);
    generationState = {
      status: 'error',
      request: request,
      result: null,
      error: error.message,
      startTime: generationState.startTime,
    };
    saveState();
    
    // Notify any open popup
    try {
      chrome.runtime.sendMessage({ type: 'GENERATION_ERROR', error: error.message });
    } catch (e) {
      // Popup might be closed, that's ok
    }
  }
}

/**
 * Fetch an image from URL and convert to base64 data URL
 */
async function fetchImageAsBase64(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch image: ${response.status}`);
    }
    
    const blob = await response.blob();
    
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  } catch (error) {
    console.error('[Background] Failed to fetch image:', error);
    throw error;
  }
}

console.log('[Background] Service worker initialized');
