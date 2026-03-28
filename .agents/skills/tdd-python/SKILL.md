---
name: tdd-python
description: Test-Driven Development workflow for Python projects
---

# TDD Workflow for Python

Test-Driven Development (TDD) workflow specifically for Python projects using pytest.

## The TDD Cycle

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Write  │ -> │  Run    │ -> │ Write   │ -> │ Refactor│
│  Test   │    │  Test   │    │ Code    │    │         │
│  (RED)  │    │  (FAIL) │    │ (GREEN) │    │(IMPROVE)│
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

## Step-by-Step Process

### 1. RED: Write a Failing Test

Before writing any implementation:

```python
# test_calculator.py
def test_add():
    calculator = Calculator()
    result = calculator.add(2, 3)
    assert result == 5
```

**Run the test (should fail):**
```bash
pytest test_calculator.py -v
```

### 2. GREEN: Write Minimal Code

Write just enough code to pass the test:

```python
# calculator.py
class Calculator:
    def add(self, a, b):
        return a + b
```

**Run the test (should pass):**
```bash
pytest test_calculator.py -v
```

### 3. IMPROVE: Refactor

Clean up while keeping tests green:

```python
# calculator.py
class Calculator:
    """Simple calculator with basic operations."""
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
```

## Testing Best Practices

### Test Structure (AAA Pattern)

```python
def test_feature():
    # Arrange
    input_data = create_test_data()
    expected = expected_output()
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected
```

### Fixtures

```python
import pytest

@pytest.fixture
def calculator():
    return Calculator()

@pytest.fixture
def sample_book():
    return Book(title="Test", author="Author")

def test_with_fixture(calculator):
    result = calculator.add(1, 2)
    assert result == 3
```

### Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (0, 0, 0),
    (-1, 1, 0),
    (100, 200, 300),
])
def test_add_parametrized(calculator, a, b, expected):
    assert calculator.add(a, b) == expected
```

### Mocking

```python
from unittest.mock import Mock, patch

def test_with_mock():
    # Mock external service
    mock_service = Mock()
    mock_service.get_data.return_value = {"key": "value"}
    
    result = process_data(mock_service)
    assert result == expected

@patch('module.external_api')
def test_with_patch(mock_api):
    mock_api.return_value = {"status": "ok"}
    result = call_api()
    assert result["status"] == "ok"
```

## Coverage Requirements

Minimum 80% coverage:

```bash
# Run with coverage
pytest --cov=src --cov-report=term-missing

# Generate HTML report
pytest --cov=src --cov-report=html
```

## Test Categories

### Unit Tests
- Test single functions/classes
- Fast execution (< 10ms each)
- No external dependencies (use mocks)

### Integration Tests
- Test component interactions
- May use test database
- Slower but comprehensive

### E2E Tests
- Test complete user flows
- Use real (or staging) services
- Slowest but most realistic

## Common Patterns

### Testing Exceptions

```python
def test_raises_error():
    with pytest.raises(ValueError, match="invalid input"):
        process_data(None)
```

### Testing Async Code

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await async_operation()
    assert result == expected
```

### Testing with Files

```python
import tempfile

def test_file_processing():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt') as f:
        f.write("test content")
        f.flush()
        result = process_file(f.name)
        assert result == "TEST CONTENT"
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_specific.py

# Run with verbose output
pytest -v

# Run only failed tests
pytest --lf

# Run in parallel
pytest -n auto

# Run with debugging
pytest --pdb

# Run specific test
pytest -k test_name
```

## RedCortex-Specific Testing

```bash
# Quick validation (3 queries, no LLM)
python tests/test_queries.py --quick

# Full test suite without LLM (saves costs)
python tests/test_queries.py --no-llm

# Full test suite with LLM (~$0.01 cost)
python tests/test_queries.py

# Run evaluation
python src/evaluation/evaluator.py
```

## Checklist

Before considering a feature complete:

- [ ] Tests written before/during implementation
- [ ] All tests pass
- [ ] 80%+ coverage for new code
- [ ] Edge cases tested
- [ ] Error conditions tested
- [ ] Integration tests for external dependencies
- [ ] Documentation updated
