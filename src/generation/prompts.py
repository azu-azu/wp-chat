# src/prompts.py - Prompt engineering for RAG generation
import json
from typing import List, Dict, Any
from ..core.config import get_config_value

def build_system_prompt() -> str:
    """Build the TsukiUsagi system prompt"""
    return """You are TsukiUsagi Assistant - warm, precise, slightly poetic.

RULES:
- Always cite sources using [[1]], [[2]] format
- If context is insufficient, say "根拠資料が不足しています"
- Never invent URLs or facts not in context
- Prefer Japanese, mix English naturally when helpful
- Be concise but complete
- When citing multiple sources, use [[1,2]] format
- If you're uncertain about something, express that uncertainty

CONTEXT FORMAT:
[1] Title: ...
URL: ...
Content: ...

Answer the user's question using ONLY the provided context. Always include citations."""

def build_user_prompt(question: str, docs: List[Dict[str, Any]]) -> str:
    """Build user prompt with context injection"""
    context_blocks = []

    for i, doc in enumerate(docs, 1):
        # Extract relevant fields
        title = doc.get('title', 'Unknown Title')
        url = doc.get('url', '')
        snippet = doc.get('snippet', '')

        # Format context block
        context_block = f"[{i}] Title: {title}\n"
        if url:
            context_block += f"URL: {url}\n"
        if snippet:
            context_block += f"Content: {snippet}\n"

        context_blocks.append(context_block)

    context = "\n".join(context_blocks)

    return f"""Q: {question}

---
CONTEXT:
{context}
---

Rules:
- Use sources from the context above
- Add 'References' list at the end
- Cite sources using [[1]], [[2]] format
- If context doesn't contain enough information, say so"""

def build_messages(question: str, docs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Build OpenAI messages format"""
    return [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": build_user_prompt(question, docs)}
    ]

def build_fallback_prompt(question: str) -> List[Dict[str, str]]:
    """Build fallback prompt when no context is available"""
    return [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": f"""Q: {question}

No relevant context was found for this question. Please respond politely that you don't have enough information to answer this question accurately."""}
    ]

def extract_citations_from_text(text: str) -> List[int]:
    """Extract citation numbers from text like [[1]], [[2]], [[1,2]]"""
    import re

    # Find all citation patterns
    citation_pattern = r'\[\[(\d+(?:,\d+)*)\]\]'
    matches = re.findall(citation_pattern, text)

    citations = set()
    for match in matches:
        # Handle both single citations [[1]] and multiple [[1,2]]
        numbers = [int(x.strip()) for x in match.split(',')]
        citations.update(numbers)

    return sorted(list(citations))

def validate_citations(text: str, num_docs: int) -> Dict[str, Any]:
    """Validate citations in the generated text"""
    citations = extract_citations_from_text(text)

    # Check for invalid citations
    invalid_citations = [c for c in citations if c < 1 or c > num_docs]

    # Check if citations exist
    has_citations = len(citations) > 0

    return {
        "citations": citations,
        "invalid_citations": invalid_citations,
        "has_citations": has_citations,
        "citation_count": len(citations),
        "is_valid": len(invalid_citations) == 0
    }

def format_references(docs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Format references for the response"""
    references = []

    for i, doc in enumerate(docs, 1):
        ref = {
            "id": i,
            "title": doc.get('title', 'Unknown Title'),
            "url": doc.get('url', ''),
            "post_id": doc.get('post_id', ''),
            "chunk_id": doc.get('chunk_id', '')
        }
        references.append(ref)

    return references

def get_prompt_stats(messages: List[Dict[str, str]]) -> Dict[str, int]:
    """Get token count estimation for prompt"""
    total_chars = sum(len(msg['content']) for msg in messages)

    # Rough estimation: ~4 chars per token for Japanese/English mixed text
    estimated_tokens = total_chars // 4

    return {
        "total_chars": total_chars,
        "estimated_tokens": estimated_tokens,
        "system_tokens": len(messages[0]['content']) // 4 if messages else 0,
        "user_tokens": len(messages[1]['content']) // 4 if len(messages) > 1 else 0
    }
