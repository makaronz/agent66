#!/usr/bin/env python3
"""
Security testing script for API endpoints following OWASP guidelines.
Tests for common vulnerabilities like SQL injection, XSS, CSRF, etc.
"""

import asyncio
import json
import logging
import sys
from typing import Dict, List, Any
import aiohttp
import sqlite3
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecurityTester:
    """Security testing framework for API endpoints."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_sql_injection(self) -> None:
        """Test for SQL injection vulnerabilities."""
        logger.info("Testing SQL injection vulnerabilities...")
        
        # Common SQL injection payloads
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "1' OR '1'='1' --",
            "admin'--",
            "1' AND 1=1--",
            "1' AND 1=2--"
        ]
        
        endpoints = [
            "/api/auth/login",
            "/api/users/search",
            "/api/trades/filter"
        ]
        
        for endpoint in endpoints:
            for payload in payloads:
                try:
                    url = urljoin(self.base_url, endpoint)
                    data = {
                        'email': payload,
                        'password': 'test123'
                    }
                    
                    async with self.session.post(url, json=data) as response:
                        content = await response.text()
                        
                        # Check for SQL error messages
                        sql_errors = [
                            'sql syntax',
                            'mysql_fetch',
                            'ora-',
                            'postgresql',
                            'sqlite',
                            'microsoft ole db provider for sql server'
                        ]
                        
                        if any(error in content.lower() for error in sql_errors):
                            self.results['failed'].append({
                                'test': 'SQL Injection',
                                'endpoint': endpoint,
                                'payload': payload,
                                'response': content[:200]
                            })
                        elif response.status == 500:
                            self.results['warnings'].append({
                                'test': 'SQL Injection',
                                'endpoint': endpoint,
                                'payload': payload,
                                'status': response.status
                            })
                        else:
                            self.results['passed'].append({
                                'test': 'SQL Injection',
                                'endpoint': endpoint,
                                'payload': payload
                            })
                            
                except Exception as e:
                    logger.error(f"Error testing SQL injection on {endpoint}: {e}")
    
    async def test_xss(self) -> None:
        """Test for XSS vulnerabilities."""
        logger.info("Testing XSS vulnerabilities...")
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
            "&#60;script&#62;alert('XSS')&#60;/script&#62;"
        ]
        
        endpoints = [
            "/api/users/profile",
            "/api/trades/comment",
            "/api/signals/note"
        ]
        
        for endpoint in endpoints:
            for payload in xss_payloads:
                try:
                    url = urljoin(self.base_url, endpoint)
                    data = {
                        'name': payload,
                        'description': payload,
                        'comment': payload
                    }
                    
                    async with self.session.post(url, json=data) as response:
                        content = await response.text()
                        
                        # Check if payload is reflected in response
                        if payload in content:
                            self.results['failed'].append({
                                'test': 'XSS',
                                'endpoint': endpoint,
                                'payload': payload,
                                'reflected': True
                            })
                        else:
                            self.results['passed'].append({
                                'test': 'XSS',
                                'endpoint': endpoint,
                                'payload': payload
                            })
                            
                except Exception as e:
                    logger.error(f"Error testing XSS on {endpoint}: {e}")
    
    async def test_csrf(self) -> None:
        """Test for CSRF vulnerabilities."""
        logger.info("Testing CSRF vulnerabilities...")
        
        # Test if endpoints accept requests without proper CSRF tokens
        csrf_endpoints = [
            "/api/trades/execute",
            "/api/users/update",
            "/api/settings/change"
        ]
        
        for endpoint in csrf_endpoints:
            try:
                url = urljoin(self.base_url, endpoint)
                headers = {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'  # Some frameworks check this
                }
                data = {'action': 'test'}
                
                async with self.session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        self.results['warnings'].append({
                            'test': 'CSRF',
                            'endpoint': endpoint,
                            'status': response.status,
                            'note': 'Endpoint might be vulnerable to CSRF'
                        })
                    elif response.status == 403:
                        self.results['passed'].append({
                            'test': 'CSRF',
                            'endpoint': endpoint,
                            'status': response.status
                        })
                    else:
                        self.results['warnings'].append({
                            'test': 'CSRF',
                            'endpoint': endpoint,
                            'status': response.status
                        })
                        
            except Exception as e:
                logger.error(f"Error testing CSRF on {endpoint}: {e}")
    
    async def test_authentication(self) -> None:
        """Test authentication and authorization."""
        logger.info("Testing authentication and authorization...")
        
        protected_endpoints = [
            "/api/users/profile",
            "/api/trades/history",
            "/api/settings",
            "/api/admin/users"
        ]
        
        for endpoint in protected_endpoints:
            try:
                url = urljoin(self.base_url, endpoint)
                
                # Test without authentication
                async with self.session.get(url) as response:
                    if response.status == 401:
                        self.results['passed'].append({
                            'test': 'Authentication',
                            'endpoint': endpoint,
                            'status': response.status
                        })
                    else:
                        self.results['failed'].append({
                            'test': 'Authentication',
                            'endpoint': endpoint,
                            'status': response.status,
                            'note': 'Endpoint accessible without authentication'
                        })
                        
            except Exception as e:
                logger.error(f"Error testing authentication on {endpoint}: {e}")
    
    async def test_rate_limiting(self) -> None:
        """Test rate limiting implementation."""
        logger.info("Testing rate limiting...")
        
        rate_limit_endpoints = [
            "/api/auth/login",
            "/api/trades/execute",
            "/api/signals/generate"
        ]
        
        for endpoint in rate_limit_endpoints:
            try:
                url = urljoin(self.base_url, endpoint)
                data = {'test': 'data'}
                
                # Send multiple requests quickly
                responses = []
                for i in range(10):
                    async with self.session.post(url, json=data) as response:
                        responses.append(response.status)
                
                # Check if rate limiting is enforced
                if 429 in responses:
                    self.results['passed'].append({
                        'test': 'Rate Limiting',
                        'endpoint': endpoint,
                        'note': 'Rate limiting enforced'
                    })
                else:
                    self.results['warnings'].append({
                        'test': 'Rate Limiting',
                        'endpoint': endpoint,
                        'note': 'Rate limiting might not be enforced'
                    })
                    
            except Exception as e:
                logger.error(f"Error testing rate limiting on {endpoint}: {e}")
    
    async def test_input_validation(self) -> None:
        """Test input validation."""
        logger.info("Testing input validation...")
        
        validation_tests = [
            {
                'endpoint': '/api/users/register',
                'data': {'email': 'invalid-email', 'password': '123'},
                'expected_status': 400
            },
            {
                'endpoint': '/api/trades/execute',
                'data': {'symbol': '', 'quantity': -1, 'price': 'invalid'},
                'expected_status': 400
            },
            {
                'endpoint': '/api/signals/create',
                'data': {'confidence': 150, 'price_level': 'invalid'},
                'expected_status': 400
            }
        ]
        
        for test in validation_tests:
            try:
                url = urljoin(self.base_url, test['endpoint'])
                
                async with self.session.post(url, json=test['data']) as response:
                    if response.status == test['expected_status']:
                        self.results['passed'].append({
                            'test': 'Input Validation',
                            'endpoint': test['endpoint'],
                            'status': response.status
                        })
                    else:
                        self.results['failed'].append({
                            'test': 'Input Validation',
                            'endpoint': test['endpoint'],
                            'expected': test['expected_status'],
                            'actual': response.status
                        })
                        
            except Exception as e:
                logger.error(f"Error testing input validation on {test['endpoint']}: {e}")
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all security tests."""
        logger.info("Starting comprehensive security testing...")
        
        await self.test_sql_injection()
        await self.test_xss()
        await self.test_csrf()
        await self.test_authentication()
        await self.test_rate_limiting()
        await self.test_input_validation()
        
        return self.results


async def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python security_test.py <base_url>")
        print("Example: python security_test.py http://localhost:8000")
        sys.exit(1)
    
    base_url = sys.argv[1]
    
    async with SecurityTester(base_url) as tester:
        results = await tester.run_all_tests()
        
        # Print results
        print("\n" + "="*50)
        print("SECURITY TEST RESULTS")
        print("="*50)
        
        print(f"\n✅ PASSED: {len(results['passed'])}")
        for test in results['passed'][:5]:  # Show first 5
            print(f"  - {test['test']}: {test.get('endpoint', 'N/A')}")
        
        print(f"\n❌ FAILED: {len(results['failed'])}")
        for test in results['failed']:
            print(f"  - {test['test']}: {test.get('endpoint', 'N/A')}")
            if 'payload' in test:
                print(f"    Payload: {test['payload']}")
        
        print(f"\n⚠️  WARNINGS: {len(results['warnings'])}")
        for test in results['warnings'][:5]:  # Show first 5
            print(f"  - {test['test']}: {test.get('endpoint', 'N/A')}")
        
        # Save detailed results to file
        with open('security_test_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: security_test_results.json")
        
        # Exit with error if any tests failed
        if results['failed']:
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())