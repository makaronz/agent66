#!/usr/bin/env node

const { performance } = require('perf_hooks');
const axios = require('axios');
const WebSocket = require('ws');

class PerformanceValidator {
  constructor(baseUrl = 'http://localhost:5001', wsUrl = 'ws://localhost:5001') {
    this.baseUrl = baseUrl;
    this.wsUrl = wsUrl;
    this.metrics = [];
  }

  startMeasurement(operation) {
    return {
      startTime: performance.now(),
      memoryBefore: process.memoryUsage().heapUsed
    };
  }

  endMeasurement(operation, startTime, memoryBefore, success, error) {
    const endTime = performance.now();
    const memoryAfter = process.memoryUsage().heapUsed;

    const metric = {
      operation,
      startTime,
      endTime,
      duration: endTime - startTime,
      memoryBefore,
      memoryAfter,
      success,
      error
    };

    this.metrics.push(metric);
    return metric;
  }

  async testAPILatency() {
    console.log('🔍 Testing API Latency...');

    const endpoints = [
      '/health',
      '/health/detailed',
      '/health/ready',
      '/metrics'
    ];

    const results = [];

    for (const endpoint of endpoints) {
      const { startTime, memoryBefore } = this.startMeasurement(`GET ${endpoint}`);

      try {
        const response = await axios.get(`${this.baseUrl}${endpoint}`, {
          timeout: 5000
        });

        const metric = this.endMeasurement(
          `GET ${endpoint}`,
          startTime,
          memoryBefore,
          true
        );

        results.push(metric);
        console.log(`✅ ${endpoint}: ${metric.duration.toFixed(2)}ms (${response.status})`);

      } catch (error) {
        const metric = this.endMeasurement(
          `GET ${endpoint}`,
          startTime,
          memoryBefore,
          false,
          error.message
        );

        results.push(metric);
        console.log(`❌ ${endpoint}: ${metric.duration.toFixed(2)}ms (${error.message})`);
      }
    }

    const averageLatency = results.reduce((sum, r) => sum + r.duration, 0) / results.length;
    const meetsRequirement = averageLatency < 200; // 200ms target for general APIs

    return {
      status: meetsRequirement ? 'PASS' : 'FAIL',
      averageLatency,
      results
    };
  }

  async testExchangeAPIs() {
    console.log('🔍 Testing Exchange API Integration...');

    const exchanges = [
      {
        name: 'binance',
        testUrl: 'https://api.binance.com/api/v3/ping',
        expectedRateLimit: 1200
      },
      {
        name: 'bybit',
        testUrl: 'https://api.bybit.com/v5/market/time',
        expectedRateLimit: 120
      }
    ];

    const results = [];

    for (const exchange of exchanges) {
      const startTime = performance.now();

      try {
        const response = await axios.get(exchange.testUrl, {
          timeout: 5000,
          headers: {
            'User-Agent': 'Agent66-Performance-Test/1.0'
          }
        });

        const latency = performance.now() - startTime;
        const rateLimitRemaining = parseInt(response.headers['x-mbx-used-weight-1m'] || '0');

        results.push({
          exchange: exchange.name,
          endpoint: exchange.testUrl,
          latency,
          success: true,
          rateLimitRemaining
        });

        console.log(`✅ ${exchange.name}: ${latency.toFixed(2)}ms`);

      } catch (error) {
        const latency = performance.now() - startTime;

        results.push({
          exchange: exchange.name,
          endpoint: exchange.testUrl,
          latency,
          success: false,
          error: error.response?.status === 429 ? 'Rate limited' : error.message
        });

        console.log(`❌ ${exchange.name}: ${latency.toFixed(2)}ms (${error.response?.status === 429 ? 'Rate limited' : error.message})`);
      }
    }

    const successRate = results.filter(r => r.success).length / results.length;
    const status = successRate >= 0.8 ? 'PASS' : 'FAIL';

    return { status, results };
  }

  async testWebSocketPerformance() {
    console.log('🔍 Testing WebSocket Connection Performance...');

    const results = [];

    return new Promise((resolve) => {
      const { startTime, memoryBefore } = this.startMeasurement('WebSocket Connection');

      const ws = new WebSocket(`${this.wsUrl}/socket.io/?EIO=4&transport=websocket`);

      const timeout = setTimeout(() => {
        ws.close();
        const metric = this.endMeasurement(
          'WebSocket Connection',
          startTime,
          memoryBefore,
          false,
          'WebSocket connection timeout'
        );
        results.push(metric);
        console.log(`❌ WebSocket Connection: timeout`);
        resolve({ status: 'FAIL', results });
      }, 5000);

      ws.on('open', () => {
        clearTimeout(timeout);
        const metric = this.endMeasurement(
          'WebSocket Connection',
          startTime,
          memoryBefore,
          true
        );
        results.push(metric);
        console.log(`✅ WebSocket Connection: ${metric.duration.toFixed(2)}ms`);
        ws.close();
        resolve({ status: 'PASS', results });
      });

      ws.on('error', (error) => {
        clearTimeout(timeout);
        const metric = this.endMeasurement(
          'WebSocket Connection',
          startTime,
          memoryBefore,
          false,
          error.message
        );
        results.push(metric);
        console.log(`❌ WebSocket Connection: ${error.message}`);
        resolve({ status: 'FAIL', results });
      });
    });
  }

  async testRateLimiting() {
    console.log('🔍 Testing Rate Limiting and Error Handling...');

    const results = [];

    // Test rapid requests to trigger rate limiting
    const rapidRequests = [];
    const requestCount = 20;

    for (let i = 0; i < requestCount; i++) {
      rapidRequests.push(
        axios.get(`${this.baseUrl}/health`, { timeout: 1000 })
          .then(response => ({ status: response.status, requestIndex: i }))
          .catch(error => ({
            status: error.response?.status || 500,
            requestIndex: i,
            error: error.message
          }))
      );
    }

    const rapidResults = await Promise.all(rapidRequests);
    const rateLimitedRequests = rapidResults.filter(r => r.status === 429).length;
    const successCount = rapidResults.filter(r => r.status === 200).length;

    results.push({
      test: 'Rapid Requests (20 requests)',
      rateLimitedRequests,
      successCount,
      successRate: (successCount / requestCount) * 100
    });

    console.log(`  Success Rate: ${results[0].successRate.toFixed(1)}%`);
    console.log(`  Rate Limited Requests: ${rateLimitedRequests}`);

    const status = successCount > 0 ? 'PASS' : 'FAIL';
    return { status, results };
  }

  async testLoadConditions() {
    console.log('🔍 Testing System Under Load Conditions...');

    const results = [];
    const concurrencyLevels = [10, 50];

    for (const concurrency of concurrencyLevels) {
      console.log(`  Testing ${concurrency} concurrent requests...`);

      const startTime = performance.now();
      const requests = [];

      // Generate concurrent requests
      for (let i = 0; i < concurrency; i++) {
        requests.push(
          axios.get(`${this.baseUrl}/health`, { timeout: 5000 })
            .catch(error => {
              return {
                status: error.response?.status || 500,
                config: error.config,
                error: error.message
              };
            })
        );
      }

      const responses = await Promise.all(requests);
      const endTime = performance.now();

      const successfulResponses = responses.filter(r => r.status === 200);
      const errorResponses = responses.filter(r => r.status !== 200);

      const totalTime = endTime - startTime;
      const requestsPerSecond = concurrency / (totalTime / 1000);

      const result = {
        concurrentRequests: concurrency,
        requestsPerSecond,
        averageLatency: totalTime / concurrency,
        errorRate: errorResponses.length / responses.length,
        totalRequests: responses.length,
        successfulRequests: successfulResponses.length
      };

      results.push(result);
      console.log(`    ✅ ${result.requestsPerSecond.toFixed(2)} req/s, ${result.averageLatency.toFixed(2)}ms avg latency, ${(result.errorRate * 100).toFixed(1)}% error rate`);
    }

    const meetsCriteria = results.every(r => r.errorRate < 0.1 && r.averageLatency < 1000);
    const status = meetsCriteria ? 'PASS' : 'FAIL';

    return { status, results };
  }

  generateReport() {
    console.log('\n📊 PERFORMANCE VALIDATION REPORT');
    console.log('='.repeat(50));

    const operationGroups = this.metrics.reduce((groups, metric) => {
      const operation = metric.operation.split(' ')[0];
      if (!groups[operation]) groups[operation] = [];
      groups[operation].push(metric);
      return groups;
    }, {});

    Object.entries(operationGroups).forEach(([operation, metrics]) => {
      const avgDuration = metrics.reduce((sum, m) => sum + m.duration, 0) / metrics.length;
      const successRate = (metrics.filter(m => m.success).length / metrics.length) * 100;

      console.log(`\n${operation.toUpperCase()}:`);
      console.log(`  Average Duration: ${avgDuration.toFixed(2)}ms`);
      console.log(`  Success Rate: ${successRate.toFixed(1)}%`);
      console.log(`  Total Operations: ${metrics.length}`);

      if (avgDuration > 200) {
        console.log(`  ⚠️  WARNING: Above 200ms target (${avgDuration.toFixed(2)}ms)`);
      }
    });

    console.log('\n' + '='.repeat(50));
  }
}

async function runPerformanceValidation() {
  const validator = new PerformanceValidator();

  try {
    console.log('🚀 Starting Performance Validation...\n');

    // Wait a bit for server to start
    console.log('⏳ Waiting for server to start...');
    await new Promise(resolve => setTimeout(resolve, 3000));

    // Run all performance tests
    const apiLatencyResult = await validator.testAPILatency();
    const exchangeAPIResult = await validator.testExchangeAPIs();
    const wsPerformanceResult = await validator.testWebSocketPerformance();
    const rateLimitResult = await validator.testRateLimiting();
    const loadTestResult = await validator.testLoadConditions();

    // Generate final report
    validator.generateReport();

    // Summary
    console.log('\n🎯 FINAL RESULTS:');
    console.log(`API Latency: ${apiLatencyResult.status} (avg: ${apiLatencyResult.averageLatency?.toFixed(2)}ms)`);
    console.log(`Exchange APIs: ${exchangeAPIResult.status}`);
    console.log(`WebSocket Performance: ${wsPerformanceResult.status}`);
    console.log(`Rate Limiting: ${rateLimitResult.status}`);
    console.log(`Load Testing: ${loadTestResult.status}`);

    const allPassed = [
      apiLatencyResult.status,
      exchangeAPIResult.status,
      wsPerformanceResult.status,
      rateLimitResult.status,
      loadTestResult.status
    ].every(status => status === 'PASS');

    console.log(`\nOverall Status: ${allPassed ? '✅ PASS' : '❌ FAIL'}`);

    if (allPassed) {
      console.log('\n🎉 All performance requirements met!');
      console.log('✅ Latency measurements completed');
      console.log('✅ Exchange API integration validated');
      console.log('✅ API rate limiting tested');
      console.log('✅ WebSocket connection performance verified');
      console.log('✅ System load testing completed');
    }

    return allPassed;

  } catch (error) {
    console.error('❌ Performance validation failed:', error);
    return false;
  }
}

// Execute if run directly
if (require.main === module) {
  runPerformanceValidation()
    .then(success => {
      process.exit(success ? 0 : 1);
    })
    .catch(error => {
      console.error('Fatal error:', error);
      process.exit(1);
    });
}

module.exports = { PerformanceValidator };