"""
Unit tests for Query value object
"""

import pytest

from wp_chat.domain.value_objects import Query


class TestQuery:
    """Test suite for Query value object"""

    def test_create_valid_query(self):
        """Test creating a valid query"""
        query = Query(text="test query")
        assert query.text == "test query"

    def test_query_validation_empty_string(self):
        """Test that empty string raises ValueError"""
        with pytest.raises(ValueError, match="Query text cannot be empty"):
            Query(text="")

    def test_query_validation_whitespace_only(self):
        """Test that whitespace-only string raises ValueError"""
        with pytest.raises(ValueError, match="Query text cannot be empty"):
            Query(text="   ")

    def test_query_validation_max_length(self):
        """Test that query exceeding max length raises ValueError"""
        long_text = "a" * 1001
        with pytest.raises(ValueError, match="Query text exceeds maximum length"):
            Query(text=long_text)

    def test_query_normalized(self):
        """Test query normalization"""
        query = Query(text="  test   query  with   spaces  ")
        assert query.normalized() == "test query with spaces"

    def test_query_length(self):
        """Test query length"""
        query = Query(text="test query")
        assert query.length() == 10

    def test_query_word_count(self):
        """Test word count"""
        query = Query(text="one two three four")
        assert query.word_count() == 4

    def test_query_word_count_with_extra_spaces(self):
        """Test word count with extra spaces"""
        query = Query(text="one  two   three")
        assert query.word_count() == 3

    def test_query_is_short(self):
        """Test short query detection"""
        short_query = Query(text="one two")
        long_query = Query(text="one two three four")
        assert short_query.is_short() is True
        assert long_query.is_short() is False

    def test_query_is_long(self):
        """Test long query detection"""
        short_query = Query(text="test query")
        long_query = Query(text="this is a very long query with more than ten words in it")
        assert short_query.is_long() is False
        assert long_query.is_long() is True

    def test_query_contains(self):
        """Test substring search (case-insensitive)"""
        query = Query(text="WordPress Security Best Practices")
        assert query.contains("security") is True
        assert query.contains("WORDPRESS") is True
        assert query.contains("python") is False

    def test_query_starts_with(self):
        """Test prefix check (case-insensitive)"""
        query = Query(text="WordPress is great")
        assert query.starts_with("wordpress") is True
        assert query.starts_with("WORD") is True
        assert query.starts_with("great") is False

    def test_query_to_lowercase(self):
        """Test lowercase conversion"""
        query = Query(text="WordPress Security")
        assert query.to_lowercase() == "wordpress security"

    def test_query_str_representation(self):
        """Test string representation"""
        query = Query(text="  test  query  ")
        assert str(query) == "test query"

    def test_query_len_support(self):
        """Test len() support"""
        query = Query(text="test query")
        assert len(query) == 10

    def test_query_from_string(self):
        """Test factory method"""
        query = Query.from_string("  test query  ")
        assert query.text == "test query"
        assert query.normalized() == "test query"

    def test_query_immutability(self):
        """Test that Query is immutable (frozen dataclass)"""
        query = Query(text="test")
        with pytest.raises((AttributeError, TypeError)):  # FrozenInstanceError
            query.text = "modified"


class TestQueryEdgeCases:
    """Test edge cases for Query value object"""

    def test_query_with_newlines(self):
        """Test query with newline characters"""
        query = Query(text="test\nquery\nwith\nnewlines")
        normalized = query.normalized()
        assert "\n" not in normalized
        assert normalized == "test query with newlines"

    def test_query_with_tabs(self):
        """Test query with tab characters"""
        query = Query(text="test\tquery\twith\ttabs")
        normalized = query.normalized()
        assert "\t" not in normalized
        assert normalized == "test query with tabs"

    def test_query_with_unicode(self):
        """Test query with Unicode characters"""
        query = Query(text="日本語のクエリ")
        assert query.text == "日本語のクエリ"
        assert query.word_count() == 1

    def test_query_with_special_characters(self):
        """Test query with special characters"""
        query = Query(text="test@#$%query")
        assert query.text == "test@#$%query"

    def test_query_exactly_max_length(self):
        """Test query at exactly max length (1000 chars)"""
        text = "a" * 1000
        query = Query(text=text)
        assert query.length() == 1000
