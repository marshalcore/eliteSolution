# tests/run_tests.py
#!/usr/bin/env python3
"""
Comprehensive Test Runner for EliteSolution Banking System
Run with: python -m tests.run_tests
"""

import sys
import os
import subprocess
import time
import argparse
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

def run_security_tests():
    """Run security-specific tests"""
    print("🔒 Running Security Tests...")
    result = subprocess.run([
        "pytest", "tests/test_security.py", "-v", 
        "--tb=short", "--color=yes"
    ], capture_output=True, text=True)
    return result

def run_authentication_tests():
    """Run authentication-specific tests"""
    print("🔑 Running Authentication Tests...")
    result = subprocess.run([
        "pytest", "tests/test_authentication.py", "-v",
        "--tb=short", "--color=yes"
    ], capture_output=True, text=True)
    return result

def run_trading_tests():
    """Run trading system tests"""
    print("💼 Running Trading System Tests...")
    result = subprocess.run([
        "pytest", "tests/test_trading.py", "-v",
        "--tb=short", "--color=yes"
    ], capture_output=True, text=True)
    return result

def run_account_management_tests():
    """Run account management tests"""
    print("👤 Running Account Management Tests...")
    result = subprocess.run([
        "pytest", "tests/test_account_management.py", "-v",
        "--tb=short", "--color=yes"
    ], capture_output=True, text=True)
    return result

def run_language_tests():
    """Run multi-language system tests"""
    print("🌐 Running Multi-Language Tests...")
    result = subprocess.run([
        "pytest", "tests/test_multilanguage.py", "-v",
        "--tb=short", "--color=yes"
    ], capture_output=True, text=True)
    return result

def run_performance_tests():
    """Run performance tests"""
    print("⚡ Running Performance Tests...")
    result = subprocess.run([
        "pytest", "tests/test_performance.py", "-v",
        "--tb=short", "--color=yes"
    ], capture_output=True, text=True)
    return result

def run_integration_tests():
    """Run integration tests"""
    print("🔄 Running Integration Tests...")
    result = subprocess.run([
        "pytest", "tests/test_integration.py", "-v",
        "--tb=short", "--color=yes"
    ], capture_output=True, text=True)
    return result

def run_all_tests():
    """Run all test suites"""
    print("🚀 Running All Test Suites...")
    result = subprocess.run([
        "pytest", "tests/", "-v",
        "--tb=short", "--color=yes"
    ], capture_output=True, text=True)
    return result

def generate_test_report(results):
    """Generate a comprehensive test report"""
    report = []
    report.append("=" * 70)
    report.append("🧪 ELITESOLUTION BANKING SYSTEM - TEST REPORT")
    report.append("=" * 70)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_suite, result in results.items():
        # Parse pytest output
        lines = result.stdout.split('\n')
        for line in lines:
            if 'passed' in line and 'failed' in line:
                # Extract test counts
                parts = line.split()
                passed = int(parts[0])
                failed = int(parts[2])
                total_tests += passed + failed
                passed_tests += passed
                failed_tests += failed
                
                report.append(f"📊 {test_suite}: {passed} passed, {failed} failed")
                break
    
    report.append("-" * 70)
    report.append(f"📈 TOTAL: {passed_tests} passed, {failed_tests} failed, {total_tests} total")
    
    # Calculate success rate
    if total_tests > 0:
        success_rate = (passed_tests / total_tests) * 100
        report.append(f"🎯 SUCCESS RATE: {success_rate:.1f}%")
    
    # Security assessment
    if failed_tests == 0:
        report.append("✅ SECURITY STATUS: ALL SECURITY TESTS PASSED")
    else:
        report.append("⚠️  SECURITY STATUS: SOME SECURITY TESTS FAILED")
    
    report.append("=" * 70)
    
    return '\n'.join(report)

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description='Run EliteSolution Banking System Tests')
    parser.add_argument('--suite', choices=['all', 'security', 'auth', 'trading', 'account', 'language', 'performance', 'integration'], 
                       default='all', help='Test suite to run')
    parser.add_argument('--report', action='store_true', help='Generate detailed test report')
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    print("🚀 Starting EliteSolution Banking System Test Suite...")
    print("📍 Test Directory:", os.path.abspath(os.path.dirname(__file__)))
    print("-" * 70)
    
    results = {}
    
    if args.suite == 'all' or args.suite == 'security':
        results['Security Tests'] = run_security_tests()
    
    if args.suite == 'all' or args.suite == 'auth':
        results['Authentication Tests'] = run_authentication_tests()
    
    if args.suite == 'all' or args.suite == 'trading':
        results['Trading Tests'] = run_trading_tests()
    
    if args.suite == 'all' or args.suite == 'account':
        results['Account Management Tests'] = run_account_management_tests()
    
    if args.suite == 'all' or args.suite == 'language':
        results['Language Tests'] = run_language_tests()
    
    if args.suite == 'all' or args.suite == 'performance':
        results['Performance Tests'] = run_performance_tests()
    
    if args.suite == 'all' or args.suite == 'integration':
        results['Integration Tests'] = run_integration_tests()
    
    end_time = time.time()
    duration = end_time - start_time
    
    print("-" * 70)
    print(f"⏱️  Test execution completed in {duration:.2f} seconds")
    
    if args.report:
        report = generate_test_report(results)
        print("\n" + report)
        
        # Save report to file
        report_file = "test_report.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"📄 Detailed report saved to: {report_file}")
    
    # Show any failures
    for test_suite, result in results.items():
        if result.returncode != 0:
            print(f"\n❌ {test_suite} had failures:")
            print(result.stderr)
    
    print("🎉 Test execution completed!")

if __name__ == "__main__":
    main()