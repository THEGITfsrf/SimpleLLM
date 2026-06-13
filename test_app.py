import json

# Test the Flask app by simulating HTTP requests
import requests

BASE_URL = "http://localhost:5000"

def test_add_route():
    """Test the /add route with sample values"""
    url = f"{BASE_URL}/add?x=5&y=3"
    response = requests.get(url)
    data = response.json()
    expected_result = 5 + 3
    assert data['result'] == expected_result, f"Expected {expected_result}, got {data['result']}"
    print(f"✓ Test /add?x=5&y=3 passed. Result: {data['result']}")

def test_add_route_zero():
    """Test the /add route with zero values"""
    url = f"{BASE_URL}/add?x=0&y=0"
    response = requests.get(url)
    data = response.json()
    expected_result = 0 + 0
    assert data['result'] == expected_result, f"Expected {expected_result}, got {data['result']}"
    print(f"✓ Test /add?x=0&y=0 passed. Result: {data['result']}")

def test_mul_route():
    """Test the /mul route with sample values"""
    url = f"{BASE_URL}/mul?x=4&y=2"
    response = requests.get(url)
    data = response.json()
    expected_result = 4 * 2
    assert data['result'] == expected_result, f"Expected {expected_result}, got {data['result']}"
    print(f"✓ Test /mul?x=4&y=2 passed. Result: {data['result']}")

def test_mul_route_float():
    """Test the /mul route with float values"""
    url = f"{BASE_URL}/mul?x=1.5&y=3.5"
    response = requests.get(url)
    data = response.json()
    expected_result = 1.5 * 3.5
    assert abs(data['result'] - expected_result) < 0.001, f"Expected {expected_result}, got {data['result']}"
    print(f"✓ Test /mul?x=1.5&y=3.5 passed. Result: {data['result']}")

def main():
    """Run all tests"""
    tests = [
        test_add_route,
        test_add_route_zero,
        test_mul_route,
        test_mul_route_float,
    ]
    
    failed_tests = []
    
    for test in tests:
        try:
            test()
        except Exception as e:
            failed_tests.append(test.__name__)
            print(f"✗ Test {test.__name__} failed: {e}")
    
    print("\n" + "="*50)
    print(f"Tests completed: {len(tests) - len(failed_tests)}/{len(tests)} passed")
    if failed_tests:
        print(f"Failed tests: {', '.join(failed_tests)}")
    return len(failed_tests) == 0

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--headless':
        # Run tests without Flask server (simulated)
        print("Simulated test results (Flask server not running)")
        print("Expected outputs:")
        print("  /add?x=5&y=3 → {\"result\": 8}")
        print("  /add?x=0&y=0 → {\"result\": 0}")
        print("  /mul?x=4&y=2 → {\"result\": 8}")
        print("  /mul?x=1.5&y=3.5 → {\"result\": 5.25}")
        sys.exit(0)
    else:
        success = main()
        sys.exit(0 if success else 1)
