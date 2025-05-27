# Testing Guide for MCP UI Explorer

This document provides comprehensive information about the testing infrastructure for the MCP UI Explorer project.

## Overview

The project uses a multi-layered testing approach with:

- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: Tests that verify component interactions
- **Performance Tests**: Benchmarking and performance regression detection
- **Security Tests**: Vulnerability scanning and security validation
- **Automated CI/CD**: GitHub Actions for continuous testing

## Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_models.py      # Pydantic model validation tests
│   ├── test_config.py      # Configuration system tests
│   └── test_utils.py       # Utility function tests
├── integration/             # Integration tests
│   └── test_ui_explorer_integration.py  # End-to-end functionality tests
├── performance/             # Performance tests
│   └── test_performance.py # Benchmarking and performance tests
└── conftest.py             # Shared pytest fixtures (if needed)
```

## Running Tests

### Prerequisites

Install development dependencies:

```bash
# Install all development dependencies
make install-dev

# Or install just testing dependencies
pip install -e ".[test]"
```

### Basic Test Commands

```bash
# Run all tests
make test

# Run specific test categories
make test-unit           # Unit tests only
make test-integration    # Integration tests only
make test-performance    # Performance tests only

# Run tests with coverage
make test-coverage

# Run tests quickly (stop on first failure)
make test-fast
```

### Advanced Test Options

```bash
# Run specific test file
pytest tests/unit/test_models.py

# Run specific test class
pytest tests/unit/test_models.py::TestScreenshotUIInput

# Run specific test method
pytest tests/unit/test_models.py::TestScreenshotUIInput::test_default_values

# Run tests with specific markers
pytest -m "unit"          # Run only unit tests
pytest -m "not slow"      # Skip slow tests
pytest -m "integration"   # Run only integration tests

# Run tests with verbose output
pytest -v

# Run tests with extra verbose output
pytest -vv

# Run tests in parallel (if pytest-xdist is installed)
pytest -n auto
```

## Test Categories

### Unit Tests

Unit tests focus on testing individual components in isolation:

- **Models**: Pydantic model validation and serialization
- **Configuration**: Settings loading and validation
- **Utilities**: Helper functions and classes
- **Services**: Individual service classes (mocked dependencies)

**Characteristics:**
- Fast execution (< 1 second per test)
- No external dependencies
- Extensive use of mocking
- High code coverage target (80%+)

### Integration Tests

Integration tests verify that components work together correctly:

- **UI Explorer**: End-to-end functionality testing
- **Service Integration**: Multiple services working together
- **Error Handling**: Error propagation and recovery
- **Configuration Integration**: Settings affecting behavior

**Characteristics:**
- Moderate execution time (1-10 seconds per test)
- May use mocked external services
- Focus on component interactions
- Real-world scenario simulation

### Performance Tests

Performance tests ensure the application meets performance requirements:

- **Benchmarking**: Measure execution time of critical operations
- **Memory Usage**: Monitor memory consumption
- **Scalability**: Test with large datasets
- **Regression Detection**: Catch performance regressions

**Characteristics:**
- Longer execution time (10+ seconds per test)
- Statistical analysis of results
- Baseline comparison
- Resource usage monitoring

## Test Configuration

### pytest Configuration

The project uses `pytest.ini` and `pyproject.toml` for configuration:

```ini
# Key pytest settings
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
```

### Coverage Configuration

Coverage settings in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src/mcp_ui_explorer"]
omit = ["*/tests/*", "*/test_*"]

[tool.coverage.report]
exclude_lines = ["pragma: no cover", "def __repr__"]
```

### Markers

Available test markers:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.performance`: Performance tests
- `@pytest.mark.slow`: Slow-running tests
- `@pytest.mark.asyncio`: Async tests

## Writing Tests

### Unit Test Example

```python
"""Unit test example."""
import pytest
from mcp_ui_explorer.models import ScreenshotUIInput

class TestScreenshotUIInput:
    """Test ScreenshotUIInput model."""

    def test_default_values(self):
        """Test default values are set correctly."""
        input_model = ScreenshotUIInput()
        assert input_model.focus_only is True
        assert input_model.max_depth == 4

    def test_invalid_max_depth(self):
        """Test invalid max_depth raises validation error."""
        with pytest.raises(ValidationError):
            ScreenshotUIInput(max_depth=-1)
```

### Integration Test Example

```python
"""Integration test example."""
import pytest
from unittest.mock import patch
from mcp_ui_explorer import UIExplorer

class TestUIExplorerIntegration:
    """Integration tests for UIExplorer."""

    @pytest.fixture
    def ui_explorer(self):
        """Create a UIExplorer instance for testing."""
        return UIExplorer()

    @pytest.mark.asyncio
    async def test_screenshot_ui_basic(self, ui_explorer):
        """Test basic screenshot functionality."""
        with patch('pyautogui.screenshot'):
            result = await ui_explorer.screenshot_ui()
            assert result["success"] is True
```

### Performance Test Example

```python
"""Performance test example."""
import pytest
from mcp_ui_explorer.utils import CoordinateConverter

class TestPerformance:
    """Performance tests."""

    def test_coordinate_conversion_performance(self, benchmark):
        """Test coordinate conversion performance."""
        converter = CoordinateConverter(1920, 1080)
        
        def convert_coordinates():
            for i in range(1000):
                x, y = i % 1920, i % 1080
                norm_x, norm_y = converter.absolute_to_normalized(x, y)
                converter.normalized_to_absolute(norm_x, norm_y)
        
        benchmark(convert_coordinates)
```

## Mocking Guidelines

### When to Mock

- External services (UI-TARS API, file system)
- System calls (pyautogui, pywinauto)
- Time-dependent operations
- Network requests

### Mocking Examples

```python
# Mock pyautogui operations
with patch('pyautogui.click') as mock_click:
    await ui_explorer.click_ui_element(x=100, y=200)
    mock_click.assert_called_once_with(100, 200)

# Mock async operations
with patch.object(ui_explorer.ui_tars_service, 'analyze_image') as mock_analyze:
    mock_analyze.return_value = {"success": True, "coordinates": {"x": 100, "y": 200}}
    result = await ui_explorer.ui_tars_analyze("image.png", "find button")
```

## Continuous Integration

### GitHub Actions Workflow

The CI pipeline includes:

1. **Code Quality**: Black, isort, flake8, mypy, pylint
2. **Security**: Bandit, safety, Trivy scanning
3. **Testing**: Unit, integration, and performance tests
4. **Build**: Package building and validation
5. **Deployment**: Automated PyPI publishing on release

### Local CI Simulation

```bash
# Run the same checks as CI
make ci

# Run pre-commit checks
make pre-commit
```

## Test Data Management

### Temporary Files

Use `tempfile` for test files:

```python
import tempfile
from pathlib import Path

def test_with_temp_file():
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
        image_path = temp_file.name
    
    try:
        # Use image_path in test
        pass
    finally:
        Path(image_path).unlink(missing_ok=True)
```

### Test Fixtures

Create reusable test data:

```python
@pytest.fixture
def sample_screenshot_input():
    """Sample screenshot input for testing."""
    return ScreenshotUIInput(
        region="screen",
        min_size=20,
        max_depth=4,
        output_prefix="test"
    )
```

## Debugging Tests

### Running Tests in Debug Mode

```bash
# Run with pdb on failure
pytest --pdb

# Run with verbose output
pytest -vv

# Run specific test with output
pytest -s tests/unit/test_models.py::TestScreenshotUIInput::test_default_values
```

### Test Debugging Tips

1. Use `pytest.set_trace()` for breakpoints
2. Add `print()` statements (use `-s` flag)
3. Check test logs in `pytest.log`
4. Use `--tb=short` for shorter tracebacks

## Performance Monitoring

### Benchmark Results

Performance tests generate benchmark data:

```bash
# Run performance tests and save results
make profile

# View benchmark results
cat benchmark.json
```

### Memory Profiling

Monitor memory usage:

```python
import psutil
import os

def test_memory_usage():
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Perform operations
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    assert memory_increase < 100 * 1024 * 1024  # Less than 100MB
```

## Best Practices

### Test Organization

1. **One test class per module/class being tested**
2. **Descriptive test names** that explain what is being tested
3. **Group related tests** in the same class
4. **Use fixtures** for common setup

### Test Quality

1. **Test one thing at a time**
2. **Use meaningful assertions**
3. **Include both positive and negative test cases**
4. **Test edge cases and error conditions**

### Performance

1. **Keep unit tests fast** (< 1 second each)
2. **Use mocks** to avoid slow operations
3. **Mark slow tests** with `@pytest.mark.slow`
4. **Run performance tests separately**

### Maintenance

1. **Update tests when code changes**
2. **Remove obsolete tests**
3. **Keep test dependencies minimal**
4. **Document complex test scenarios**

## Troubleshooting

### Common Issues

1. **Import errors**: Check PYTHONPATH and package installation
2. **Async test failures**: Ensure `@pytest.mark.asyncio` is used
3. **Mock not working**: Verify the import path being mocked
4. **Coverage too low**: Add tests for uncovered code paths

### Environment Issues

1. **Windows-specific tests**: Use `pytest.mark.skipif` for platform-specific tests
2. **Missing dependencies**: Install with `make install-dev`
3. **Permission errors**: Run with appropriate permissions

## Contributing

When adding new tests:

1. **Follow the existing structure**
2. **Add appropriate markers**
3. **Update this documentation** if needed
4. **Ensure tests pass in CI**

For questions about testing, please check the existing tests for examples or open an issue for clarification. 