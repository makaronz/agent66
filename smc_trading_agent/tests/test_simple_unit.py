"""
Simple unit tests to verify test coverage setup works.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime


def simple_function(x, y):
    """Simple function for testing."""
    if x > y:
        return x + y
    elif x < y:
        return x - y
    else:
        return x * y


def data_processing_function(data):
    """Simple data processing function."""
    if not data:
        return []
    
    processed = []
    for item in data:
        if isinstance(item, (int, float)) and item > 0:
            processed.append(item * 2)
        else:
            processed.append(0)
    
    return processed


class SimpleCalculator:
    """Simple calculator class for testing."""
    
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        result = a + b
        self.history.append(('add', a, b, result))
        return result
    
    def subtract(self, a, b):
        result = a - b
        self.history.append(('subtract', a, b, result))
        return result
    
    def multiply(self, a, b):
        result = a * b
        self.history.append(('multiply', a, b, result))
        return result
    
    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self.history.append(('divide', a, b, result))
        return result
    
    def get_history(self):
        return self.history.copy()
    
    def clear_history(self):
        self.history.clear()


class TestSimpleFunctions:
    """Test simple functions."""
    
    def test_simple_function_greater(self):
        """Test simple function when x > y."""
        result = simple_function(5, 3)
        assert result == 8
    
    def test_simple_function_less(self):
        """Test simple function when x < y."""
        result = simple_function(3, 5)
        assert result == -2
    
    def test_simple_function_equal(self):
        """Test simple function when x == y."""
        result = simple_function(4, 4)
        assert result == 16
    
    @pytest.mark.parametrize("x,y,expected", [
        (10, 5, 15),
        (2, 8, -6),
        (7, 7, 49),
        (0, 0, 0),
        (-3, -3, 9)
    ])
    def test_simple_function_parametrized(self, x, y, expected):
        """Test simple function with various parameters."""
        result = simple_function(x, y)
        assert result == expected


class TestDataProcessing:
    """Test data processing functions."""
    
    def test_data_processing_empty_list(self):
        """Test data processing with empty list."""
        result = data_processing_function([])
        assert result == []
    
    def test_data_processing_positive_numbers(self):
        """Test data processing with positive numbers."""
        data = [1, 2, 3, 4, 5]
        result = data_processing_function(data)
        assert result == [2, 4, 6, 8, 10]
    
    def test_data_processing_mixed_data(self):
        """Test data processing with mixed data types."""
        data = [1, -2, 0, 3.5, "string", None]
        result = data_processing_function(data)
        assert result == [2, 0, 0, 7.0, 0, 0]
    
    def test_data_processing_edge_cases(self):
        """Test data processing with edge cases."""
        data = [0.1, -0.1, float('inf'), float('-inf')]
        result = data_processing_function(data)
        assert result == [0.2, 0, float('inf'), 0]


class TestSimpleCalculator:
    """Test simple calculator class."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator instance for testing."""
        return SimpleCalculator()
    
    def test_calculator_add(self, calculator):
        """Test calculator addition."""
        result = calculator.add(5, 3)
        assert result == 8
        
        history = calculator.get_history()
        assert len(history) == 1
        assert history[0] == ('add', 5, 3, 8)
    
    def test_calculator_subtract(self, calculator):
        """Test calculator subtraction."""
        result = calculator.subtract(10, 4)
        assert result == 6
        
        history = calculator.get_history()
        assert len(history) == 1
        assert history[0] == ('subtract', 10, 4, 6)
    
    def test_calculator_multiply(self, calculator):
        """Test calculator multiplication."""
        result = calculator.multiply(6, 7)
        assert result == 42
        
        history = calculator.get_history()
        assert len(history) == 1
        assert history[0] == ('multiply', 6, 7, 42)
    
    def test_calculator_divide(self, calculator):
        """Test calculator division."""
        result = calculator.divide(15, 3)
        assert result == 5.0
        
        history = calculator.get_history()
        assert len(history) == 1
        assert history[0] == ('divide', 15, 3, 5.0)
    
    def test_calculator_divide_by_zero(self, calculator):
        """Test calculator division by zero."""
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            calculator.divide(10, 0)
        
        # History should be empty since operation failed
        history = calculator.get_history()
        assert len(history) == 0
    
    def test_calculator_multiple_operations(self, calculator):
        """Test calculator with multiple operations."""
        calculator.add(5, 3)
        calculator.subtract(10, 2)
        calculator.multiply(4, 6)
        
        history = calculator.get_history()
        assert len(history) == 3
        assert history[0] == ('add', 5, 3, 8)
        assert history[1] == ('subtract', 10, 2, 8)
        assert history[2] == ('multiply', 4, 6, 24)
    
    def test_calculator_clear_history(self, calculator):
        """Test calculator history clearing."""
        calculator.add(1, 2)
        calculator.subtract(5, 3)
        
        assert len(calculator.get_history()) == 2
        
        calculator.clear_history()
        assert len(calculator.get_history()) == 0
    
    @pytest.mark.parametrize("operation,a,b,expected", [
        ("add", 1, 2, 3),
        ("subtract", 5, 3, 2),
        ("multiply", 4, 5, 20),
        ("divide", 12, 3, 4.0)
    ])
    def test_calculator_operations_parametrized(self, calculator, operation, a, b, expected):
        """Test calculator operations with parameters."""
        method = getattr(calculator, operation)
        result = method(a, b)
        assert result == expected


class TestDataFrameOperations:
    """Test pandas DataFrame operations."""
    
    @pytest.fixture
    def sample_dataframe(self):
        """Create sample DataFrame for testing."""
        return pd.DataFrame({
            'A': [1, 2, 3, 4, 5],
            'B': [10, 20, 30, 40, 50],
            'C': [0.1, 0.2, 0.3, 0.4, 0.5]
        })
    
    def test_dataframe_creation(self, sample_dataframe):
        """Test DataFrame creation and basic properties."""
        assert len(sample_dataframe) == 5
        assert list(sample_dataframe.columns) == ['A', 'B', 'C']
        assert sample_dataframe['A'].sum() == 15
    
    def test_dataframe_operations(self, sample_dataframe):
        """Test DataFrame mathematical operations."""
        # Test column addition
        sample_dataframe['D'] = sample_dataframe['A'] + sample_dataframe['B']
        assert sample_dataframe['D'].tolist() == [11, 22, 33, 44, 55]
        
        # Test column multiplication
        sample_dataframe['E'] = sample_dataframe['A'] * sample_dataframe['C']
        expected = [0.1, 0.4, 0.9, 1.6, 2.5]
        # Use pytest.approx for floating point comparison
        assert sample_dataframe['E'].tolist() == pytest.approx(expected, rel=1e-9)
    
    def test_dataframe_filtering(self, sample_dataframe):
        """Test DataFrame filtering operations."""
        filtered = sample_dataframe[sample_dataframe['A'] > 3]
        assert len(filtered) == 2
        assert filtered['A'].tolist() == [4, 5]
    
    def test_dataframe_aggregation(self, sample_dataframe):
        """Test DataFrame aggregation operations."""
        stats = sample_dataframe.describe()
        assert stats.loc['mean', 'A'] == 3.0
        assert stats.loc['std', 'B'] == pytest.approx(15.811, rel=1e-3)


@pytest.mark.unit
class TestPerformanceBasics:
    """Basic performance tests."""
    
    def test_list_comprehension_performance(self):
        """Test list comprehension performance."""
        import time
        
        # Test data
        data = list(range(10000))
        
        # Measure list comprehension
        start_time = time.perf_counter()
        result = [x * 2 for x in data if x % 2 == 0]
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        
        # Should complete quickly
        assert duration < 0.1  # Less than 100ms
        assert len(result) == 5000  # Half the numbers are even
    
    def test_numpy_operations_performance(self):
        """Test NumPy operations performance."""
        import time
        
        # Create test arrays
        arr1 = np.random.rand(10000)
        arr2 = np.random.rand(10000)
        
        # Measure NumPy operations
        start_time = time.perf_counter()
        result = arr1 + arr2
        mean_result = np.mean(result)
        std_result = np.std(result)
        end_time = time.perf_counter()
        
        duration = end_time - start_time
        
        # Should complete quickly
        assert duration < 0.1  # Less than 100ms
        assert len(result) == 10000
        assert isinstance(mean_result, (float, np.floating))
        assert isinstance(std_result, (float, np.floating))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])