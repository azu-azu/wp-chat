# src/highlight.py - Query highlighting functionality
import re
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

def extract_keywords_from_query(query: str, max_keywords: int = 10) -> List[str]:
    """Extract important keywords from query"""
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

def highlight_text(text: str, keywords: List[str], max_length: int = 200) -> str:
    """Highlight keywords in text with <em> tags"""
    if not keywords:
        return text[:max_length] + ("…" if len(text) > max_length else "")

    # Create regex pattern for case-insensitive matching
    pattern = '|'.join(re.escape(keyword) for keyword in keywords)
    regex = re.compile(f'({pattern})', re.IGNORECASE)

    # Highlight matches
    highlighted = regex.sub(r'<em>\1</em>', text)

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

def highlight_snippet(text: str, query: str, max_length: int = 200) -> str:
    """Create highlighted snippet from text based on query"""
    keywords = extract_keywords_from_query(query)
    return highlight_text(text, keywords, max_length)

def highlight_results(results: List[dict], query: str, max_length: int = 200) -> List[dict]:
    """Add highlighted snippets to search results"""
    highlighted_results = []

    for result in results:
        highlighted_result = result.copy()

        # Highlight the snippet if it exists
        if 'snippet' in result:
            highlighted_result['snippet'] = highlight_snippet(result['snippet'], query, max_length)

        # Also highlight the title
        if 'title' in result:
            highlighted_result['title'] = highlight_text(result['title'], extract_keywords_from_query(query), 100)

        highlighted_results.append(highlighted_result)

    return highlighted_results
