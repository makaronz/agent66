import { test, expect } from '@playwright/test';

test.describe('Film Industry Time Tracking - Timesheet Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to application
    await page.goto('http://localhost:3000');

    // Handle any welcome modals or notifications
    try {
      await page.waitForSelector('[data-testid="welcome-modal"]', { timeout: 5000 });
      await page.click('[data-testid="welcome-modal"] button[data-testid="close-button"]');
    } catch (error) {
      // No modal present, continue
    }
  });

  test('Complete timesheet entry workflow from login to submission', async ({ page }) => {
    // Step 1: Login as crew member
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.click('[data-testid="login-button"]');

    // Verify successful login
    await expect(page.locator('[data-testid="dashboard-header"]')).toBeVisible();
    await expect(page.locator('[data-testid="user-name"]')).toContainText('John Doe');

    // Step 2: Navigate to timesheet entry
    await page.click('[data-testid="timesheet-nav-link"]');
    await expect(page.locator('[data-testid="timesheet-page"]')).toBeVisible();

    // Step 3: Create new timesheet entry
    await page.click('[data-testid="new-entry-button"]');
    await expect(page.locator('[data-testid="timesheet-form"]')).toBeVisible();

    // Step 4: Fill timesheet details
    await page.fill('[data-testid="date-picker"]', '2025-10-15');
    await page.fill('[data-testid="clock-in-time"]', '08:00');
    await page.fill('[data-testid="clock-out-time"]', '19:00');
    await page.fill('[data-testid="break-duration"]', '60');

    // Select project
    await page.click('[data-testid="project-select"]');
    await page.click('[data-testid="project-summer-blockbuster"]');

    // Select department
    await page.click('[data-testid="department-select"]');
    await page.click('[data-testid="department-camera"]');

    // Fill location
    await page.fill('[data-testid="location-input"]', 'Studio A - Main Stage');

    // Add notes
    await page.fill('[data-testid="notes-textarea"]', 'Extended shooting due to weather delay - Scene 23-25 completed');

    // Step 5: Add equipment used
    await page.click('[data-testid="add-equipment-button"]');
    await page.fill('[data-testid="equipment-input"]', 'Camera A1 - RED Monstro 8K');
    await page.click('[data-testid="add-equipment-confirm"]');

    // Step 6: Add scenes shot
    await page.click('[data-testid="add-scene-button"]');
    await page.fill('[data-testid="scene-input"]', 'Scene 23 - Exterior battle sequence');
    await page.click('[data-testid="add-scene-confirm"]');

    await page.click('[data-testid="add-scene-button"]');
    await page.fill('[data-testid="scene-input"]', 'Scene 24 - Interior dialogue');
    await page.click('[data-testid="add-scene-confirm"]');

    // Step 7: Review calculated hours
    await expect(page.locator('[data-testid="regular-hours"]')).toContainText('8.0');
    await expect(page.locator('[data-testid="overtime-hours"]')).toContainText('2.0');
    await expect(page.locator('[data-testid="total-hours"]')).toContainText('10.0');

    // Step 8: Submit timesheet
    await page.click('[data-testid="submit-timesheet-button"]');

    // Verify submission success
    await expect(page.locator('[data-testid="success-notification"]')).toBeVisible();
    await expect(page.locator('[data-testid="success-notification"]')).toContainText('Timesheet submitted successfully');

    // Step 9: Verify timesheet appears in list
    await expect(page.locator('[data-testid="timesheet-list"]')).toBeVisible();
    await expect(page.locator('[data-testid="timesheet-entry-2025-10-15"]')).toBeVisible();
    await expect(page.locator('[data-testid="entry-status-pending"]')).toBeVisible();
  });

  test('Supervisor approval workflow', async ({ page }) => {
    // Login as supervisor
    await page.fill('[data-testid="email-input"]', 'jane.smith@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SupervisorPassword123!');
    await page.click('[data-testid="login-button"]');

    // Navigate to supervisor dashboard
    await page.click('[data-testid="supervisor-nav-link"]');
    await expect(page.locator('[data-testid="supervisor-dashboard"]')).toBeVisible();

    // Navigate to pending approvals
    await page.click('[data-testid="pending-approvals-tab"]');
    await expect(page.locator('[data-testid="pending-timesheets"]')).toBeVisible();

    // Click on first pending timesheet
    await page.click('[data-testid="timesheet-item-0"]');
    await expect(page.locator('[data-testid="timesheet-details"]')).toBeVisible();

    // Review timesheet details
    await expect(page.locator('[data-testid="crew-member-name"]')).toContainText('John Doe');
    await expect(page.locator('[data-testid="regular-hours"]')).toContainText('8.0');
    await expect(page.locator('[data-testid="overtime-hours"]')).toContainText('2.0');
    await expect(page.locator('[data-testid="total-cost"]')).toBeVisible();

    // Request clarification (simulate finding issue)
    await page.click('[data-testid="request-clarification-button"]');
    await page.fill('[data-testid="clarification-text"]', 'Please specify which weather conditions caused the delay and provide production manager approval for overtime.');
    await page.click('[data-testid="send-clarification-button"]');

    // Verify clarification sent
    await expect(page.locator('[data-testid="clarification-sent-notification"]')).toBeVisible();

    // Switch to crew member account
    await page.click('[data-testid="user-menu"]');
    await page.click('[data-testid="logout-button"]');

    // Login as crew member
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.click('[data-testid="login-button"]');

    // Navigate to timesheet
    await page.click('[data-testid="timesheet-nav-link"]');

    // Check for clarification notification
    await expect(page.locator('[data-testid="clarification-notification"]')).toBeVisible();
    await page.click('[data-testid="clarification-notification"]');

    // Provide additional information
    await page.fill('[data-testid="additional-notes"]', 'Heavy rain caused 4-hour delay. Production manager Sarah Johnson authorized overtime to meet daily shooting targets. Weather report attached.');
    await page.click('[data-testid="submit-clarification-button"]');

    // Login back as supervisor
    await page.click('[data-testid="user-menu"]');
    await page.click('[data-testid="logout-button"]');

    await page.fill('[data-testid="email-input"]', 'jane.smith@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SupervisorPassword123!');
    await page.click('[data-testid="login-button"]');

    await page.click('[data-testid="supervisor-nav-link"]');
    await page.click('[data-testid="pending-approvals-tab"]');
    await page.click('[data-testid="timesheet-item-0"]');

    // Approve timesheet
    await expect(page.locator('[data-testid="clarification-response"]')).toContainText('Heavy rain caused 4-hour delay');
    await page.click('[data-testid="approve-timesheet-button"]');
    await page.fill('[data-testid="approval-notes"]', 'Approved - weather delay verified with production manager. Overtime authorized.');
    await page.check('[data-testid="approve-overtime-checkbox"]');
    await page.click('[data-testid="confirm-approval-button"]');

    // Verify approval
    await expect(page.locator('[data-testid="approval-success-notification"]')).toBeVisible();
    await expect(page.locator('[data-testid="entry-status-approved"]')).toBeVisible();
  });

  test('Bulk timesheet approval workflow', async ({ page }) => {
    // Login as supervisor
    await page.fill('[data-testid="email-input"]', 'jane.smith@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SupervisorPassword123!');
    await page.click('[data-testid="login-button"]');

    // Navigate to supervisor dashboard
    await page.click('[data-testid="supervisor-nav-link"]');
    await expect(page.locator('[data-testid="supervisor-dashboard"]')).toBeVisible();

    // Navigate to pending approvals
    await page.click('[data-testid="pending-approvals-tab"]');
    await expect(page.locator('[data-testid="pending-timesheets"]')).toBeVisible();

    // Select multiple timesheets for bulk approval
    await page.check('[data-testid="select-timesheet-0"]');
    await page.check('[data-testid="select-timesheet-1"]');
    await page.check('[data-testid="select-timesheet-2"]');

    // Verify selection count
    await expect(page.locator('[data-testid="selected-count"]')).toContainText('3');

    // Click bulk approve
    await page.click('[data-testid="bulk-approve-button"]');
    await expect(page.locator('[data-testid="bulk-approval-modal"]')).toBeVisible();

    // Add bulk approval notes
    await page.fill('[data-testid="bulk-approval-notes"]', 'Weekly timesheet approval - all entries verified against production schedules. Standard hours approved.');

    // Confirm bulk approval
    await page.click('[data-testid="confirm-bulk-approval-button"]');

    // Verify bulk approval success
    await expect(page.locator('[data-testid="bulk-approval-success"]')).toBeVisible();
    await expect(page.locator('[data-testid="bulk-approval-success"]')).toContainText('3 timesheets approved');

    // Verify timesheets moved to approved section
    await page.click('[data-testid="approved-tab"]');
    await expect(page.locator('[data-testid="approved-timesheets"]')).toBeVisible();
    await expect(page.locator('[data-testid="approved-timesheet-item"]')).toHaveCount(3);
  });

  test('Timesheet dispute resolution workflow', async ({ page }) => {
    // Login as crew member with rejected timesheet
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.click('[data-testid="login-button"]');

    // Navigate to timesheet
    await page.click('[data-testid="timesheet-nav-link"]');

    // Find rejected timesheet
    await expect(page.locator('[data-testid="entry-status-rejected"]')).toBeVisible();
    await page.click('[data-testid="rejected-timesheet"]');

    // View rejection details
    await expect(page.locator('[data-testid="rejection-reason"]')).toContainText('Overtime not authorized');
    await expect(page.locator('[data-testid="rejection-notes"]')).toBeVisible();

    // File dispute
    await page.click('[data-testid="file-dispute-button"]');
    await expect(page.locator('[data-testid="dispute-form"]')).toBeVisible();

    // Fill dispute details
    await page.fill('[data-testid="dispute-reason"]', 'Overtime requested by production manager');
    await page.fill('[data-testid="dispute-description"]', 'Production manager John Smith explicitly requested extended hours for scene reshoot due to weather issues. Sarah Johnson (Lighting) can confirm. Weather delay report attached.');

    // Add evidence
    await page.click('[data-testid="add-evidence-button"]');
    await page.fill('[data-testid="evidence-description"]', 'Production schedule update');
    await page.click('[data-testid="add-evidence-confirm"]');

    await page.click('[data-testid="add-evidence-button"]');
    await page.fill('[data-testid="evidence-description"]', 'Weather delay report');
    await page.click('[data-testid="add-evidence-confirm"]');

    // Submit dispute
    await page.click('[data-testid="submit-dispute-button"]');

    // Verify dispute submitted
    await expect(page.locator('[data-testid="dispute-submitted-notification"]')).toBeVisible();
    await expect(page.locator('[data-testid="dispute-status-under-review"]')).toBeVisible();

    // Login as admin to review dispute
    await page.click('[data-testid="user-menu"]');
    await page.click('[data-testid="logout-button"]');

    await page.fill('[data-testid="email-input"]', 'admin@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'AdminPassword123!');
    await page.click('[data-testid="login-button"]');

    // Navigate to admin dashboard
    await page.click('[data-testid="admin-nav-link"]');
    await page.click('[data-testid="disputes-tab"]');

    // Review dispute
    await expect(page.locator('[data-testid="dispute-item"]')).toBeVisible();
    await page.click('[data-testid="dispute-item"]');

    // Review dispute details
    await expect(page.locator('[data-testid="dispute-details"]')).toBeVisible();
    await expect(page.locator('[data-testid="dispute-reason"]')).toContainText('Overtime requested by production manager');
    await expect(page.locator('[data-testid="evidence-list"]')).toBeVisible();

    // Approve dispute
    await page.click('[data-testid="resolve-dispute-button"]');
    await page.click('[data-testid="approve-dispute-radio"]');
    await page.fill('[data-testid="resolution-notes"]', 'Production manager confirmation received. Weather delay verified with location reports. Overtime approved.');
    await page.click('[data-testid="confirm-resolution-button"]');

    // Verify dispute resolved
    await expect(page.locator('[data-testid="dispute-resolved-notification"]')).toBeVisible();
    await expect(page.locator('[data-testid="dispute-status-resolved"]')).toBeVisible();

    // Login back as crew member to verify resolution
    await page.click('[data-testid="user-menu"]');
    await page.click('[data-testid="logout-button"]');

    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.click('[data-testid="login-button"]');

    await page.click('[data-testid="timesheet-nav-link"]');
    await page.click('[data-testid="previously-disputed-timesheet"]');

    await expect(page.locator('[data-testid="entry-status-approved"]')).toBeVisible();
    await expect(page.locator('[data-testid="resolution-notification"]')).toContainText('Dispute resolved - Overtime approved');
  });

  test('Mobile responsive timesheet entry', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Login as crew member
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.click('[data-testid="login-button"]');

    // Verify mobile navigation
    await expect(page.locator('[data-testid="mobile-menu-button"]')).toBeVisible();
    await page.click('[data-testid="mobile-menu-button"]');
    await expect(page.locator('[data-testid="mobile-navigation"]')).toBeVisible();

    // Navigate to timesheet
    await page.click('[data-testid="timesheet-mobile-link"]');
    await expect(page.locator('[data-testid="timesheet-page"]')).toBeVisible();

    // Verify mobile form layout
    await expect(page.locator('[data-testid="mobile-timesheet-form"]')).toBeVisible();
    await expect(page.locator('[data-testid="date-input-mobile"]')).toBeVisible();
    await expect(page.locator('[data-testid="time-inputs-mobile"]')).toBeVisible();

    // Fill timesheet on mobile
    await page.fill('[data-testid="date-input-mobile"]', '2025-10-15');
    await page.fill('[data-testid="clock-in-mobile"]', '08:00');
    await page.fill('[data-testid="clock-out-mobile"]', '17:00');
    await page.fill('[data-testid="break-mobile"]', '60');

    // Use mobile-friendly project selector
    await page.click('[data-testid="project-select-mobile"]');
    await page.click('[data-testid="project-summer-blockbuster-mobile"]');

    // Submit timesheet
    await page.click('[data-testid="submit-timesheet-mobile"]');

    // Verify mobile success notification
    await expect(page.locator('[data-testid="mobile-success-notification"]')).toBeVisible();
    await expect(page.locator('[data-testid="mobile-success-notification"]')).toContainText('Timesheet submitted');
  });

  test('Offline functionality and sync', async ({ page }) => {
    // Simulate offline mode
    await page.context().setOffline(true);

    // Login (should work with cached credentials)
    await page.goto('http://localhost:3000');
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.click('[data-testid="login-button"]');

    // Verify offline indicator
    await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible();
    await expect(page.locator('[data-testid="offline-indicator"]')).toContainText('Offline Mode');

    // Navigate to timesheet
    await page.click('[data-testid="timesheet-nav-link"]');

    // Create timesheet entry offline
    await page.click('[data-testid="new-entry-button"]');
    await page.fill('[data-testid="date-picker"]', '2025-10-15');
    await page.fill('[data-testid="clock-in-time"]', '08:00');
    await page.fill('[data-testid="clock-out-time"]', '17:00');
    await page.fill('[data-testid="break-duration"]', '60');
    await page.fill('[data-testid="location-input"]', 'Studio A');

    // Submit offline
    await page.click('[data-testid="submit-timesheet-button"]');

    // Verify queued for sync
    await expect(page.locator('[data-testid="sync-queued-notification"]')).toBeVisible();
    await expect(page.locator('[data-testid="sync-queue-count"]')).toContainText('1');

    // Go back online
    await page.context().setOffline(false);

    // Verify sync completes
    await expect(page.locator('[data-testid="sync-complete-notification"]')).toBeVisible();
    await expect(page.locator('[data-testid="sync-queue-count"]')).toContainText('0');

    // Refresh to verify persisted data
    await page.reload();
    await page.click('[data-testid="timesheet-nav-link"]');
    await expect(page.locator('[data-testid="timesheet-entry-2025-10-15"]')).toBeVisible();
  });

  test('Performance with large datasets', async ({ page }) => {
    // Login and navigate to reports
    await page.fill('[data-testid="email-input"]', 'john.doe@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.click('[data-testid="login-button"]');

    await page.click('[data-testid="reports-nav-link"]');

    // Generate large report (simulating 6 months of data)
    await page.click('[data-testid="generate-report-button"]');
    await page.fill('[data-testid="report-start-date"]', '2025-04-15');
    await page.fill('[data-testid="report-end-date"]', '2025-10-15');
    await page.selectOption('[data-testid="report-type"]', 'detailed');
    await page.click('[data-testid="generate-report-submit"]');

    // Verify loading indicator
    await expect(page.locator('[data-testid="report-loading"]')).toBeVisible();

    // Verify report loads within reasonable time (5 seconds)
    await expect(page.locator('[data-testid="report-results"]')).toBeVisible({ timeout: 5000 });

    // Verify report has expected data
    await expect(page.locator('[data-testid="report-summary"]')).toBeVisible();
    await expect(page.locator('[data-testid="total-hours"]')).toBeVisible();
    await expect(page.locator('[data-testid="total-earnings"]')).toBeVisible();
    await expect(page.locator('[data-testid="report-table"]')).toBeVisible();

    // Test pagination performance
    await expect(page.locator('[data-testid="pagination-controls"]')).toBeVisible();
    await page.click('[data-testid="next-page-button"]');
    await expect(page.locator('[data-testid="report-table"]')).toBeVisible({ timeout: 2000 });

    // Test filtering performance
    await page.fill('[data-testid="report-filter"]', 'overtime');
    await page.click('[data-testid="apply-filter-button"]');
    await expect(page.locator('[data-testid="filtered-results"]')).toBeVisible({ timeout: 3000 });
  });
});