#!/usr/bin/env python3
"""
Test runner for the programas_crubunco application.
This script discovers and runs all tests in the tests directory.
"""
import unittest
import os
import sys

if __name__ == '__main__':
    # Make sure the app directory is in path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
    
    # Discover and run all tests
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    
    # Run the tests
    result = unittest.TextTestRunner().run(test_suite)
    
    # Return non-zero exit code if tests failed
    sys.exit(not result.wasSuccessful())