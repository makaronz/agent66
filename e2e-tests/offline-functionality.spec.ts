import { test, expect } from '@playwright/test';

test.describe('Offline Functionality - Film Industry Time Tracking', () => {
  test.beforeEach(async ({ page }) => {
    // Enable service worker for PWA functionality
    await page.addInitScript(() => {
      window.addEventListener('load', () => {
        if ('serviceWorker' in navigator) {
          navigator.serviceWorker.register('/sw.js');
        }
      });
    });

    // Grant necessary permissions
    await page.context().grantPermissions(['geolocation', 'camera', 'storage']);
  });

  test('Complete offline timesheet workflow', async ({ page }) => {
    // Navigate to app and login while online
    await page.goto('http://localhost:3000/login');

    // Login and cache credentials
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.check('[data-testid="remember-me-checkbox"]');
    await page.click('[data-testid="login-button"]');

    // Wait for service worker activation
    await page.waitForLoadState('networkidle');

    // Verify service worker is active
    const swActive = await page.evaluate(() => {
      return navigator.serviceWorker.controller !== null;
    });
    expect(swActive).toBe(true);

    // Simulate offline mode
    await page.context().setOffline(true);

    // Verify offline indicator appears
    await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[data-testid="offline-indicator"]')).toContainText('Offline Mode');

    // Test offline navigation
    await page.click('[data-testid="timesheet-nav-link"]');
    await expect(page.locator('[data-testid="timesheet-page"]')).toBeVisible();

    // Create timesheet entry offline
    await page.click('[data-testid="new-entry-button"]');
    await expect(page.locator('[data-testid="timesheet-form"]')).toBeVisible();

    // Fill timesheet details
    await page.fill('[data-testid="date-picker"]', '2025-10-15');
    await page.fill('[data-testid="clock-in-time"]', '08:00');
    await page.fill('[data-testid="clock-out-time"]', '19:00'); // 11 hours total
    await page.fill('[data-testid="break-duration"]', '60');

    // Select project (should use cached data)
    await page.click('[data-testid="project-select"]');
    await expect(page.locator('[data-testid="project-options"]')).toBeVisible();
    await page.click('[data-testid="project-summer-blockbuster"]');

    await page.fill('[data-testid="location-input"]', 'Studio A - Main Stage');
    await page.fill('[data-testid="notes-textarea"]', 'Extended shooting due to weather delay. Scenes 23-25 completed.');

    // Submit offline
    await page.click('[data-testid="submit-timesheet-button"]');

    // Verify queued for sync notification
    await expect(page.locator('[data-testid="offline-queue-notification"]')).toBeVisible();
    await expect(page.locator('[data-testid="sync-queue-count"]')).toContainText('1');

    // Add equipment usage offline
    await page.click('[data-testid="add-equipment-button"]');
    await page.fill('[data-testid="equipment-input"]', 'RED Monstro 8K Camera');
    await page.click('[data-testid="add-equipment-confirm"]');

    // Verify queued count increases
    await expect(page.locator('[data-testid="sync-queue-count"]')).toContainText('2');

    // Test offline data persistence
    await page.reload();
    await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible();

    // Navigate back to timesheet
    await page.click('[data-testid="timesheet-nav-link"]');
    await expect(page.locator('[data-testid="offline-timesheet-list"]')).toBeVisible();

    // Verify entry is still queued
    await expect(page.locator('[data-testid="queued-entry"]')).toBeVisible();
    await expect(page.locator('[data-testid="sync-status"]')).toContainText('Queued');

    // Go back online
    await page.context().setOffline(false);

    // Verify sync process starts automatically
    await expect(page.locator('[data-testid="syncing-indicator"]')).toBeVisible();
    await expect(page.locator('[data-testid="sync-progress"]')).toBeVisible();

    // Wait for sync to complete
    await expect(page.locator('[data-testid="sync-complete-notification"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="sync-queue-count"]')).toContainText('0');

    // Verify data was synced correctly
    await page.reload();
    await expect(page.locator('[data-testid="timesheet-entry-2025-10-15"]')).toBeVisible();
    await expect(page.locator('[data-testid="entry-status"]')).toContainText('Pending');
  });

  test('Offline clock in/out functionality', async ({ page }) => {
    // Login and cache session
    await page.goto('http://localhost:3000/login');
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.check('[data-testid="remember-me-checkbox"]');
    await page.click('[data-testid="login-button"]');

    // Set geolocation
    await page.setGeolocation({ latitude: 34.052235, longitude: -118.243683 });

    // Go offline
    await page.context().setOffline(true);

    // Verify offline dashboard works
    await expect(page.locator('[data-testid="offline-dashboard"]')).toBeVisible();
    await expect(page.locator('[data-testid="clock-in-button"]')).toBeVisible();

    // Test offline clock in
    await page.click('[data-testid="clock-in-button"]');
    await expect(page.locator('[data-testid="offline-clock-in-modal"]')).toBeVisible();

    // Verify location services work offline (cached location)
    await expect(page.locator('[data-testid="location-display"]')).toContainText('Los Angeles, CA');
    await page.fill('[data-testid="location-verification"]', 'Studio A - Base Camp');
    await page.click('[data-testid="confirm-clock-in-button"]');

    // Verify offline timer starts
    await expect(page.locator('[data-testid="offline-timer"]')).toBeVisible();
    await expect(page.locator('[data-testid="timer-display"]')).toBeVisible();

    // Test break functionality offline
    await page.click('[data-testid="start-break-button"]');
    await expect(page.locator('[data-testid="offline-break-modal"]')).toBeVisible();
    await page.selectOption('[data-testid="break-type"]', 'LUNCH');
    await page.click('[data-testid="confirm-break-button"]');

    // Verify break timer works offline
    await expect(page.locator('[data-testid="offline-break-timer"]')).toBeVisible();

    // End break
    await page.click('[data-testid="end-break-button"]');

    // Test offline clock out
    await page.click('[data-testid="clock-out-button"]');
    await expect(page.locator('[data-testid="offline-clock-out-modal"]')).toBeVisible();
    await page.fill('[data-testid="clock-out-notes"]', 'Completed day ahead of schedule. All scenes shot successfully.');
    await page.click('[data-testid="confirm-clock-out-button"]');

    // Verify summary is generated offline
    await expect(page.locator('[data-testid="offline-daily-summary"]')).toBeVisible();
    await expect(page.locator('[data-testid="offline-total-hours"]')).toBeVisible();
    await expect(page.locator('[data-testid="offline-sync-queued"]')).toBeVisible();

    // Go back online
    await page.context().setOffline(false);

    // Verify sync process
    await expect(page.locator('[data-testid="syncing-indicator"]')).toBeVisible();
    await expect(page.locator('[data-testid="sync-complete-notification"]')).toBeVisible();

    // Verify timesheet was created correctly
    await page.click('[data-testid="timesheet-nav-link"]');
    await expect(page.locator('[data-testid="timesheet-entry-2025-10-15"]')).toBeVisible();
  });

  test('Offline data consistency across multiple devices', async ({ page, context }) => {
    // Create first device context
    const device1Context = await browser.newContext();
    const device1Page = await device1Context.newPage();

    // Create second device context
    const device2Context = await browser.newContext();
    const device2Page = await device2Context.newPage();

    // Login on first device online
    await device1Page.goto('http://localhost:3000/login');
    await device1Page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await device1Page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await device1Page.check('[data-testid="remember-me-checkbox"]');
    await device1Page.click('[data-testid="login-button"]');

    // Set first device offline
    await device1Context.setOffline(true);

    // Create timesheet entry on first device offline
    await device1Page.click('[data-testid="timesheet-nav-link"]');
    await device1Page.click('[data-testid="new-entry-button"]');
    await device1Page.fill('[data-testid="date-picker"]', '2025-10-15');
    await device1Page.fill('[data-testid="clock-in-time"]', '08:00');
    await device1Page.fill('[data-testid="clock-out-time"]', '17:00');
    await device1Page.fill('[data-testid="break-duration"]', '60');
    await device1Page.fill('[data-testid="location-input"]', 'Studio A');
    await device1Page.click('[data-testid="submit-timesheet-button"]');

    // Verify queued on first device
    await expect(device1Page.locator('[data-testid="sync-queue-count"]')).toContainText('1');

    // Login on second device (still online)
    await device2Page.goto('http://localhost:3000/login');
    await device2Page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await device2Page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await device2Page.check('[data-testid="remember-me-checkbox"]');
    await device2Page.click('[data-testid="login-button"]');

    // Create different timesheet entry on second device
    await device2Page.click('[data-testid="timesheet-nav-link"]');
    await device2Page.click('[data-testid="new-entry-button"]');
    await device2Page.fill('[data-testid="date-picker"]', '2025-10-14');
    await device2Page.fill('[data-testid="clock-in-time"]', '09:00');
    await device2Page.fill('[data-testid="clock-out-time"]', '18:00');
    await device2Page.fill('[data-testid="break-duration"]', '60');
    await device2Page.fill('[data-testid="location-input"]', 'Studio B');
    await device2Page.click('[data-testid="submit-timesheet-button"]');

    // Verify entry created immediately on second device
    await expect(device2Page.locator('[data-testid="timesheet-entry-2025-10-14"]')).toBeVisible();
    await expect(device2Page.locator('[data-testid="entry-status"]')).toContainText('Pending');

    // Bring first device online
    await device1Context.setOffline(false);

    // Verify sync on first device
    await expect(device1Page.locator('[data-testid="syncing-indicator"]')).toBeVisible();
    await expect(device1Page.locator('[data-testid="sync-complete-notification"]')).toBeVisible();

    // Verify both entries appear on both devices
    await device1Page.reload();
    await expect(device1Page.locator('[data-testid="timesheet-entry-2025-10-15"]')).toBeVisible();
    await expect(device1Page.locator('[data-testid="timesheet-entry-2025-10-14"]')).toBeVisible();

    await device2Page.reload();
    await expect(device2Page.locator('[data-testid="timesheet-entry-2025-10-15"]')).toBeVisible();
    await expect(device2Page.locator('[data-testid="timesheet-entry-2025-10-14"]')).toBeVisible();

    // Cleanup
    await device1Context.close();
    await device2Context.close();
  });

  test('Offline conflict resolution', async ({ page }) => {
    // Login and create initial entry
    await page.goto('http://localhost:3000/login');
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.click('[data-testid="login-button"]');

    // Create initial timesheet entry
    await page.click('[data-testid="timesheet-nav-link"]');
    await page.click('[data-testid="new-entry-button"]');
    await page.fill('[data-testid="date-picker"]', '2025-10-15');
    await page.fill('[data-testid="clock-in-time"]', '08:00');
    await page.fill('[data-testid="clock-out-time"]', '17:00');
    await page.fill('[data-testid="break-duration"]', '60');
    await page.fill('[data-testid="location-input"]', 'Studio A');
    await page.click('[data-testid="submit-timesheet-button"]');

    // Get entry ID
    await expect(page.locator('[data-testid="timesheet-entry-2025-10-15"]')).toBeVisible();
    const entryId = await page.locator('[data-testid="timesheet-entry-2025-10-15"]').getAttribute('data-entry-id');

    // Go offline and modify entry
    await page.context().setOffline(true);

    await page.click('[data-testid="edit-entry-button"]');
    await page.fill('[data-testid="clock-out-time"]', '19:00'); // Extended hours
    await page.fill('[data-testid="notes-textarea"]', 'Extended shooting due to weather delay. Modified offline.');
    await page.click('[data-testid="save-changes-button"]');

    // Verify modification is queued
    await expect(page.locator('[data-testid="conflict-queued-notification"]')).toBeVisible();

    // Simulate server-side modification (go online briefly)
    await page.context().setOffline(false);

    // Simulate supervisor modification through API (in real scenario)
    await page.evaluate((id) => {
      // Simulate server update
      fetch(`/api/time-entries/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          notes: 'Supervisor note: Scene requirements changed',
          clockOut: '18:00'
        })
      });
    }, entryId);

    // Go back offline and sync
    await page.context().setOffline(true);
    await page.context().setOffline(false);

    // Conflict detection should occur
    await expect(page.locator('[data-testid="conflict-detection-modal"]')).toBeVisible();

    // Verify conflict details
    await expect(page.locator('[data-testid="local-version"]')).toContainText('Extended shooting due to weather delay');
    await expect(page.locator('[data-testid="server-version"]')).toContainText('Supervisor note: Scene requirements changed');

    // Test conflict resolution options
    await expect(page.locator('[data-testid="use-local-version-button"]')).toBeVisible();
    await expect(page.locator('[data-testid="use-server-version-button"]')).toBeVisible();
    await expect(page.locator('[data-testid="merge-versions-button"]')).toBeVisible();

    // Choose to merge versions
    await page.click('[data-testid="merge-versions-button"]');

    // Verify merge interface
    await expect(page.locator('[data-testid="merge-interface"]')).toBeVisible();
    await expect(page.locator('[data-testid="merge-clock-out"]')).toHaveValue('19:00'); // Keep later time
    await page.fill('[data-testid="merge-notes"]', 'Extended shooting due to weather delay. Supervisor note: Scene requirements changed. Merged conflict resolution.');

    await page.click('[data-testid="confirm-merge-button"]');

    // Verify conflict resolved
    await expect(page.locator('[data-testid="conflict-resolved-notification"]')).toBeVisible();

    // Verify final state
    await page.reload();
    await page.click('[data-testid="timesheet-nav-link"]');
    await expect(page.locator('[data-testid="timesheet-entry-2025-10-15"]')).toBeVisible();
    await expect(page.locator('[data-testid="entry-notes"]')).toContainText('Merged conflict resolution');
  });

  test('Offline storage limits and cleanup', async ({ page }) => {
    // Login and go offline
    await page.goto('http://localhost:3000/login');
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.click('[data-testid="login-button"]');

    await page.context().setOffline(true);

    // Fill offline storage with many entries
    for (let i = 0; i < 50; i++) {
      await page.click('[data-testid="new-entry-button"]');
      await page.fill('[data-testid="date-picker"]', `2025-10-${String(i + 1).padStart(2, '0')}`);
      await page.fill('[data-testid="clock-in-time"]', '08:00');
      await page.fill('[data-testid="clock-out-time"]', '17:00');
      await page.fill('[data-testid="break-duration"]', '60');
      await page.fill('[data-testid="location-input"]', `Studio ${i % 3 + 1}`);
      await page.click('[data-testid="submit-timesheet-button']);

      // Add some delay to simulate realistic usage
      await page.waitForTimeout(100);
    }

    // Check storage usage
    const storageUsage = await page.evaluate(() => {
      if ('storage' in navigator && 'estimate' in navigator.storage) {
        return navigator.storage.estimate();
      }
      return null;
    });

    if (storageUsage) {
      expect(storageUsage.usage).toBeGreaterThan(0);
      expect(storageUsage.quota).toBeGreaterThan(storageUsage.usage);
    }

    // Verify storage management interface
    await page.click('[data-testid="user-menu"]');
    await page.click('[data-testid="offline-settings-button"]');

    await expect(page.locator('[data-testid="offline-storage-info"]')).toBeVisible();
    await expect(page.locator('[data-testid="queued-items-count"]')).toContainText('50');

    // Test storage cleanup
    await page.click('[data-testid="cleanup-storage-button"]');
    await expect(page.locator('[data-testid="cleanup-modal"]')).toBeVisible();

    // Select old entries for cleanup
    await page.check('[data-testid="cleanup-older-than-30-days"]');
    await page.check('[data-testid="cleanup-synced-entries"]');
    await page.click('[data-testid="perform-cleanup-button"]');

    // Verify cleanup results
    await expect(page.locator('[data-testid="cleanup-complete-notification"]')).toBeVisible();
    await expect(page.locator('[data-testid="storage-freed"]')).toBeVisible();

    // Go online and sync remaining entries
    await page.context().setOffline(false);

    // Verify sync process handles remaining entries
    await expect(page.locator('[data-testid="syncing-indicator"]')).toBeVisible();
    await expect(page.locator('[data-testid="sync-complete-notification"]')).toBeVisible({ timeout: 30000 });

    // Verify all entries were synced
    await page.click('[data-testid="timesheet-nav-link"]');
    const entryCount = await page.locator('[data-testid="timesheet-entry"]').count();
    expect(entryCount).toBeGreaterThan(40); // Most entries should be synced
  });

  test('Offline security and data protection', async ({ page }) => {
    // Login with biometric authentication enabled
    await page.goto('http://localhost:3000/login');
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.check('[data-testid="enable-biometric-checkbox"]');
    await page.check('[data-testid="enable-offline-security-checkbox"]');
    await page.click('[data-testid="login-button"]');

    // Set up biometric authentication (simulated)
    await expect(page.locator('[data-testid="biometric-setup-modal"]')).toBeVisible();
    await page.click('[data-testid="enable-biometric-button"]');

    // Go offline and test biometric login
    await page.context().setOffline(true);

    // Test session timeout
    await page.reload();
    await expect(page.locator('[data-testid="biometric-login-prompt"]')).toBeVisible();

    // Simulate successful biometric authentication
    await page.click('[data-testid="simulate-biometric-success"]');

    // Verify secure access
    await expect(page.locator('[data-testid="dashboard-header"]')).toBeVisible();
    await expect(page.locator('[data-testid="security-indicator"]')).toContainText('Secure');

    // Test data encryption
    await page.click('[data-testid="timesheet-nav-link"]');
    await page.click('[data-testid="new-entry-button"]');
    await page.fill('[data-testid="date-picker"]', '2025-10-15');
    await page.fill('[data-testid="clock-in-time"]', '08:00');
    await page.fill('[data-testid="clock-out-time"]', '17:00');
    await page.fill('[data-testid="location-input"]', 'Studio A');
    await page.fill('[data-testid="notes-textarea"]', 'Sensitive production information');

    // Verify encryption indicator
    await expect(page.locator('[data-testid="encryption-indicator"]')).toBeVisible();
    await expect(page.locator('[data-testid="data-encrypted"]')).toContainText('Encrypted');

    await page.click('[data-testid="submit-timesheet-button"]');

    // Test secure storage verification
    await page.click('[data-testid="user-menu"]');
    await page.click('[data-testid="security-settings-button"]');

    await expect(page.locator('[data-testid="security-status"]')).toBeVisible();
    await expect(page.locator('[data-testid="encryption-status"]')).toContainText('Active');
    await expect(page.locator('[data-testid="biometric-status"]')).toContainText('Enabled');

    // Verify data integrity
    const dataIntegrityCheck = await page.evaluate(() => {
      // Check if stored data is encrypted
      const storedData = localStorage.getItem('offlineQueue');
      if (storedData) {
        try {
          JSON.parse(storedData);
          return false; // Not encrypted
        } catch (e) {
          return true; // Encrypted (not parseable as plain JSON)
        }
      }
      return false;
    });

    expect(dataIntegrityCheck).toBe(true);

    // Go online and verify secure sync
    await page.context().setOffline(false);

    await expect(page.locator('[data-testid="secure-sync-indicator"]')).toBeVisible();
    await expect(page.locator('[data-testid="sync-complete-notification"]')).toBeVisible();
  });
});