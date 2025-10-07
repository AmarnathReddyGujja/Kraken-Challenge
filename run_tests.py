#!/usr/bin/env python
"""
Quick test runner script for the Meter Reading application.

This script provides a simple way to run tests with common configurations.
"""

import os
import sys
import subprocess
import argparse

def run_command(command, description):
    """Run a command and return the exit code."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, check=True)
        print(f"✅ {description} completed successfully")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return e.returncode

def main():
    parser = argparse.ArgumentParser(description='Run tests for Meter Reading application')
    parser.add_argument('--type', choices=['all', 'unit', 'integration', 'smoke', 'quick'], 
                       default='quick', help='Type of tests to run')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--parallel', '-p', action='store_true', help='Run tests in parallel')
    parser.add_argument('--keepdb', '-k', action='store_true', help='Keep test database')
    parser.add_argument('--failfast', '-f', action='store_true', help='Stop on first failure')
    
    args = parser.parse_args()
    
    # Build command
    cmd_parts = ['python', 'manage.py', 'test']
    
    if args.verbose:
        cmd_parts.append('--verbosity=2')
    else:
        cmd_parts.append('--verbosity=1')
    
    if args.parallel:
        cmd_parts.append('--parallel')
    
    if args.keepdb:
        cmd_parts.append('--keepdb')
    
    if args.failfast:
        cmd_parts.append('--failfast')
    
    # Add test labels based on type
    if args.type == 'unit':
        cmd_parts.extend(['meter_readings.tests.ModelTests', 'meter_readings.tests.ParserTests'])
    elif args.type == 'integration':
        cmd_parts.extend(['meter_readings.tests.IntegrationTests', 'meter_readings.tests.ViewTests'])
    elif args.type == 'smoke':
        cmd_parts.append('meter_readings.tests.SmokeTests')
    elif args.type == 'quick':
        cmd_parts.extend(['meter_readings.tests.SmokeTests', 'meter_readings.tests.ModelTests'])
    # 'all' runs all tests (no additional labels needed)
    
    command = ' '.join(cmd_parts)
    
    # Run the tests
    exit_code = run_command(command, f"Running {args.type} tests")
    
    if exit_code == 0:
        print(f"\n🎉 All {args.type} tests passed!")
    else:
        print(f"\n💥 Some {args.type} tests failed!")
    
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
