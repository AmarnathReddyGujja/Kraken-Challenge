#!/usr/bin/env python
"""
Custom test runner for the Meter Reading application.

This script provides a convenient way to run different types of tests
with various configurations and reporting options.
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

def run_tests(test_labels=None, verbosity=1, interactive=True, keepdb=False, parallel=None, failfast=False):
    """Run the test suite with specified options."""
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kraken_project.settings')
    django.setup()
    
    # Get test runner
    TestRunner = get_runner(settings)
    
    # Create test runner instance
    test_runner = TestRunner(
        verbosity=verbosity,
        interactive=interactive,
        keepdb=keepdb,
        parallel=parallel,
        failfast=failfast
    )
    
    # Run tests
    failures = test_runner.run_tests(test_labels)
    
    return failures

def run_unit_tests():
    """Run only unit tests."""
    print("Running unit tests...")
    return run_tests(['meter_readings.tests.ModelTests', 'meter_readings.tests.ParserTests'])

def run_integration_tests():
    """Run only integration tests."""
    print("Running integration tests...")
    return run_tests(['meter_readings.tests.IntegrationTests', 'meter_readings.tests.ViewTests'])

def run_performance_tests():
    """Run only performance tests."""
    print("Running performance tests...")
    return run_tests(['meter_readings.tests.PerformanceTests'])

def run_all_tests():
    """Run all tests."""
    print("Running all tests...")
    return run_tests()

def run_smoke_tests():
    """Run only smoke tests."""
    print("Running smoke tests...")
    return run_tests(['meter_readings.tests.SmokeTests'])

if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        
        if test_type == 'unit':
            failures = run_unit_tests()
        elif test_type == 'integration':
            failures = run_integration_tests()
        elif test_type == 'performance':
            failures = run_performance_tests()
        elif test_type == 'smoke':
            failures = run_smoke_tests()
        elif test_type == 'all':
            failures = run_all_tests()
        else:
            print(f"Unknown test type: {test_type}")
            print("Available types: unit, integration, performance, smoke, all")
            sys.exit(1)
    else:
        failures = run_all_tests()
    
    sys.exit(failures)
