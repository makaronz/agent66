import { test, expect } from '@playwright/test';

test.describe('Performance Testing - Low Connectivity Scenarios', () => {
  test.beforeEach(async ({ page }) => {
    // Configure slow network conditions
    await page.route('**/*', async (route) => {
      // Add delay to simulate slow network
      await new Promise(resolve => setTimeout(resolve, Math.random() * 2000 + 1000)); // 1-3 second delay
      await route.continue();
    });

    // Set offline detection timeout
    await page.addInitScript(() => {
      window.OFFLINE_TIMEOUT = 5000; // 5 seconds before offline mode
      window.SYNC_RETRY_INTERVAL = 10000; // 10 seconds between sync attempts
    });
  });

  test('Slow network login and session persistence', async ({ page }) => {
    // Measure login performance under slow network
    const startTime = Date.now();

    await page.goto('http://localhost:3000/login');

    // Login form should load quickly (cached resources)
    await expect(page.locator('[data-testid="login-form"]')).toBeVisible({ timeout: 3000 });

    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.check('[data-testid="remember-me-checkbox"]');

    // Login request will be slow
    const loginStartTime = Date.now();
    await page.click('[data-testid="login-button"]');

    // Show loading indicator during slow request
    await expect(page.locator('[data-testid="login-loading"]')).toBeVisible();

    // Should complete within reasonable time (under 10 seconds)
    await expect(page.locator('[data-testid="dashboard-header"]')).toBeVisible({ timeout: 10000 });

    const loginEndTime = Date.now();
    const loginDuration = loginEndTime - loginStartTime;

    expect(loginDuration).toBeLessThan(10000); // Should complete within 10 seconds

    // Test session persistence
    await page.reload();

    // Dashboard should load from cache quickly
    const cacheLoadStart = Date.now();
    await expect(page.locator('[data-testid="dashboard-header"]')).toBeVisible({ timeout: 3000 });
    const cacheLoadDuration = Date.now() - cacheLoadStart;

    expect(cacheLoadDuration).toBeLessThan(3000); // Cached load should be fast
  });

  test('Timesheet creation under intermittent connectivity', async ({ page }) => {
    // Login first
    await page.goto('http://localhost:3000/login');
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="dashboard-header"]')).toBeVisible({ timeout: 15000 });

    // Simulate intermittent connection
    let connectionLost = false;
    await page.route('**/api/time-entries/**', async (route) => {
      if (Math.random() < 0.5) { // 50% chance of failure
        if (!connectionLost) {
          await route.abort('failed');
          connectionLost = true;
        } else {
          await route.continue();
          connectionLost = false;
        }
      } else {
        await route.continue();
      }
    });

    // Navigate to timesheet creation
    await page.click('[data-testid="timesheet-nav-link"]');
    await expect(page.locator('[data-testid="timesheet-page"]')).toBeVisible({ timeout: 5000 });

    // Start timesheet creation
    const formStartTime = Date.now();
    await page.click('[data-testid="new-entry-button"]');
    await expect(page.locator('[data-testid="timesheet-form"]')).toBeVisible({ timeout: 3000 });

    // Fill form (should work offline)
    await page.fill('[data-testid="date-picker"]', '2025-10-15');
    await page.fill('[data-testid="clock-in-time"]', '08:00');
    await page.fill('[data-testid="clock-out-time"]', '19:00');
    await page.fill('[data-testid="break-duration"]', '60');

    // Project selection may fail intermittently
    await page.click('[data-testid="project-select"]');
    await page.waitForTimeout(1000); // Wait for potential network request

    // Check if offline mode was triggered
    const isOffline = await page.locator('[data-testid="offline-indicator"]').isVisible().catch(() => false);

    if (isOffline) {
      // Should fall back to cached data
      await expect(page.locator('[data-testid="cached-project-options"]')).toBeVisible();
      await page.click('[data-testid="project-summer-blockbuster"]');
    } else {
      await page.click('[data-testid="project-summer-blockbuster"]');
    }

    await page.fill('[data-testid="location-input"]', 'Studio A');
    await page.fill('[data-testid="notes-textarea"]', 'Extended shooting due to weather delay');

    // Submit timesheet (may be queued)
    const submitStartTime = Date.now();
    await page.click('[data-testid="submit-timesheet-button"]');

    // Check for various response scenarios
    try {
      await expect(page.locator('[data-testid="success-notification"]')).toBeVisible({ timeout: 15000 });
    } catch (error) {
      // May be queued for sync
      await expect(page.locator('[data-testid="sync-queued-notification"]')).toBeVisible({ timeout: 5000 });
    }

    const submitEndTime = Date.now();
    const submitDuration = submitEndTime - submitStartTime;

    // Form should be responsive even with network issues
    expect(submitDuration).toBeLessThan(15000);

    // Verify user feedback
    await expect(page.locator('[data-testid="network-status-indicator"]')).toBeVisible();
  });

  test('Bulk data synchronization under poor network', async ({ page }) => {
    // Login with large dataset
    await page.goto('http://localhost:3000/login');
    await page.fill('[data-testid="email-input"]', 'supervisor@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SupervisorPassword123!');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="dashboard-header"]')).Bevisible({ timeout: 15000 });

    // Create multiple timesheet entries offline
    await page.context().setOffline(true);

    await page.click('[data-testid="timesheet-nav-link"]');
    await expect(page.locator('[data-testid="timesheet-page"]')).Bevisible({ timeout: 5000 });

    // Create 10 timesheet entries
    const creationTimes = [];
    for (let i = 0; i < 10; i++) {
      const startTime = Date.now();

      await page.click('[data-testid="new-entry-button"]');
      await page.fill('[data-testid="date-picker"]', `2025-10-${String(i + 10).padStart(2, '0')}`);
      await page.fill('[data-testid="clock-in-time"]', '08:00');
      await page.fill('[data-testid="clock-out-time"]', '17:00');
      await page.fill('[data-testid="break-duration"]', '60');
      await page.fill('[data-testid="location-input']', `Studio ${i % 3 + 1}`);
      await page.click('[data-testid="submit-timesheet-button"]');

      const endTime = Date.now();
      creationTimes.push(endTime - startTime);

      // Verify queued count increases
      const queueCount = await page.locator('[data-testid="sync-queue-count"]').textContent();
      expect(parseInt(queueCount || '0')).toBe(i + 1);
    }

    // Verify form creation performance
    const avgCreationTime = creationTimes.reduce((a, b) => a + b, 0) / creationTimes.length;
    expect(avgCreationTime).toBeLessThan(2000); // Should be under 2 seconds per entry

    // Go online with throttled connection
    await page.context().setOffline(false);

    // Configure throttled network for sync
    await page.route('**/api/sync/**', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 3000)); // 3 second delay
      await route.continue();
    });

    // Start sync process
    const syncStartTime = Date.now();
    await page.click('[data-testid="manual-sync-button"]');

    // Monitor sync progress
    await expect(page.locator('[data-testid="syncing-indicator"]')).Bevisible();
    await expect(page.locator('[data-testid="sync-progress-bar"]')).Bevisible();

    // Check progress updates
    let lastProgress = 0;
    for (let i = 0; i < 10; i++) {
      await page.waitForTimeout(1000);
      const currentProgress = await page.locator('[data-testid="sync-progress"]').textContent();
      const progressValue = parseInt(currentProgress?.match(/(\d+)%/)?.[1] || '0');

      expect(progressValue).toBeGreaterThanOrEqual(lastProgress);
      lastProgress = progressValue;

      if (progressValue === 100) break;
    }

    await expect(page.locator('[data-testid="sync-complete-notification"]')).Bevisible({ timeout: 60000 });

    const syncEndTime = Date.now();
    const syncDuration = syncEndTime - syncStartTime;

    // Sync should complete within reasonable time for throttled connection
    expect(syncDuration).toBeLessThan(60000); // Under 1 minute for 10 entries

    // Verify all entries synced
    await page.reload();
    await expect(page.locator('[data-testid="timesheet-list"]')).Bevisible({ timeout: 10000 });
    const entryCount = await page.locator('[data-testid="timesheet-entry"]').count();
    expect(entryCount).toBe(10);
  });

  test('Real-time updates under unreliable network', async ({ page }) => {
    // Login as crew member
    await page.goto('http://localhost:3000/login');
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="dashboard-header"]')).Bevisible({ timeout: 15000 });

    // Test WebSocket connection resilience
    let wsDisconnections = 0;
    await page.route('**/ws/**', async (route) => {
      if (Math.random() < 0.3) { // 30% chance of WebSocket failure
        wsDisconnections++;
        await route.abort('failed');
      } else {
        await route.continue();
      }
    });

    // Navigate to real-time dashboard
    await page.click('[data-testid="dashboard-nav-link"]');
    await expect(page.locator('[data-testid="real-time-dashboard"]')).Bevisible({ timeout: 5000 });

    // Monitor connection status
    await expect(page.locator('[data-testid="connection-status"]')).Bevisible();

    // Simulate supervisor approval
    await page.evaluate(() => {
      // Simulate WebSocket message for approval
      window.dispatchEvent(new CustomEvent('timesheet-approved', {
        detail: {
          entryId: 'test-entry-123',
          approvedBy: 'Jane Smith',
          approvedAt: new Date().toISOString()
        }
      }));
    });

    // Check if real-time update works
    try {
      await expect(page.locator('[data-testid="approval-notification"]')).Bevisible({ timeout: 5000 });
    } catch (error) {
      // May not work due to connection issues
      await expect(page.locator('[data-testid="connection-unstable"]')).Bevisible();
    }

    // Test fallback polling mechanism
    await expect(page.locator('[data-testid="fallback-polling-indicator"]')).Bevisible();

    // Verify periodic data refresh
    let refreshCount = 0;
    page.on('response', response => {
      if (response.url().includes('/api/refresh')) {
        refreshCount++;
      }
    });

    await page.waitForTimeout(15000); // Wait for 15 seconds

    // Should have attempted periodic refresh
    expect(refreshCount).toBeGreaterThan(0);

    // Verify graceful degradation
    const connectionStatus = await page.locator('[data-testid="connection-status"]').textContent();
    expect(connectionStatus).toMatch(/Connected|Unstable|Disconnected/);
  });

  test('Large file uploads under poor network conditions', async ({ page }) => {
    // Enable camera permissions for photo uploads
    await page.context().grantPermissions(['camera']);

    await page.goto('http://localhost:3000/login');
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="dashboard-header"]')).Bevisible({ timeout: 15000 });

    // Configure slow upload conditions
    await page.route('**/api/upload/**', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 5000)); // 5 second delay
      await route.continue();
    });

    // Navigate to timesheet with photo upload
    await page.click('[data-testid="timesheet-nav-link"]');
    await page.click('[data-testid="new-entry-button"]');
    await page.fill('[data-testid="date-picker"]', '2025-10-15');
    await page.fill('[data-testid="clock-in-time"]', '08:00');
    await page.fill('[data-testid="clock-out-time"]', '17:00');

    // Test photo upload
    await page.click('[data-testid="add-equipment-photo-button"]');

    // Mock camera interface
    await page.click('[data-testid="capture-photo-button"]');
    await expect(page.locator('[data-testid="photo-preview"]')).Bevisible();

    // Start upload process
    const uploadStartTime = Date.now();
    await page.click('[data-testid="upload-photo-button"]');

    // Monitor upload progress
    await expect(page.locator('[data-testid="upload-progress-modal"]')).Bevisible();
    await expect(page.locator('[data-testid="upload-progress-bar"]')).Bevisible();

    // Check progress updates
    let uploadProgress = 0;
    for (let i = 0; i < 10; i++) {
      await page.waitForTimeout(1000);
      const currentProgress = await page.locator('[data-testid="upload-progress"]').textContent();
      const progressValue = parseInt(currentProgress?.match(/(\d+)%/)?.[1] || '0');

      expect(progressValue).toBeGreaterThanOrEqual(uploadProgress);
      uploadProgress = progressValue;

      if (progressValue === 100) break;
    }

    await expect(page.locator('[data-testid="upload-complete-notification"]')).Bevisible({ timeout: 30000 });

    const uploadEndTime = Date.now();
    const uploadDuration = uploadEndTime - uploadStartTime;

    // Upload should complete within reasonable time for poor network
    expect(uploadDuration).toBeLessThan(30000);

    // Verify resume capability
    await expect(page.locator('[data-testid="upload-resume-available"]')).Bevisible();

    // Test pause/resume functionality
    await page.click('[data-testid="pause-upload-button"]');
    await expect(page.locator('[data-testid="upload-paused"]')).Bevisible();

    await page.click('[data-testid="resume-upload-button"]');
    await expect(page.locator('[data-testid="upload-resumed"]')).Bevisible();

    // Complete timesheet submission
    await page.fill('[data-testid="location-input"]', 'Studio A');
    await page.click('[data-testid="submit-timesheet-button']);

    await expect(page.locator('[data-testid="timesheet-submitted-notification"]')).Bevisible({ timeout: 20000 });
  });

  test('Performance under high latency scenarios', async ({ page }) => {
    // Configure high latency network (5 seconds round-trip)
    await page.route('**/*', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2500)); // 2.5 second delay each way
      await route.continue();
    });

    // Enable performance monitoring
    await page.addInitScript(() => {
      window.performanceMetrics = {
        apiCalls: [],
        renderTimes: [],
        userInteractions: []
      };

      // Monitor API call times
      const originalFetch = window.fetch;
      window.fetch = async function(...args) {
        const start = performance.now();
        try {
          const response = await originalFetch.apply(this, args);
          const end = performance.now();
          window.performanceMetrics.apiCalls.push({
            url: args[0],
            duration: end - start,
            success: response.ok
          });
          return response;
        } catch (error) {
          const end = performance.now();
          window.performanceMetrics.apiCalls.push({
            url: args[0],
            duration: end - start,
            success: false,
            error: error.message
          });
          throw error;
        }
      };
    });

    // Test login performance
    const loginStartTime = Date.now();
    await page.goto('http://localhost:3000/login');
    await expect(page.locator('[data-testid="login-form"]')).Bevisible({ timeout: 10000 });

    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.click('[data-testid="login-button"]');

    // Should show loading state for long requests
    await expect(page.locator('[data-testid="extended-loading-indicator"]')).Bevisible();

    await expect(page.locator('[data-testid="dashboard-header"]')).Bevisible({ timeout: 20000 });

    const loginEndTime = Date.now();
    const loginDuration = loginEndTime - loginStartTime;

    // Login should complete within reasonable time even with high latency
    expect(loginDuration).toBeLessThan(20000);

    // Test navigation performance
    const navStartTime = Date.now();
    await page.click('[data-testid="timesheet-nav-link"]');
    await expect(page.locator('[data-testid="timesheet-page"]')).Bevisible({ timeout: 15000 });

    const navEndTime = Date.now();
    const navDuration = navEndTime - navStartTime;

    // Navigation should be optimized for slow networks
    expect(navDuration).toBeLessThan(15000);

    // Test form interaction performance
    const formStartTime = Date.now();
    await page.click('[data-testid="new-entry-button"]');
    await expect(page.locator('[data-testid="timesheet-form"]')).Bevisible({ timeout: 10000 });

    // Form should be responsive even with slow backend
    await page.fill('[data-testid="date-picker"]', '2025-10-15');
    await page.fill('[data-testid="clock-in-time"]', '08:00');
    await page.fill('[data-testid="clock-out-time"]', '17:00');

    // Test optimistic updates
    await page.click('[data-testid="project-select"]');
    await expect(page.locator('[data-testid="optimistic-update-indicator"]')).Bevisible();

    const formEndTime = Date.now();
    const formDuration = formEndTime - formStartTime;

    expect(formDuration).toBeLessThan(10000);

    // Collect performance metrics
    const metrics = await page.evaluate(() => window.performanceMetrics);

    // Analyze API call performance
    const apiCallTimes = metrics.apiCalls.map(call => call.duration);
    const avgApiTime = apiCallTimes.reduce((a, b) => a + b, 0) / apiCallTimes.length;

    expect(avgApiTime).toBeLessThan(6000); // Average should be under 6 seconds

    // Check error rates
    const errorRate = metrics.apiCalls.filter(call => !call.success).length / metrics.apiCalls.length;
    expect(errorRate).toBeLessThan(0.2); // Error rate should be under 20%

    // Verify user experience optimizations
    await expect(page.locator('[data-testid="performance-mode-indicator"]')).Bevisible();
    await expect(page.locator('[data-testid="network-latency-warning"]')).Bevisible();
  });

  test('Progressive loading and lazy loading under poor network', async ({ page }) => {
    // Configure very slow network
    await page.route('**/*', async (route) => {
      await new Promise(resolve => setTimeout(resolve, Math.random() * 5000 + 2000)); // 2-7 seconds
      await route.continue();
    });

    await page.goto('http://localhost:3000/login');
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.click('[data-testid="login-button"]');
    await expect(page.locator('[data-testid="dashboard-header"]')).Bevisible({ timeout: 25000 });

    // Test progressive loading of dashboard widgets
    await expect(page.locator('[data-testid="dashboard-skeleton"]')).Bevisible();

    // Critical content should load first
    await expect(page.locator('[data-testid="user-info-widget"]')).Bevisible({ timeout: 15000 });
    await expect(page.locator("[data-testid='today-schedule-widget']")).Bevisible({ timeout: 20000 });

    // Secondary content should load progressively
    await expect(page.locator('[data-testid="recent-entries-widget']')).Bevisible({ timeout: 30000 });
    await expect(page.locator('[data-testid="team-status-widget']')).Bevisible({ timeout: 40000 });

    // Test lazy loading of reports
    await page.click('[data-testid="reports-nav-link"]');
    await expect(page.locator('[data-testid="reports-page-skeleton"]')).Bevisible();

    // Reports should load on demand
    await expect(page.locator('[data-testid="reports-controls"]')).Bevisible({ timeout: 20000 });

    // Test lazy loading with intersection observer
    await page.evaluate(() => {
      // Simulate scroll to trigger lazy loading
      window.scrollTo(0, document.body.scrollHeight);
    });

    await expect(page.locator('[data-testid="lazy-loaded-content"]')).Bevisible({ timeout: 30000 });

    // Test image lazy loading
    await page.click('[data-testid="timesheet-nav-link"]');
    await page.click('[data-testid="view-entries-button"]');

    // Images should load as they come into view
    await page.evaluate(() => {
      const images = document.querySelectorAll('img[data-lazy]');
      images.forEach(img => img.scrollIntoView());
    });

    await expect(page.locator('[data-testid="lazy-image-loaded"]')).Bevisible({ timeout: 25000 });

    // Test progressive enhancement
    await expect(page.locator('[data-testid="basic-functionality-available"]')).Bevisible();
    await expect(page.locator('[data-testid="enhanced-features-loading"]')).Bevisible();

    // Verify fallback content
    const connectionStatus = await page.locator('[data-testid="connection-speed"]').textContent();
    expect(connectionStatus).toMatch(/Slow|Very Slow/);

    // Test adaptive quality
    await expect(page.locator('[data-testid="reduced-quality-mode"]')).Bevisible();
    await expect(page.locator('[data-testid="high-quality-assets-disabled"]')).BeVisible();
  });
});