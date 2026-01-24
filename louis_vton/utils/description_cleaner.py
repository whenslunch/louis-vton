"""Utility to clean product descriptions for prompt generation."""

import re


# Marketing/noise phrases to remove
NOISE_PHRASES = [
    # Marketing
    r'\bnew arrival\b',
    r'\bbest seller\b',
    r'\bsale\b',
    r'\blimited edition\b',
    r'\bexclusive\b',
    r'\bfree shipping\b',
    r'\bfree returns\b',
    r'\bmust.have\b',
    r'\btrending\b',
    r'\bpopular\b',
    r'\bfavorite\b',
    r'\bessential\b',
    r'\bwardrobe staple\b',
    # UI elements
    r'\bread more\b',
    r'\bshow more\b',
    r'\bview details\b',
    r'\bexpand\b',
    r'\bcollapse\b',
    r'\bclick here\b',
    r'\badd to cart\b',
    r'\badd to bag\b',
    r'\bsize guide\b',
    r'\bdelivery\b',
    # Article numbers
    r'\bart\.?\s*no\.?:?\s*\d+',
    r'\bsku:?\s*\w+',
    r'\bproduct\s*code:?\s*\w+',
    r'\bitem\s*#?\s*\d+',
    # Percentages and composition details (keep fabric name, remove %)
    r'\d+%',
    r'\badditional material information\b',
    r'\bthe total weight of this product contains\b',
    r'\bat least:?\s*\d+',
]

# Garment type keywords to identify
GARMENT_TYPES = [
    'maxi dress', 'midi dress', 'mini dress', 'slip dress', 'wrap dress',
    'shirt dress', 'bodycon dress', 'a-line dress', 'sundress', 'dress',
    'blouse', 'top', 'shirt', 'tee', 't-shirt', 'tank top', 'camisole',
    'pants', 'trousers', 'jeans', 'shorts', 'skirt', 'culottes',
    'jacket', 'blazer', 'coat', 'cardigan', 'sweater', 'jumper', 'hoodie',
    'romper', 'jumpsuit', 'playsuit', 'overalls',
]


def clean_description(raw_description: str) -> dict:
    """Clean a raw product description for use in prompts.
    
    Returns:
        dict with 'garment_type', 'clean_description', and 'key_features'
    """
    if not raw_description:
        return {
            'garment_type': 'outfit',
            'clean_description': '',
            'key_features': [],
        }
    
    text = raw_description.lower()
    
    # Remove noise phrases
    for pattern in NOISE_PHRASES:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Normalize separators
    text = text.replace('|', '. ')
    text = text.replace('•', '. ')
    text = text.replace('  ', ' ')
    
    # Fix punctuation
    text = re.sub(r'\s*,\s*', ', ', text)
    text = re.sub(r'\s*\.\s*', '. ', text)
    text = re.sub(r'\.+', '.', text)
    text = re.sub(r'\s+', ' ', text)
    
    # Remove duplicate sentences (common in scraped data)
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    seen = set()
    unique_sentences = []
    for s in sentences:
        # Use first 30 chars as key to catch near-duplicates
        key = s[:30].strip()
        if key not in seen:
            seen.add(key)
            unique_sentences.append(s)
    
    text = '. '.join(unique_sentences)
    
    # Identify garment type
    garment_type = 'outfit'
    text_lower = text.lower()
    for gt in GARMENT_TYPES:
        if gt in text_lower:
            garment_type = gt
            break
    
    # Extract key features (things that describe the garment visually)
    key_features = []
    
    # Necklines
    neckline_patterns = [
        r'(v-neck|sweetheart|scoop|crew|boat|square|halter|off.shoulder|strapless|cowl)',
        r'(neckline)',
    ]
    for pattern in neckline_patterns:
        match = re.search(pattern, text_lower)
        if match:
            key_features.append(match.group(0))
            break
    
    # Sleeves
    sleeve_patterns = [
        r'(sleeveless|long.sleeve|short.sleeve|cap.sleeve|3/4.sleeve|puff.sleeve|bell.sleeve)',
        r'(shoulder straps|tie.?top shoulder straps|spaghetti straps|wide straps)',
    ]
    for pattern in sleeve_patterns:
        match = re.search(pattern, text_lower)
        if match:
            key_features.append(match.group(0).replace('.', ' '))
            break
    
    # Fabrics
    fabric_patterns = [
        r'(linen|cotton|silk|satin|velvet|jersey|chiffon|lace|denim|wool|cashmere|viscose)',
        r'(woven|knit|ribbed|textured|pleated)',
    ]
    for pattern in fabric_patterns:
        matches = re.findall(pattern, text_lower)
        for m in matches[:2]:  # Max 2 fabric mentions
            if m not in key_features:
                key_features.append(m)
    
    # Fit/silhouette
    fit_patterns = [
        r'(fitted|relaxed|loose|a-line|flared|bodycon|oversized|slim|tailored)',
        r'(fitted bodice|flared skirt|straight cut)',
    ]
    for pattern in fit_patterns:
        match = re.search(pattern, text_lower)
        if match:
            key_features.append(match.group(0))
            break
    
    # Special details
    detail_patterns = [
        r'(tie.?detail|bow|ruffle|ruched|gathered|pleated|embroidered|beaded)',
        r'(lace.?trim|scalloped|cutout|slit|button|zipper)',
    ]
    for pattern in detail_patterns:
        matches = re.findall(pattern, text_lower)
        for m in matches[:2]:
            clean_m = m.replace('.', ' ').replace('?', ' ').strip()
            if clean_m not in key_features:
                key_features.append(clean_m)
    
    # Clean up the description text
    clean_text = text.strip()
    if clean_text and not clean_text.endswith('.'):
        clean_text += '.'
    
    # Capitalize first letter of each sentence
    clean_text = '. '.join(s.strip().capitalize() for s in clean_text.split('.') if s.strip())
    
    return {
        'garment_type': garment_type,
        'clean_description': clean_text[:400],  # Limit length
        'key_features': key_features[:5],  # Max 5 features
    }


def build_tryon_prompt(raw_description: str) -> str:
    """Build a FLUX prompt from raw product description.
    
    Uses simple string interpolation with cleaned description.
    """
    cleaned = clean_description(raw_description)
    
    garment_type = cleaned['garment_type']
    features = cleaned['key_features']
    
    # Build feature string
    if features:
        feature_str = ', '.join(features)
        feature_text = f" The {garment_type} has {feature_str}."
    else:
        feature_text = ""
    
    # Simple template prompt
    prompt = (
        f"Keep the exact same person from reference image 1 — "
        f"preserve their face, hair, skin tone, body shape, pose, and background exactly. "
        f"ONLY replace their clothing with the {garment_type} shown in reference image 2."
        f"{feature_text} "
        f"The person should look identical except for wearing this {garment_type}."
    )
    
    return prompt
