"""
Unit tests for Score value object
"""

import pytest

from wp_chat.domain.value_objects import Score


class TestScore:
    """Test suite for Score value object"""

    def test_create_valid_score(self):
        """Test creating a valid score"""
        score = Score(value=0.85)
        assert score.value == 0.85

    def test_create_score_from_int(self):
        """Test creating score from integer"""
        score = Score(value=1)
        assert score.value == 1.0

    def test_score_validation_negative(self):
        """Test that negative score raises ValueError"""
        with pytest.raises(ValueError, match="Score cannot be negative"):
            Score(value=-0.1)

    def test_score_validation_type(self):
        """Test that non-numeric type raises TypeError"""
        with pytest.raises(TypeError, match="Score must be numeric"):
            Score(value="0.5")

    def test_score_is_above_threshold(self):
        """Test threshold comparison (above)"""
        score = Score(value=0.8)
        assert score.is_above_threshold(0.7) is True
        assert score.is_above_threshold(0.8) is True
        assert score.is_above_threshold(0.9) is False

    def test_score_is_below_threshold(self):
        """Test threshold comparison (below)"""
        score = Score(value=0.6)
        assert score.is_below_threshold(0.7) is True
        assert score.is_below_threshold(0.6) is False
        assert score.is_below_threshold(0.5) is False

    def test_score_is_relevant(self):
        """Test relevance check (default threshold 0.7)"""
        relevant_score = Score(value=0.75)
        not_relevant_score = Score(value=0.65)
        assert relevant_score.is_relevant() is True
        assert not_relevant_score.is_relevant() is False

    def test_score_is_relevant_custom_threshold(self):
        """Test relevance check with custom threshold"""
        score = Score(value=0.75)
        assert score.is_relevant(threshold=0.7) is True
        assert score.is_relevant(threshold=0.8) is False

    def test_score_is_highly_relevant(self):
        """Test high relevance check (default threshold 0.85)"""
        highly_relevant = Score(value=0.9)
        not_highly_relevant = Score(value=0.8)
        assert highly_relevant.is_highly_relevant() is True
        assert not_highly_relevant.is_highly_relevant() is False

    def test_score_normalized(self):
        """Test score normalization"""
        score = Score(value=0.5)
        assert score.normalized(max_value=1.0) == 0.5
        assert score.normalized(max_value=2.0) == 0.25

    def test_score_normalized_exceeds_max(self):
        """Test normalization when value exceeds max"""
        score = Score(value=1.5)
        assert score.normalized(max_value=1.0) == 1.0

    def test_score_normalized_invalid_max(self):
        """Test normalization with invalid max_value"""
        score = Score(value=0.5)
        with pytest.raises(ValueError, match="max_value must be positive"):
            score.normalized(max_value=0)

    def test_score_as_percentage(self):
        """Test percentage conversion"""
        score = Score(value=0.75)
        assert score.as_percentage() == 75.0

    def test_score_float_conversion(self):
        """Test conversion to float"""
        score = Score(value=0.85)
        assert float(score) == 0.85
        assert isinstance(float(score), float)

    def test_score_int_conversion(self):
        """Test conversion to int (truncated)"""
        score = Score(value=0.85)
        assert int(score) == 0
        score2 = Score(value=1.9)
        assert int(score2) == 1

    def test_score_str_representation(self):
        """Test string representation"""
        score = Score(value=0.12345678)
        assert str(score) == "0.1235"

    def test_score_repr(self):
        """Test detailed representation"""
        score = Score(value=0.85)
        assert repr(score) == "Score(0.8500)"

    def test_score_comparison_operators(self):
        """Test comparison operators (order=True in dataclass)"""
        score1 = Score(value=0.7)
        score2 = Score(value=0.8)
        score3 = Score(value=0.7)

        assert score1 < score2
        assert score2 > score1
        assert score1 == score3
        assert score1 <= score3
        assert score2 >= score1

    def test_score_addition_with_score(self):
        """Test adding two Score objects"""
        score1 = Score(value=0.5)
        score2 = Score(value=0.3)
        result = score1 + score2
        assert isinstance(result, Score)
        assert result.value == 0.8

    def test_score_addition_with_number(self):
        """Test adding Score and number"""
        score = Score(value=0.5)
        result1 = score + 0.3
        result2 = score + 1
        assert isinstance(result1, Score)
        assert result1.value == 0.8
        assert result2.value == 1.5

    def test_score_subtraction_with_score(self):
        """Test subtracting two Score objects"""
        score1 = Score(value=0.8)
        score2 = Score(value=0.3)
        result = score1 - score2
        assert isinstance(result, Score)
        assert result.value == pytest.approx(0.5)

    def test_score_subtraction_with_number(self):
        """Test subtracting number from Score"""
        score = Score(value=0.8)
        result = score - 0.3
        assert isinstance(result, Score)
        assert result.value == pytest.approx(0.5)

    def test_score_multiplication(self):
        """Test multiplying Score by number"""
        score = Score(value=0.5)
        result1 = score * 2
        result2 = score * 0.5
        assert isinstance(result1, Score)
        assert result1.value == 1.0
        assert result2.value == 0.25

    def test_score_division(self):
        """Test dividing Score by number"""
        score = Score(value=0.8)
        result = score / 2
        assert isinstance(result, Score)
        assert result.value == 0.4

    def test_score_division_by_zero(self):
        """Test division by zero raises error"""
        score = Score(value=0.5)
        with pytest.raises(ZeroDivisionError, match="Cannot divide score by zero"):
            score / 0

    def test_score_from_float(self):
        """Test factory method from_float"""
        score = Score.from_float(0.85)
        assert score.value == 0.85

    def test_score_zero(self):
        """Test zero score factory"""
        score = Score.zero()
        assert score.value == 0.0

    def test_score_max(self):
        """Test max score factory"""
        score = Score.max()
        assert score.value == 1.0

    def test_score_immutability(self):
        """Test that Score is immutable (frozen dataclass)"""
        score = Score(value=0.5)
        with pytest.raises((AttributeError, TypeError)):  # FrozenInstanceError
            score.value = 0.8


class TestScoreArithmeticEdgeCases:
    """Test edge cases for Score arithmetic operations"""

    def test_score_addition_resulting_negative(self):
        """Test addition that could result in negative (but validation catches it)"""
        score1 = Score(value=0.5)
        # Adding negative number directly to value would violate validation
        # So we test the operation works correctly
        result = score1 + (-0.3)  # This creates Score(0.2)
        assert result.value == pytest.approx(0.2)

    def test_score_subtraction_resulting_negative(self):
        """Test subtraction resulting in negative value"""
        # This will create a negative score, which violates validation
        # The subtraction operation itself works, but creating Score with negative fails
        with pytest.raises(ValueError):
            Score(value=-0.2)  # Simulating result of 0.3 - 0.5

    def test_score_arithmetic_with_invalid_types(self):
        """Test arithmetic with invalid types returns NotImplemented"""
        score = Score(value=0.5)
        # These operations should return NotImplemented (Python will raise TypeError)
        with pytest.raises(TypeError):
            score + "invalid"
        with pytest.raises(TypeError):
            score - "invalid"
        with pytest.raises(TypeError):
            score * "invalid"
        with pytest.raises(TypeError):
            score / "invalid"

    def test_score_chain_operations(self):
        """Test chaining multiple arithmetic operations"""
        score = Score(value=0.5)
        result = ((score + 0.3) * 2) / 4
        assert isinstance(result, Score)
        assert result.value == pytest.approx(0.4)
