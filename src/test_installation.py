#!/usr/bin/env python3
"""
Installation verification script
Tests that all modules can be imported and basic functionality works
"""

import sys
import os

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from config import DISCOUNT_RATE, CONSERVATIVE_PE
        print("  ✓ config.py imported successfully")
        
        from data_fetcher import StockDataFetcher
        print("  ✓ data_fetcher.py imported successfully")
        
        from valuations import GrahamValuator, ValuationResult
        print("  ✓ valuations.py imported successfully")
        
        from screener import ValueScreener
        print("  ✓ screener.py imported successfully")
        
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic valuation calculations"""
    print("\nTesting basic functionality...")
    
    try:
        from valuations import GrahamValuator
        
        valuator = GrahamValuator()
        
        # Test EPV calculation
        epv = valuator.earnings_power_value(5.0)
        expected_epv = 5.0 / 0.09
        assert abs(epv - expected_epv) < 0.01, f"EPV calculation failed: {epv} != {expected_epv}"
        print(f"  ✓ EPV calculation works (5.0 EPS -> ${epv:.2f})")
        
        # Test conservative multiple
        multiple = valuator.conservative_multiple_valuation(5.0, 15.0, 12.0)
        expected_multiple = 5.0 * 10  # Should use conservative PE of 10
        assert abs(multiple - expected_multiple) < 0.01, f"Multiple calculation failed"
        print(f"  ✓ Multiple valuation works (uses PE of 10 -> ${multiple:.2f})")
        
        # Test interest coverage
        coverage = valuator.calculate_interest_coverage(600_000, 50_000)
        assert abs(coverage - 12.0) < 0.01, "Interest coverage calculation failed"
        print(f"  ✓ Interest coverage works (600k/50k = {coverage:.1f}x)")
        
        return True
    except Exception as e:
        print(f"  ✗ Functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dependencies():
    """Test that required packages are installed"""
    print("\nTesting dependencies...")
    
    dependencies = [
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('yfinance', 'yfinance'),
    ]
    
    all_present = True
    for package_name, import_name in dependencies:
        try:
            __import__(import_name)
            print(f"  ✓ {package_name} installed")
        except ImportError:
            print(f"  ✗ {package_name} NOT installed - run: pip install {package_name}")
            all_present = False
    
    return all_present

def main():
    """Run all tests"""
    print("=" * 70)
    print("VALUE INVESTOR - Installation Verification")
    print("=" * 70)
    
    results = []
    
    # Test dependencies
    results.append(("Dependencies", test_dependencies()))
    
    # Test imports
    results.append(("Imports", test_imports()))
    
    # Test functionality
    results.append(("Functionality", test_basic_functionality()))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8s} - {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n✅ All tests passed! Installation is working correctly.")
        print("\nNext steps:")
        print("  1. Run the demo: python demo.py")
        print("  2. Try quick mode: python main.py --quick")
        print("  3. Read QUICKSTART.md for full guide")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Missing dependencies: pip install -r requirements.txt")
        print("  - Wrong directory: cd to src/ folder first")
        return 1

if __name__ == "__main__":
    sys.exit(main())
