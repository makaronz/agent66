import { test, expect } from '@playwright/test';

test.describe('Critical User Journeys - Film Industry Time Tracking', () => {
  test('First-time user onboarding journey', async ({ page }) => {
    // Navigate to registration page
    await page.goto('http://localhost:3000/register');

    // Complete registration form
    await page.fill('[data-testid="first-name-input"]', 'Michael');
    await page.fill('[data-testid="last-name-input"]', 'Chen');
    await page.fill('[data-testid="email-input"]', 'michael.chen@filmcrew.com');
    await page.fill('[data-testid="phone-input"]', '+1234567890');
    await page.fill('[data-testid="password-input"]', 'SecurePassword123!');
    await page.fill('[data-testid="confirm-password-input"]', 'SecurePassword123!');

    // Select role
    await page.selectOption('[data-testid="role-select"]', 'CAMERA_OPERATOR');

    // Select department
    await page.selectOption('[data-testid="department-select"]', 'CAMERA');

    // Add union information
    await page.fill('[data-testid="union-number-input"]', 'IATSE-600-12345');
    await page.selectOption('[data-testid="union-select"]', 'IATSE');

    // Accept terms
    await page.check('[data-testid="terms-checkbox"]');
    await page.check('[data-testid="privacy-checkbox"]');

    // Submit registration
    await page.click('[data-testid="register-button"]');

    // Verify email verification screen
    await expect(page.locator('[data-testid="email-verification-required"]')).toBeVisible();
    await expect(page.locator('[data-testid="verification-instructions"]')).toContainText('michael.chen@filmcrew.com');

    // Simulate email verification (in real test, would check email)
    await page.fill('[data-testid="verification-code-input"]', '123456');
    await page.click('[data-testid="verify-email-button"]');

    // Complete onboarding wizard
    await expect(page.locator('[data-testid="onboarding-welcome"]')).toBeVisible();
    await page.click('[data-testid="onboarding-next-button"]');

    // Profile setup step
    await expect(page.locator('[data-testid="profile-setup-step"]')).toBeVisible();
    await page.fill('[data-testid="emergency-contact-name"]', 'Sarah Chen');
    await page.fill('[data-testid="emergency-contact-phone"]', '+1234567891');
    await page.fill('[data-testid="tax-id-input"]', '123-45-6789');
    await page.click('[data-testid="onboarding-next-button"]');

    // Equipment preferences step
    await expect(page.locator('[data-testid="equipment-preferences-step"]')).toBeVisible();
    await page.check('[data-testid="camera-red-checkbox"]');
    await page.check('[data-testid="camera-sony-checkbox"]');
    await page.check('[data-testid="lighting-led-checkbox"]');
    await page.click('[data-testid="onboarding-next-button"]');

    // Notification preferences step
    await expect(page.locator('[data-testid="notification-preferences-step"]')).toBeVisible();
    await page.check('[data-testid="email-notifications-checkbox"]');
    await page.check('[data-testid="sms-notifications-checkbox"]');
    await page.uncheck('[data-testid="push-notifications-checkbox"]');
    await page.click('[data-testid="onboarding-next-button"]');

    // Complete onboarding
    await expect(page.locator('[data-testid="onboarding-complete"]')).toBeVisible();
    await page.click('[data-testid="finish-onboarding-button"]');

    // Verify dashboard access
    await expect(page.locator('[data-testid="dashboard-header"]')).toBeVisible();
    await expect(page.locator('[data-testid="user-name"]')).toContainText('Michael Chen');
    await expect(page.locator("[data-testid='first-time-tour']")).toBeVisible();

    // Complete interactive tour
    await expect(page.locator('[data-testid="tour-step-1"]')).toBeVisible();
    await page.click('[data-testid="tour-next-button"]');

    await expect(page.locator('[data-testid="tour-step-2"]')).toBeVisible();
    await page.click('[data-testid="tour-next-button"]');

    await expect(page.locator('[data-testid="tour-step-3"]')).toBeVisible();
    await page.click('[data-testid="tour-finish-button"]');

    // Verify tour completion
    await expect(page.locator('[data-testid="tour-completion-badge"]')).toBeVisible();
  });

  test('Complete daily time tracking workflow', async ({ page }) => {
    // Login as experienced crew member
    await page.goto('http://localhost:3000/login');
    await page.fill('[data-testid="email-input"]', 'sarah.johnson@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'DailyPassword123!');
    await page.click('[data-testid="login-button"]');

    // Check today's schedule
    await expect(page.locator('[data-testid="todays-schedule"]')).toBeVisible();
    await expect(page.locator('[data-testid="scheduled-project"]')).toContainText('Summer Blockbuster 2025');
    await expect(page.locator('[data-testid="call-time"]')).toContainText('07:30 AM');

    // Clock in for the day
    await page.click('[data-testid="clock-in-button"]');
    await expect(page.locator('[data-testid="clock-in-confirmation"]')).toBeVisible();
    await page.fill('[data-testid="clock-in-location"]', 'Studio A - Base Camp');
    await page.click('[data-testid="confirm-clock-in-button"]');

    // Verify active timer
    await expect(page.locator('[data-testid="active-timer"]')).toBeVisible();
    await expect(page.locator('[data-testid="current-shift-duration"]')).toBeVisible();

    // Navigate to timesheet during shift
    await page.click('[data-testid="timesheet-nav-link"]');
    await expect(page.locator('[data-testid="in-progress-entry"]')).toBeVisible();

    // Add equipment usage during shift
    await page.click('[data-testid="add-equipment-button"]');
    await page.selectOption('[data-testid="equipment-select"]', 'RED Monstro 8K Camera');
    await page.fill('[data-testid="equipment-notes"]', 'Camera A1 - Primary unit for today');
    await page.click('[data-testid="add-equipment-confirm-button"]');

    // Add scene progress updates
    await page.click('[data-testid="add-scene-progress-button"]');
    await page.selectOption('[data-testid="scene-select"]', 'Scene 23');
    await page.selectOption('[data-testid="progress-status"]', 'COMPLETED');
    await page.fill('[data-testid="progress-notes"]', 'Exterior battle sequence completed successfully');
    await page.click('[data-testid="add-progress-confirm-button"]');

    // Take break (lunch)
    await page.click('[data-testid="start-break-button"]');
    await page.selectOption('[data-testid="break-type"]', 'LUNCH');
    await page.click('[data-testid="confirm-break-start-button"]');

    // Verify break timer
    await expect(page.locator('[data-testid="break-timer"]')).toBeVisible();

    // End break after 1 minute (simulate)
    await page.waitForTimeout(1000);
    await page.click('[data-testid="end-break-button"]');
    await page.click('[data-testid="confirm-break-end-button"]');

    // Continue work for the day
    await expect(page.locator('[data-testid="active-timer"]')).toBeVisible();

    // Clock out at end of day
    await page.click('[data-testid="clock-out-button"]');
    await expect(page.locator('[data-testid="clock-out-confirmation"]')).toBeVisible();
    await page.fill('[data-testid="clock-out-notes"]', 'Completed day ahead of schedule. All scenes shot successfully.');
    await page.click('[data-testid="confirm-clock-out-button"]');

    // Review and submit daily timesheet
    await expect(page.locator('[data-testid="daily-summary"]')).toBeVisible();
    await expect(page.locator('[data-testid="total-hours-worked"]')).toBeVisible();
    await expect(page.locator('[data-testid="break-time"]')).toBeVisible();
    await expect(page.locator('[data-testid="equipment-used"]')).toBeVisible();
    await expect(page.locator('[data-testid="scenes-completed"]')).toBeVisible();

    // Add additional notes
    await page.fill('[data-testid="daily-notes"]', 'Great day on set. Weather cooperated well. Team performance excellent.');

    // Submit for approval
    await page.click('[data-testid="submit-day-timesheet-button"]');
    await expect(page.locator('[data-testid="submission-confirmation"]')).toBeVisible();
    await page.click('[data-testid="confirm-submission-button"]');

    // Verify submission success
    await expect(page.locator('[data-testid="submission-success-notification"]')).toBeVisible();
    await expect(page.locator('[data-testid="timesheet-status-pending"]')).toBeVisible();
  });

  test('Supervisor daily workflow - Review and approve team timesheets', async ({ page }) => {
    // Login as department supervisor
    await page.goto('http://localhost:3000/login');
    await page.fill('[data-testid="email-input"]', 'david.miller@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'SupervisorPassword123!');
    await page.click('[data-testid="login-button"]');

    // Review supervisor dashboard
    await expect(page.locator('[data-testid="supervisor-dashboard"]')).toBeVisible();
    await expect(page.locator("[data-testid='team-status-overview']")).toBeVisible();
    await expect(page.locator('[data-testid="pending-approvals-count"]')).toBeVisible();
    await expect(page.locator('[data-testid="todays-schedule-overview"]')).toBeVisible();

    // Navigate to timesheet approvals
    await page.click('[data-testid="approvals-nav-link"]');
    await expect(page.locator('[data-testid="approvals-dashboard"]')).toBeVisible();

    // Filter by department
    await page.selectOption('[data-testid="department-filter"]', 'CAMERA');
    await page.click('[data-testid="apply-filter-button"]');

    // Review first pending timesheet
    await expect(page.locator('[data-testid="pending-timesheets-list"]')).toBeVisible();
    await page.click('[data-testid="timesheet-review-0"]');

    // Review detailed timesheet information
    await expect(page.locator('[data-testid="timesheet-details"]')).toBeVisible();
    await expect(page.locator('[data-testid="crew-member-info"]')).toBeVisible();
    await expect(page.locator('[data-testid="time-breakdown"]')).toBeVisible();
    await expect(page.locator('[data-testid="equipment-usage"]')).toBeVisible();
    await expect(page.locator('[data-testid="scene-progress"]')).toBeVisible();

    // Check for any alerts or issues
    const alertsCount = await page.locator('[data-testid="timesheet-alerts"]').count();
    if (alertsCount > 0) {
      await expect(page.locator('[data-testid="timesheet-alerts"]')).toBeVisible();
      await page.click('[data-testid="review-alerts-button"]');
    }

    // Cross-reference with production schedule
    await page.click('[data-testid="check-schedule-button"]');
    await expect(page.locator('[data-testid="schedule-comparison"]')).toBeVisible();
    await expect(page.locator('[data-testid="schedule-match-indicator"]')).toBeVisible();

    // Approve timesheet with notes
    await page.click('[data-testid="approve-timesheet-button"]');
    await page.fill('[data-testid="approval-notes"]', 'Excellent work today. All scenes completed on schedule. Equipment usage properly documented.');
    await page.check('[data-testid="confirm-overtime-checkbox"]'); // If overtime exists
    await page.click('[data-testid="submit-approval-button"]');

    // Quick approve remaining timesheets (bulk action)
    await page.click('[data-testid="back-to-list-button"]');
    await page.check('[data-testid="select-all-pending"]');
    await page.click('[data-testid="bulk-approve-button"]');
    await page.fill('[data-testid="bulk-approval-notes"]', 'Daily timesheets approved - All crew members met expectations.');
    await page.click('[data-testid="confirm-bulk-approval-button"]');

    // Generate daily report
    await page.click('[data-testid="reports-nav-link"]');
    await page.selectOption('[data-testid="report-type"]', 'daily-summary');
    await page.fill('[data-testid="report-date"]', '2025-10-15');
    await page.click('[data-testid="generate-report-button"]');

    // Review report results
    await expect(page.locator('[data-testid="report-results"]')).toBeVisible();
    await expect(page.locator('[data-testid="department-summary"]')).toBeVisible();
    await expect(page.locator('[data-testid="total-hours-department"]')).toBeVisible();
    await expect(page.locator('[data-testid="total-cost-department"]')).toBeVisible();

    // Export report for production manager
    await page.click('[data-testid="export-report-button"]');
    await page.selectOption('[data-testid="export-format"]', 'PDF');
    await page.click('[data-testid="download-report-button"]');
  });

  test('Production manager weekly review workflow', async ({ page }) => {
    // Login as production manager
    await page.goto('http://localhost:3000/login');
    await page.fill('[data-testid="email-input"]', 'lisa.wang@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'ManagerPassword123!');
    await page.click('[data-testid="login-button"]');

    // Navigate to production analytics
    await page.click('[data-testid="production-nav-link"]');
    await expect(page.locator('[data-testid="production-dashboard"]')).toBeVisible();

    // Review weekly budget status
    await expect(page.locator('[data-testid="budget-overview"]')).toBeVisible();
    await expect(page.locator('[data-testid="weekly-spend']")).toBeVisible();
    await expect(page.locator('[data-testid="budget-remaining"]')).toBeVisible();

    // Generate weekly cost report
    await page.click('[data-testid="weekly-reports-tab"]');
    await page.selectOption('[data-testid="report-week"]', '2025-W42'); // Current week
    await page.click('[data-testid="generate-weekly-report-button"]');

    // Review department breakdown
    await expect(page.locator('[data-testid="department-breakdown"]')).toBeVisible();
    await expect(page.locator('[data-testid="camera-department-costs"]')).toBeVisible();
    await expect(page.locator('[data-testid="lighting-department-costs"]')).toBeVisible();
    await expect(page.locator('[data-testid="sound-department-costs"]')).toBeVisible();

    // Review overtime analysis
    await page.click('[data-testid="overtime-analysis-tab"]');
    await expect(page.locator('[data-testid="overtime-trends"]')).toBeVisible();
    await expect(page.locator('[data-testid="overtime-by-department"]')).toBeVisible();

    // Check for cost overruns
    const overrunsCount = await page.locator('[data-testid="cost-overrun-alert"]').count();
    if (overrunsCount > 0) {
      await page.click('[data-testid="overrun-details-button"]');
      await expect(page.locator('[data-testid="overrun-explanation"]')).toBeVisible();
    }

    // Review crew performance metrics
    await page.click('[data-testid="crew-performance-tab"]');
    await expect(page.locator('[data-testid="crew-productivity-chart"]')).toBeVisible();
    await expect(page.locator('[data-testid="top-performers-list"]')).toBeVisible();

    // Approve weekly timesheets
    await page.click('[data-testid="weekly-approval-tab"]');
    await expect(page.locator('[data-testid="weekly-timesheets-summary"]')).toBeVisible();

    // Review any disputed timesheets
    const disputesCount = await page.locator('[data-testid="disputed-timesheet"]').count();
    if (disputesCount > 0) {
      await page.click('[data-testid="disputed-timesheet"]');
      await expect(page.locator('[data-testid="dispute-details"]')).toBeVisible();

      // Make decision on dispute
      await page.click('[data-testid="resolve-dispute-button"]');
      await page.selectOption('[data-testid="dispute-resolution"]', 'APPROVE');
      await page.fill('[data-testid="resolution-notes"]', 'Production schedule confirms extended hours were necessary.');
      await page.click('[data-testid="submit-resolution-button"]');
    }

    // Export weekly reports for stakeholders
    await page.click('[data-testid="export-reports-button"]');
    await page.check('[data-testid="include-budget-report"]');
    await page.check('[data-testid="include-crew-performance"]');
    await page.check('[data-testid="include-overtime-analysis"]');
    await page.selectOption('[data-testid="export-format"]', 'EXCEL');
    await page.click('[data-testid="download-package-button"]');

    // Schedule weekly review meeting
    await page.click('[data-testid="schedule-meeting-button"]');
    await page.fill('[data-testid="meeting-title"]', 'Weekly Production Review - Week 42');
    await page.fill('[data-testid="meeting-agenda"]', 'Budget review, crew performance, upcoming schedule adjustments');
    await page.selectOption('[data-testid="attendees-select"]', 'department-heads');
    await page.click('[data-testid="schedule-meeting-confirm-button']);

    // Verify meeting scheduled
    await expect(page.locator('[data-testid="meeting-scheduled-confirmation"]')).toBeVisible();
  });

  test('Payroll processor end-of-month workflow', async ({ page }) => {
    // Login as payroll processor
    await page.goto('http://localhost:3000/login');
    await page.fill('[data-testid="email-input"]', 'robert.brown@filmcrew.com');
    await page.fill('[data-testid="password-input"]', 'PayrollPassword123!');
    await page.click('[data-testid="login-button"]');

    // Navigate to payroll dashboard
    await page.click('[data-testid="payroll-nav-link"]');
    await expect(page.locator('[data-testid="payroll-dashboard"]')).toBeVisible();

    // Review monthly timesheet approval status
    await expect(page.locator('[data-testid="monthly-summary"]')).toBeVisible();
    await expect(page.locator('[data-testid="approved-timesheets-count"]')).toBeVisible();
    await expect(page.locator('[data-testid="pending-timesheets-count"]')).toBeVisible();

    // Process any remaining timesheets
    const pendingCount = await page.locator('[data-testid="pending-timesheets-count"]').textContent();
    if (parseInt(pendingCount || '0') > 0) {
      await page.click('[data-testid="process-pending-timesheets-button"]');
      await expect(page.locator('[data-testid="pending-timesheets-list"]')).toBeVisible();

      // Review and approve remaining timesheets
      const timesheetItems = await page.locator('[data-testid="pending-timesheet-item"]').count();
      for (let i = 0; i < timesheetItems; i++) {
        await page.click(`[data-testid="pending-timesheet-item"]:nth-child(${i + 1})`);
        await expect(page.locator('[data-testid="timesheet-review-modal"]')).toBeVisible();

        // Quick review
        await expect(page.locator('[data-testid="hours-calculated"]')).toBeVisible();
        await expect(page.locator('[data-testid="rate-applied"]')).toBeVisible();
        await expect(page.locator('[data-testid="total-earnings"]')).toBeVisible();

        // Approve
        await page.click('[data-testid="quick-approve-button"]');
        await page.click('[data-testid="confirm-approval-button"]');
      }
    }

    // Generate payroll report
    await page.click('[data-testid="generate-payroll-report-button"]');
    await page.selectOption('[data-testid="pay-period-select"]', '2025-10-01_to_2025-10-31');
    await page.click('[data-testid="generate-report-submit"]');

    // Review payroll calculations
    await expect(page.locator('[data-testid="payroll-report-results"]')).toBeVisible();
    await expect(page.locator('[data-testid="total-payroll-amount"]')).toBeVisible();
    await expect(page.locator('[data-testid="tax-summaries"]')).toBeVisible();
    await expect(page.locator('[data-testid="union-dues-summary"]')).toBeVisible();

    // Validate compliance
    await page.click('[data-testid="compliance-check-button"]');
    await expect(page.locator('[data-testid="compliance-results"]')).toBeVisible();
    await expect(page.locator('[data-testid="overtime-compliance"]')).toBeVisible();
    await expect(page.locator('[data-testid="minimum-wage-compliance"]')).toBeVisible();

    // Export payroll data
    await page.click('[data-testid="export-payroll-button"]');
    await page.check('[data-testid="include-detailed-breakdown"]');
    await page.check('[data-testid="include-tax-information"]');
    await page.check('[data-testid="include-union-reporting"]');
    await page.selectOption('[data-testid="export-format-select"]', 'ADP');
    await page.click('[data-testid="download-payroll-file"]');

    // Archive processed period
    await page.click('[data-testid="archive-period-button"]');
    await expect(page.locator('[data-testid="archive-confirmation"]')).toBeVisible();
    await page.fill('[data-testid="archive-notes"]', 'October 2025 payroll processed and exported to ADP');
    await page.click('[data-testid="confirm-archive-button]');

    // Verify archiving complete
    await expect(page.locator('[data-testid="archive-success-notification"]')).toBeVisible();
    await expect(page.locator('[data-testid="period-status-archived"]')).toBeVisible();
  });
});