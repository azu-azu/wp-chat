# src/highlight.py - Query highlighting functionality with morphological analysis
import re
from typing import List, Tuple, Set
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

try:
    from janome.tokenizer import Tokenizer
    JANOME_AVAILABLE = True
except ImportError:
    JANOME_AVAILABLE = False
    print("Warning: janome not available. Using basic highlighting.")

def extract_keywords_with_morphology(query: str, max_keywords: int = 10) -> List[str]:
    """Extract keywords using morphological analysis for Japanese"""
    keywords = []

    if JANOME_AVAILABLE:
        # Use morphological analysis for Japanese
        tokenizer = Tokenizer()
        tokens = tokenizer.tokenize(query)

        # Filter stop words and extract meaningful terms
        stop_words = {
            'の', 'は', 'が', 'を', 'に', 'で', 'と', 'から', 'まで', 'より', 'も', 'か', 'や',
            'について', '教えて', 'ください', 'です', 'である', 'だ', 'する', 'した', 'して',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'
        }

        for token in tokens:
            surface = token.surface
            part_of_speech = token.part_of_speech.split(',')[0]

            # Extract nouns, verbs, adjectives, and important terms
            if (part_of_speech in ['名詞', '動詞', '形容詞', '副詞'] and
                surface not in stop_words and
                len(surface) > 1):
                keywords.append(surface)

            # Also extract compound nouns and technical terms
            if (part_of_speech == '名詞' and
                len(surface) > 2 and
                not surface.isdigit()):
                keywords.append(surface)

    # Fallback to basic extraction if janome is not available
    if not keywords:
        keywords = extract_keywords_basic(query, max_keywords)

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    return unique_keywords[:max_keywords]

def extract_keywords_basic(query: str, max_keywords: int = 10) -> List[str]:
    """Basic keyword extraction (fallback method)"""
    # Filter out common stop words (Japanese and English)
    stop_words = {
        'の', 'は', 'が', 'を', 'に', 'で', 'と', 'から', 'まで', 'より', 'も', 'か', 'や',
        'について', '教えて', 'ください', 'です', 'である', 'だ', 'する', 'した', 'して',
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'
    }

    keywords = []

    # Extract individual words (Japanese and English)
    words = re.findall(r'[a-zA-Z]+|[ひらがなカタカナ一-龯]+', query.lower())
    for word in words:
        if word not in stop_words and len(word) > 1:
            keywords.append(word)

    # Extract 2-word phrases
    phrases_2 = re.findall(r'[a-zA-Z]+\s+[a-zA-Z]+|[ひらがなカタカナ一-龯]+\s+[ひらがなカタカナ一-龯]+', query.lower())
    for phrase in phrases_2:
        if not any(stop in phrase for stop in stop_words):
            keywords.append(phrase)

    # Prioritize longer phrases first
    keywords.sort(key=len, reverse=True)
    return keywords[:max_keywords]

def extract_keywords_from_query(query: str, max_keywords: int = 10, use_morphology: bool = True) -> List[str]:
    """Extract keywords from query with optional morphological analysis"""
    if use_morphology and JANOME_AVAILABLE:
        return extract_keywords_with_morphology(query, max_keywords)
    else:
        return extract_keywords_basic(query, max_keywords)

def highlight_text(text: str, keywords: List[str], max_length: int = 200,
                  highlight_class: str = "em") -> str:
    """Highlight keywords in text with customizable tags"""
    if not keywords:
        return text[:max_length] + ("…" if len(text) > max_length else "")

    # Create regex pattern for case-insensitive matching
    # Prioritize longer keywords first to avoid partial matches
    sorted_keywords = sorted(keywords, key=len, reverse=True)
    pattern = '|'.join(re.escape(keyword) for keyword in sorted_keywords)
    regex = re.compile(f'({pattern})', re.IGNORECASE)

    # Highlight matches with customizable tag
    highlighted = regex.sub(f'<{highlight_class}>\\1</{highlight_class}>', text)

    # Truncate if too long
    if len(highlighted) > max_length:
        # Find the last complete word before max_length
        truncated = highlighted[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # Only truncate at word boundary if it's not too short
            highlighted = truncated[:last_space] + "…"
        else:
            highlighted = truncated + "…"

    return highlighted

def highlight_snippet(text: str, query: str, max_length: int = 200,
                     use_morphology: bool = True) -> str:
    """Create highlighted snippet from text based on query"""
    keywords = extract_keywords_from_query(query, use_morphology=use_morphology)
    return highlight_text(text, keywords, max_length)

def highlight_results(results: List[dict], query: str, max_length: int = 200,
                     use_morphology: bool = True) -> List[dict]:
    """Add highlighted snippets to search results"""
    highlighted_results = []

    for result in results:
        highlighted_result = result.copy()

        # Highlight the snippet if it exists
        if 'snippet' in result:
            highlighted_result['snippet'] = highlight_snippet(
                result['snippet'], query, max_length, use_morphology
            )

        # Also highlight the title
        if 'title' in result:
            keywords = extract_keywords_from_query(query, use_morphology=use_morphology)
            highlighted_result['title'] = highlight_text(result['title'], keywords, 100)

        highlighted_results.append(highlighted_result)

    return highlighted_results

def get_highlight_info(query: str) -> dict:
    """Get information about highlighting capabilities"""
    return {
        "morphology_available": JANOME_AVAILABLE,
        "extracted_keywords": extract_keywords_from_query(query),
        "morphology_keywords": extract_keywords_with_morphology(query) if JANOME_AVAILABLE else [],
        "basic_keywords": extract_keywords_basic(query)
    }
