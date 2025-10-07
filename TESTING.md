# Testing Guide for Meter Reading Application

This document provides comprehensive instructions for running and understanding the test suite for the Meter Reading application.

## Overview

The test suite is designed to ensure the reliability and correctness of the Meter Reading application. It covers:

- **Model Tests**: Database models, relationships, and constraints
- **Parser Tests**: File parsing for UFF, CSV, JSON, XML, and TXT formats
- **View Tests**: Web interface functionality and URL routing
- **File Upload Tests**: File upload and processing
- **Duplicate Prevention Tests**: Checksum-based idempotency
- **Error Handling Tests**: Malformed data and edge cases
- **Database Constraint Tests**: Data integrity and uniqueness
- **Admin Tests**: Django admin interface functionality
- **Management Command Tests**: Django management commands
- **Performance Tests**: Bulk operations and scalability
- **Integration Tests**: End-to-end workflow testing
- **Smoke Tests**: Basic functionality verification

## Prerequisites

Before running tests, ensure you have:

1. Python 3.8+ installed
2. Django 5.2+ installed
3. All project dependencies installed (`pip install -r requirements.txt`)
4. Database configured (SQLite by default)

## Running Tests

### Method 1: Using Django's Test Runner (Recommended)

#### Run All Tests
```bash
python manage.py test
```

#### Run Specific Test Classes
```bash
# Run only model tests
python manage.py test meter_readings.tests.ModelTests

# Run only parser tests
python manage.py test meter_readings.tests.ParserTests

# Run only view tests
python manage.py test meter_readings.tests.ViewTests

# Run only integration tests
python manage.py test meter_readings.tests.IntegrationTests
```

#### Run Specific Test Methods
```bash
# Run a specific test method
python manage.py test meter_readings.tests.ModelTests.test_flow_file_creation

# Run multiple specific tests
python manage.py test meter_readings.tests.ModelTests.test_flow_file_creation meter_readings.tests.ModelTests.test_meter_creation
```

#### Run Tests with Verbose Output
```bash
python manage.py test --verbosity=2
```

#### Run Tests in Parallel
```bash
python manage.py test --parallel
```

#### Run Tests and Keep Database
```bash
python manage.py test --keepdb
```

#### Run Tests and Stop on First Failure
```bash
python manage.py test --failfast
```

### Method 2: Using pytest (Optional)

If you have pytest installed, you can use it instead:

```bash
# Install pytest and pytest-django
pip install pytest pytest-django

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest meter_readings/tests.py

# Run specific test class
pytest meter_readings/tests.py::ModelTests

# Run specific test method
pytest meter_readings/tests.py::ModelTests::test_flow_file_creation
```

### Method 3: Using Custom Test Runner

Use the provided custom test runner for different test categories:

```bash
# Run all tests
python test_runner.py all

# Run only unit tests
python test_runner.py unit

# Run only integration tests
python test_runner.py integration

# Run only performance tests
python test_runner.py performance

# Run only smoke tests
python test_runner.py smoke
```

## Test Categories

### Unit Tests
- **ModelTests**: Test model creation, relationships, and string representations
- **ParserTests**: Test individual parser functionality for different file formats
- **SmokeTests**: Basic functionality verification

### Integration Tests
- **ViewTests**: Test web interface and URL routing
- **FileUploadTests**: Test file upload functionality
- **IntegrationTests**: End-to-end workflow testing

### System Tests
- **DuplicatePreventionTests**: Test checksum-based idempotency
- **ErrorHandlingTests**: Test error handling and edge cases
- **DatabaseConstraintTests**: Test database-level constraints
- **AdminTests**: Test Django admin interface

### Performance Tests
- **PerformanceTests**: Test bulk operations and scalability

## Test Data

The test suite creates temporary test files and data as needed. All test data is cleaned up automatically after each test.

### Sample Test Files

The tests use various sample file formats:

#### UFF Files
- Standard D0010 format with ZHD/026/028/029/ZTR records
- Non-standard format with ZHV/026/028/030/ZPT records

#### CSV Files
```csv
mpan,serial,reading,date
1200023305967,F75A00802,12345.67,2023-01-01
```

#### JSON Files
```json
{
    "readings": [
        {
            "mpan": "1200023305967",
            "serial": "F75A00802",
            "reading": 12345.67,
            "date": "2023-01-01"
        }
    ]
}
```

#### XML Files
```xml
<?xml version="1.0" encoding="UTF-8"?>
<readings>
    <reading mpan="1200023305967" serial="F75A00802" value="12345.67" date="2023-01-01" />
</readings>
```

#### TXT Files
```
1200023305967|F75A00802|12345.67|2023-01-01
```

## Test Configuration

### Database
Tests use a separate test database (SQLite in-memory by default) to avoid affecting your development data.

### File Handling
Tests create temporary files that are automatically cleaned up after each test.

### Logging
Test output includes detailed logging information when using verbose mode.

## Continuous Integration

For CI/CD pipelines, use:

```bash
# Run tests with minimal output
python manage.py test --verbosity=0

# Run tests and generate coverage report (if coverage.py is installed)
coverage run --source='.' manage.py test
coverage report
coverage html
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Database Errors**: Run migrations before tests
3. **File Permission Errors**: Ensure write permissions in temp directories
4. **Memory Issues**: Use `--parallel` for large test suites

### Debug Mode

Run tests with debug output:

```bash
python manage.py test --verbosity=2 --debug-mode
```

### Test Isolation

Each test runs in isolation with a clean database state. If tests are failing due to data conflicts, check for:

- Hardcoded primary keys
- Missing test data cleanup
- Shared test data between tests

## Writing New Tests

When adding new tests:

1. Follow the existing naming convention
2. Use descriptive test method names
3. Include proper setup and teardown
4. Test both success and failure cases
5. Add appropriate assertions
6. Clean up any created data

### Example Test Structure

```python
class NewFeatureTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.test_data = create_test_data()
    
    def test_feature_success_case(self):
        """Test successful feature operation"""
        result = self.feature.operate(self.test_data)
        self.assertEqual(result.status, 'success')
    
    def test_feature_error_case(self):
        """Test feature error handling"""
        with self.assertRaises(ValueError):
            self.feature.operate(invalid_data)
    
    def tearDown(self):
        """Clean up test data"""
        cleanup_test_data()
```

## Performance Considerations

- Use `bulk_create()` for large datasets
- Avoid creating unnecessary test data
- Use database transactions where appropriate
- Consider using `--parallel` for large test suites

## Coverage

To measure test coverage:

```bash
# Install coverage
pip install coverage

# Run tests with coverage
coverage run --source='.' manage.py test

# Generate coverage report
coverage report

# Generate HTML coverage report
coverage html
```

## Best Practices

1. **Test Independence**: Each test should be able to run independently
2. **Clear Naming**: Use descriptive test and method names
3. **Single Responsibility**: Each test should test one specific behavior
4. **Proper Setup/Teardown**: Clean up after each test
5. **Assertions**: Use appropriate assertions for the expected behavior
6. **Error Testing**: Test both success and failure scenarios
7. **Documentation**: Document complex test scenarios

## Resources

- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Python unittest Documentation](https://docs.python.org/3/library/unittest.html)
- [pytest Documentation](https://docs.pytest.org/)
