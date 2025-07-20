#!/usr/bin/env python3
"""
Backend API Testing Script for Crypto Screener
Tests the implemented features: configurable intervals and history loading
"""

import requests
import json
import time
import sys
from typing import Dict, Any, List

# Use the production URL from frontend/.env
BASE_URL = "https://af0849c5-3dfc-4bda-91cb-0b368ca074da.preview.emergentagent.com/api"

class CryptoScreenerTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.timeout = 30
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
    
    def test_basic_endpoints(self):
        """Test basic API endpoints"""
        print("\n=== Testing Basic Endpoints ===")
        
        # Test root endpoint
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "MEXC TradingView Screener API" in data["message"]:
                    self.log_test("Root endpoint (/api/)", True, f"Version: {data.get('message', 'N/A')}")
                else:
                    self.log_test("Root endpoint (/api/)", False, f"Unexpected response format: {data}")
            else:
                self.log_test("Root endpoint (/api/)", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Root endpoint (/api/)", False, f"Exception: {str(e)}")
        
        # Test health endpoint
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    active_symbols = data.get("active_symbols", 0)
                    total_tickers = data.get("total_supported_tickers", 0)
                    self.log_test("Health endpoint (/api/health)", True, 
                                f"Active symbols: {active_symbols}, Total tickers: {total_tickers}")
                else:
                    self.log_test("Health endpoint (/api/health)", False, f"Status not healthy: {data}")
            else:
                self.log_test("Health endpoint (/api/health)", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Health endpoint (/api/health)", False, f"Exception: {str(e)}")
        
        # Test tickers endpoint
        try:
            response = self.session.get(f"{self.base_url}/tickers")
            if response.status_code == 200:
                data = response.json()
                if "tickers" in data and "count" in data:
                    ticker_count = data["count"]
                    self.log_test("Tickers endpoint (/api/tickers)", True, 
                                f"Returned {ticker_count} tickers")
                else:
                    self.log_test("Tickers endpoint (/api/tickers)", False, f"Missing required fields: {data}")
            else:
                self.log_test("Tickers endpoint (/api/tickers)", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Tickers endpoint (/api/tickers)", False, f"Exception: {str(e)}")
    
    def test_configurable_intervals(self):
        """Test configurable intervals feature"""
        print("\n=== Testing Configurable Intervals Feature ===")
        
        # Test default intervals
        try:
            response = self.session.get(f"{self.base_url}/crypto/prices?limit=5")
            if response.status_code == 200:
                data = response.json()
                if "data" in data and data["data"]:
                    # Check if we have the expected fields
                    first_symbol = list(data["data"].keys())[0]
                    first_item = data["data"][first_symbol]
                    
                    has_interval_configs = "interval_configs" in first_item
                    has_change_interval_0 = "change_interval_0" in first_item
                    has_change_interval_1 = "change_interval_1" in first_item
                    has_change_interval_2 = "change_interval_2" in first_item
                    
                    if has_interval_configs and has_change_interval_0 and has_change_interval_1 and has_change_interval_2:
                        interval_configs = first_item["interval_configs"]
                        self.log_test("Default intervals support", True, 
                                    f"Default configs: {interval_configs}")
                    else:
                        missing_fields = []
                        if not has_interval_configs: missing_fields.append("interval_configs")
                        if not has_change_interval_0: missing_fields.append("change_interval_0")
                        if not has_change_interval_1: missing_fields.append("change_interval_1")
                        if not has_change_interval_2: missing_fields.append("change_interval_2")
                        self.log_test("Default intervals support", False, 
                                    f"Missing fields: {missing_fields}")
                else:
                    self.log_test("Default intervals support", False, "No data returned")
            else:
                self.log_test("Default intervals support", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Default intervals support", False, f"Exception: {str(e)}")
        
        # Test custom intervals
        test_cases = [
            ("15s,30s,24h", "Standard intervals"),
            ("2s,5m,1h", "Mixed short/medium/long intervals"),
            ("1m,10m,4h", "All minute/hour intervals"),
            ("5s,15s,30s", "All seconds intervals")
        ]
        
        for interval_config, description in test_cases:
            try:
                response = self.session.get(
                    f"{self.base_url}/crypto/prices?limit=3&interval_configs={interval_config}"
                )
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and data["data"]:
                        first_symbol = list(data["data"].keys())[0]
                        first_item = data["data"][first_symbol]
                        
                        returned_configs = first_item.get("interval_configs", [])
                        expected_configs = [i.strip() for i in interval_config.split(',')]
                        
                        if returned_configs == expected_configs:
                            self.log_test(f"Custom intervals: {description}", True, 
                                        f"Configs: {returned_configs}")
                        else:
                            self.log_test(f"Custom intervals: {description}", False, 
                                        f"Expected: {expected_configs}, Got: {returned_configs}")
                    else:
                        self.log_test(f"Custom intervals: {description}", False, "No data returned")
                else:
                    self.log_test(f"Custom intervals: {description}", False, f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Custom intervals: {description}", False, f"Exception: {str(e)}")
        
        # Test sorting by interval columns
        try:
            response = self.session.get(
                f"{self.base_url}/crypto/prices?limit=5&sort_by=change_interval_0&sort_order=desc"
            )
            if response.status_code == 200:
                data = response.json()
                if "data" in data and data["data"]:
                    self.log_test("Sorting by interval columns", True, 
                                f"Returned {len(data['data'])} items sorted by change_interval_0")
                else:
                    self.log_test("Sorting by interval columns", False, "No data returned")
            else:
                self.log_test("Sorting by interval columns", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Sorting by interval columns", False, f"Exception: {str(e)}")
    
    def test_history_loading(self):
        """Test history loading feature"""
        print("\n=== Testing History Loading Feature ===")
        
        # Test history status endpoint (should be idle initially)
        try:
            response = self.session.get(f"{self.base_url}/crypto/history-status")
            if response.status_code == 200:
                data = response.json()
                if "status" in data and "progress" in data and "total" in data:
                    initial_status = data["status"]
                    self.log_test("History status endpoint", True, 
                                f"Initial status: {initial_status}, Progress: {data['progress']}/{data['total']}")
                else:
                    self.log_test("History status endpoint", False, f"Missing required fields: {data}")
            else:
                self.log_test("History status endpoint", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("History status endpoint", False, f"Exception: {str(e)}")
        
        # Test starting history load
        try:
            response = self.session.post(f"{self.base_url}/crypto/load-history")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "started":
                    self.log_test("Start history loading", True, 
                                f"Message: {data.get('message', 'N/A')}")
                    
                    # Wait a bit and check status again
                    time.sleep(2)
                    
                    status_response = self.session.get(f"{self.base_url}/crypto/history-status")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        new_status = status_data.get("status", "unknown")
                        progress = status_data.get("progress", 0)
                        total = status_data.get("total", 0)
                        current_symbol = status_data.get("current_symbol", "")
                        
                        if new_status in ["loading", "completed", "idle"]:
                            self.log_test("History loading status change", True, 
                                        f"Status: {new_status}, Progress: {progress}/{total}, Current: {current_symbol}")
                        else:
                            self.log_test("History loading status change", False, 
                                        f"Unexpected status: {new_status}")
                    else:
                        self.log_test("History loading status change", False, 
                                    f"Status check failed: {status_response.status_code}")
                else:
                    self.log_test("Start history loading", False, f"Unexpected response: {data}")
            else:
                self.log_test("Start history loading", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Start history loading", False, f"Exception: {str(e)}")
        
        # Test multiple status checks to see progress
        print("   Monitoring history loading progress...")
        for i in range(3):
            try:
                time.sleep(1)
                response = self.session.get(f"{self.base_url}/crypto/history-status")
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status", "unknown")
                    progress = data.get("progress", 0)
                    total = data.get("total", 0)
                    current_symbol = data.get("current_symbol", "")
                    
                    print(f"   Check {i+1}: Status={status}, Progress={progress}/{total}, Symbol={current_symbol}")
                    
                    if i == 2:  # Last check
                        if status in ["loading", "completed", "idle"]:
                            self.log_test("History loading progress monitoring", True, 
                                        f"Final status: {status}, Progress: {progress}/{total}")
                        else:
                            self.log_test("History loading progress monitoring", False, 
                                        f"Unexpected final status: {status}")
                else:
                    print(f"   Check {i+1}: Failed with status {response.status_code}")
            except Exception as e:
                print(f"   Check {i+1}: Exception - {str(e)}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Crypto Screener Backend API Tests")
        print(f"Testing against: {self.base_url}")
        
        # Run test suites
        self.test_basic_endpoints()
        self.test_configurable_intervals()
        self.test_history_loading()
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['details']}")
        
        print("\n" + "="*60)
        return failed_tests == 0

if __name__ == "__main__":
    tester = CryptoScreenerTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)