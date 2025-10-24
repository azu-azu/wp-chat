# src/generation.py - Core RAG generation module
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from .config import get_config_value
from .prompts import build_messages, build_fallback_prompt, validate_citations, format_references

@dataclass
class GenerationResult:
    """Result of generation process"""
    answer: str
    references: List[Dict[str, str]]
    metadata: Dict[str, Any]
    citations: List[int]
    is_valid: bool
    error_message: Optional[str] = None

class ContextComposer:
    """Compose context from retrieved documents with token budgeting"""

    def __init__(self):
        self.max_context_tokens = get_config_value("generation.context_max_tokens", 3500)
        self.max_chunk_tokens = get_config_value("generation.chunk_max_tokens", 1000)
        self.max_chunks = get_config_value("generation.max_chunks", 5)

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 chars per token for Japanese/English"""
        return len(text) // 4

    def deduplicate_by_url(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate documents by URL, keeping highest scoring ones"""
        url_map = {}

        for doc in docs:
            url = doc.get('url', '')
            if url not in url_map or doc.get('hybrid_score', 0) > url_map[url].get('hybrid_score', 0):
                url_map[url] = doc

        return list(url_map.values())

    def truncate_chunk(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit"""
        if self.estimate_tokens(text) <= max_tokens:
            return text

        # Truncate by characters (rough approximation)
        max_chars = max_tokens * 4
        truncated = text[:max_chars]

        # Try to end at a sentence boundary
        last_period = truncated.rfind('。')
        last_exclamation = truncated.rfind('！')
        last_question = truncated.rfind('？')

        sentence_end = max(last_period, last_exclamation, last_question)
        if sentence_end > max_chars * 0.8:  # Only if we don't lose too much
            truncated = truncated[:sentence_end + 1]

        return truncated + ("…" if len(text) > max_chars else "")

    def compose_context(self, docs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Compose context from documents with token budgeting"""
        if not docs:
            return [], {"total_tokens": 0, "chunks_used": 0, "chunks_truncated": 0}

        # Deduplicate by URL
        unique_docs = self.deduplicate_by_url(docs)

        # Sort by hybrid score (descending)
        unique_docs.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)

        # Limit number of chunks
        selected_docs = unique_docs[:self.max_chunks]

        # Process each document
        processed_docs = []
        total_tokens = 0
        chunks_truncated = 0

        for doc in selected_docs:
            # Extract text content
            text = doc.get('snippet', '') or doc.get('chunk', '')
            if not text:
                continue

            # Estimate tokens for this chunk
            chunk_tokens = self.estimate_tokens(text)

            # Truncate if necessary
            if chunk_tokens > self.max_chunk_tokens:
                text = self.truncate_chunk(text, self.max_chunk_tokens)
                chunk_tokens = self.estimate_tokens(text)
                chunks_truncated += 1

            # Check if adding this chunk would exceed total limit
            if total_tokens + chunk_tokens > self.max_context_tokens:
                break

            # Create processed document
            processed_doc = {
                'title': doc.get('title', 'Unknown Title'),
                'url': doc.get('url', ''),
                'snippet': text,
                'post_id': doc.get('post_id', ''),
                'chunk_id': doc.get('chunk_id', ''),
                'hybrid_score': doc.get('hybrid_score', 0),
                'ce_score': doc.get('ce_score')
            }

            processed_docs.append(processed_doc)
            total_tokens += chunk_tokens

        metadata = {
            "total_tokens": total_tokens,
            "chunks_used": len(processed_docs),
            "chunks_truncated": chunks_truncated,
            "original_chunks": len(docs),
            "unique_chunks": len(unique_docs)
        }

        return processed_docs, metadata

class CitationProcessor:
    """Process citations in generated text"""

    def __init__(self):
        self.citation_style = get_config_value("generation.citation_style", "bracketed")

    def inject_citations(self, text: str, docs: List[Dict[str, Any]]) -> Tuple[str, List[int]]:
        """Ensure proper citation format in text"""
        # For now, assume the LLM already includes citations
        # This could be enhanced to automatically inject citations if missing
        from .prompts import extract_citations_from_text
        citations = extract_citations_from_text(text)
        return text, citations

    def validate_and_fix_citations(self, text: str, docs: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
        """Validate citations and fix if necessary"""
        validation_result = validate_citations(text, len(docs))

        if not validation_result["is_valid"]:
            # Log warning but don't modify text
            print(f"Warning: Invalid citations found: {validation_result['invalid_citations']}")

        return text, validation_result

class GenerationPipeline:
    """Main generation pipeline"""

    def __init__(self):
        self.context_composer = ContextComposer()
        self.citation_processor = CitationProcessor()

    def process_retrieval_results(self, docs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Process retrieval results into context"""
        return self.context_composer.compose_context(docs)

    def build_prompt(self, question: str, docs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """Build prompt for LLM"""
        if not docs:
            messages = build_fallback_prompt(question)
            prompt_stats = {"total_tokens": 0, "context_tokens": 0}
        else:
            messages = build_messages(question, docs)
            from .prompts import get_prompt_stats
            prompt_stats = get_prompt_stats(messages)

        return messages, prompt_stats

    def post_process_response(self, text: str, docs: List[Dict[str, Any]]) -> GenerationResult:
        """Post-process LLM response"""
        # Process citations
        processed_text, citation_validation = self.citation_processor.validate_and_fix_citations(text, docs)

        # Format references
        references = format_references(docs)

        # Extract citations
        from .prompts import extract_citations_from_text
        citations = extract_citations_from_text(processed_text)

        # Build metadata
        metadata = {
            "citation_count": len(citations),
            "has_citations": len(citations) > 0,
            "references_count": len(references),
            "citation_validation": citation_validation
        }

        return GenerationResult(
            answer=processed_text,
            references=references,
            metadata=metadata,
            citations=citations,
            is_valid=citation_validation["is_valid"]
        )

    def generate_fallback_response(self, question: str, docs: List[Dict[str, Any]]) -> GenerationResult:
        """Generate fallback response when LLM fails"""
        if docs:
            # Return retrieval results with explanation
            answer = f"申し訳ございませんが、現在AIによる回答生成が利用できません。\n\n関連する情報を以下に示します：\n\n"

            for i, doc in enumerate(docs[:3], 1):  # Show top 3
                answer += f"{i}. **{doc.get('title', 'Unknown Title')}**\n"
                answer += f"   {doc.get('url', '')}\n"
                if doc.get('snippet'):
                    answer += f"   {doc.get('snippet', '')[:200]}...\n\n"
        else:
            answer = "申し訳ございませんが、ご質問に関連する情報が見つかりませんでした。"

        references = format_references(docs) if docs else []

        return GenerationResult(
            answer=answer,
            references=references,
            metadata={"fallback": True, "reason": "llm_unavailable"},
            citations=[],
            is_valid=True,
            error_message="LLM generation failed, using fallback"
        )

# Global pipeline instance
generation_pipeline = GenerationPipeline()
