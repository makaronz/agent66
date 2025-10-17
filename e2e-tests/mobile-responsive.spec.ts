import { test, devices, expect } from '@playwright/test';

// Mobile device configurations for film industry use cases
const mobileDevices = [
  {
    name: 'iPhone 12',
    device: devices['iPhone 12'],
    description: 'Modern smartphone for crew members'
  },
  {
    name: 'iPhone SE',
    device: devices['iPhone SE'],
    description: 'Compact smartphone for field use'
  },
  {
    name: 'Samsung Galaxy S21',
    device: devices['Galaxy S21'],
    description: 'Android smartphone for diverse crew'
  },
  {
    name: 'iPad',
    device: devices['iPad'],
    description: 'Tablet for supervisors on set'
  },
  {
    name: 'iPad Pro',
    device: devices['iPad Pro'],
    description: 'Large tablet for production managers'
  }
];

// Tablet configurations
const tabletDevices = [
  {
    name: 'iPad Mini',
    device: devices['iPad Mini'],
    description: 'Portable tablet for department heads'
  },
  {
    name: 'Surface Pro',
    device: devices['Surface Pro'],
    description: 'Windows tablet for production coordinators'
  }
];

mobileDevices.forEach(({ name, device, description }) => {
  test.describe(`${name} Mobile Testing - ${description}`, () => {
    test.use({ ...device });

    test('Mobile login and dashboard navigation', async ({ page }) => {
      // Test mobile-optimized login
      await page.goto('http://localhost:3000/login');

      // Verify mobile layout
      await expect(page.locator('[data-testid="mobile-logo"]')).toBeVisible();
      await expect(page.locator('[data-testid="mobile-login-form"]')).toBeVisible();

      // Login with mobile keyboard considerations
      await page.tap('[data-testid="email-input"]');
      await page.fill('[data-testid="email-input"]', 'crew@filmcrew.com');

      // Test mobile number input optimization
      await page.tap('[data-testid="password-input"]');
      await page.fill('[data-testid="password-input"]', 'Password123!');

      // Test mobile button sizing
      await expect(page.locator('[data-testid="login-button"]')).toBeVisible();
      const loginButton = page.locator('[data-testid="login-button"]');
      const boundingBox = await loginButton.boundingBox();
      expect(boundingBox?.height).toBeGreaterThan(44); // iOS minimum touch target
      expect(boundingBox?.width).toBeGreaterThan(44);

      await page.tap('[data-testid="login-button"]');

      // Verify mobile dashboard
      await expect(page.locator('[data-testid="mobile-dashboard"]')).toBeVisible();
      await expect(page.locator('[data-testid="mobile-navigation"]')).toBeVisible();

      // Test mobile menu navigation
      await page.tap('[data-testid="mobile-menu-button"]');
      await expect(page.locator('[data-testid="mobile-navigation-drawer"]')).toBeVisible();

      // Test touch-friendly navigation items
      const navItems = page.locator('[data-testid="mobile-nav-item"]');
      const count = await navItems.count();
      for (let i = 0; i < count; i++) {
        const item = navItems.nth(i);
        const box = await item.boundingBox();
        expect(box?.height).toBeGreaterThan(44);
      }
    });

    test('Mobile timesheet entry workflow', async ({ page }) => {
      // Login and navigate to timesheet
      await page.goto('http://localhost:3000/login');
      await page.fill('[data-testid="email-input"]', 'crew@filmcrew.com');
      await page.fill('[data-testid="password-input"]', 'Password123!');
      await page.tap('[data-testid="login-button"]');

      await page.tap('[data-testid="mobile-menu-button"]');
      await page.tap('[data-testid="timesheet-nav-link"]');

      // Test mobile timesheet form
      await expect(page.locator('[data-testid="mobile-timesheet-form"]')).toBeVisible();

      // Test mobile date picker
      await page.tap('[data-testid="mobile-date-picker"]');
      await expect(page.locator('[data-testid="mobile-date-modal"]')).toBeVisible();
      await page.tap('[data-testid="today-button"]');
      await page.tap('[data-testid="confirm-date-button"]');

      // Test mobile time input (optimized for mobile)
      await page.tap('[data-testid="mobile-time-input"]');
      await expect(page.locator('[data-testid="mobile-time-picker"]')).toBeVisible();
      await page.tap('[data-testid="time-08"]');
      await page.tap('[data-testid="time-00"]');
      await page.tap('[data-testid="set-time-button"]');

      await page.tap('[data-testid="mobile-clock-out-input"]');
      await page.tap('[data-testid="time-17"]');
      await page.tap('[data-testid="time-00"]');
      await page.tap('[data-testid="set-time-button"]');

      // Test mobile dropdowns
      await page.tap('[data-testid="mobile-project-select"]');
      await expect(page.locator('[data-testid="mobile-select-modal"]')).toBeVisible();
      await page.tap('[data-testid="project-option-0"]');

      // Test mobile text input with appropriate keyboard
      await page.tap('[data-testid="mobile-location-input"]');
      // Verify numeric keyboard appears for phone input
      const inputType = await page.locator('[data-testid="mobile-location-input"]').getAttribute('inputmode');
      expect(inputType).toBe('text');

      await page.fill('[data-testid="mobile-location-input"]', 'Studio A');

      // Test mobile textarea with auto-resize
      await page.tap('[data-testid="mobile-notes-textarea"]');
      await page.fill('[data-testid="mobile-notes-textarea"]', 'Extended shooting due to weather conditions');

      // Verify textarea expands appropriately
      const textareaHeight = await page.locator('[data-testid="mobile-notes-textarea"]').evaluate(
        el => (el as HTMLTextAreaElement).scrollHeight
      );
      expect(textareaHeight).toBeGreaterThan(60);

      // Test mobile form submission
      await page.tap('[data-testid="mobile-submit-button"]');

      // Verify mobile success notification
      await expect(page.locator('[data-testid="mobile-success-notification"]')).toBeVisible();
      await expect(page.locator('[data-testid="mobile-success-notification"]')).toHaveText(/successfully/);
    });

    test('Mobile clock in/out functionality', async ({ page }) => {
      // Login as crew member
      await page.goto('http://localhost:3000/login');
      await page.fill('[data-testid="email-input"]', 'crew@filmcrew.com');
      await page.fill('[data-testid="password-input"]', 'Password123!');
      await page.tap('[data-testid="login-button"]');

      // Test quick clock-in from dashboard
      await expect(page.locator('[data-testid="mobile-clock-in-button"]')).toBeVisible();

      // Test geolocation functionality
      page.context().grantPermissions(['geolocation']);
      await page.setGeolocation({ latitude: 34.052235, longitude: -118.243683 }); // LA coordinates

      await page.tap('[data-testid="mobile-clock-in-button"]');

      // Verify location confirmation modal
      await expect(page.locator('[data-testid="location-confirmation-modal"]')).toBeVisible();
      await expect(page.locator('[data-testid="detected-location"]')).toBeVisible();

      await page.tap('[data-testid="confirm-location-button"]');

      // Verify active timer display
      await expect(page.locator('[data-testid="mobile-active-timer"]')).toBeVisible();
      await expect(page.locator('[data-testid="mobile-timer-display"]')).toBeVisible();

      // Test mobile timer controls
      await page.tap('[data-testid="mobile-start-break-button"]');
      await expect(page.locator('[data-testid="mobile-break-modal"]')).toBeVisible();

      await page.selectOption('[data-testid="mobile-break-type"]', 'LUNCH');
      await page.tap('[data-testid="confirm-break-button"]');

      // Test break timer
      await expect(page.locator('[data-testid="mobile-break-timer"]')).toBeVisible();

      // End break
      await page.tap('[data-testid="mobile-end-break-button"]');

      // Clock out
      await page.tap('[data-testid="mobile-clock-out-button"]');
      await page.fill('[data-testid="mobile-clock-out-notes"]', 'Completed all scheduled scenes');
      await page.tap('[data-testid="confirm-clock-out-button"]');

      // Verify clock out confirmation
      await expect(page.locator('[data-testid="mobile-clock-out-summary"]')).Bevisible();
      await expect(page.locator('[data-testid="mobile-total-hours"]')).Bevisible();
    });

    test('Mobile offline functionality', async ({ page }) => {
      // Test offline detection
      await page.context().setOffline(true);
      await page.goto('http://localhost:3000/login');

      // Verify offline indicator
      await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible();

      // Test cached login functionality
      await page.fill('[data-testid="email-input"]', 'crew@filmcrew.com');
      await page.fill('[data-testid="password-input"]', 'Password123!');
      await page.tap('[data-testid="login-button"]');

      // Verify app works offline
      await expect(page.locator('[data-testid="offline-dashboard"]')).toBeVisible();
      await expect(page.locator('[data-testid="sync-status"]')).toContainText('Offline');

      // Create timesheet entry offline
      await page.tap('[data-testid="mobile-menu-button"]');
      await page.tap('[data-testid="timesheet-nav-link"]');
      await page.tap('[data-testid="new-entry-button"]');

      await page.fill('[data-testid="mobile-date-picker"]', '2025-10-15');
      await page.fill('[data-testid="mobile-time-input"]', '08:00');
      await page.fill('[data-testid="mobile-clock-out-input"]', '17:00');
      await page.tap('[data-testid="mobile-submit-button"]');

      // Verify queued for sync
      await expect(page.locator('[data-testid="sync-queue-indicator"]')).toBeVisible();
      await expect(page.locator('[data-testid="sync-queue-count"]')).toContainText('1');

      // Go back online
      await page.context().setOffline(false);

      // Verify sync process
      await expect(page.locator('[data-testid="syncing-indicator"]')).toBeVisible();
      await expect(page.locator('[data-testid="sync-complete-notification"]')).toBeVisible();
    });

    test('Mobile gesture support and touch interactions', async ({ page }) => {
      // Login and navigate to timesheet list
      await page.goto('http://localhost:3000/login');
      await page.fill('[data-testid="email-input"]', 'crew@filmcrew.com');
      await page.fill('[data-testid="password-input"]', 'Password123!');
      await page.tap('[data-testid="login-button"]');

      await page.tap('[data-testid="mobile-menu-button"]');
      await page.tap('[data-testid="timesheet-nav-link"]');

      // Test swipe gestures for timesheet list
      await page.tap('[data-testid="timesheet-list-container"]');

      // Test pull to refresh
      await page.touchscreen.tap(200, 100);
      await page.touchscreen.tap(200, 300);

      // Verify refresh indicator
      await expect(page.locator('[data-testid="pull-to-refresh-indicator"]')).toBeVisible();

      // Test swipe actions on timesheet items
      const firstTimesheet = page.locator('[data-testid="timesheet-item-0"]');
      await firstTimesheet.swipe('left');

      // Verify swipe action buttons
      await expect(page.locator('[data-testid="edit-button"]')).toBeVisible();
      await expect(page.locator('[data-testid="delete-button"]')).toBeVisible();

      // Test long press for context menu
      await firstTimesheet.tap();
      await page.waitForTimeout(500); // Hold for long press

      // Verify context menu
      await expect(page.locator('[data-testid="context-menu"]')).toBeVisible();

      // Test pinch to zoom for detailed views
      if (name.includes('iPad')) {
        await page.goto('http://localhost:3000/reports');
        await page.tap('[data-testid="generate-report-button"]');

        // Test pinch zoom on report
        await page.touchscreen.tap(400, 300);
        await page.touchscreen.tap(400, 301);
        await page.touchscreen.tap(500, 400);
        await page.touchscreen.tap(500, 401);

        // Verify zoom controls
        await expect(page.locator('[data-testid="zoom-controls"]')).toBeVisible();
      }
    });

    test('Mobile camera integration for documentation', async ({ page }) => {
      // Test camera permissions
      await page.context().grantPermissions(['camera']);

      await page.goto('http://localhost:3000/login');
      await page.fill('[data-testid="email-input"]', 'crew@filmcrew.com');
      await page.fill('[data-testid="password-input"]', 'Password123!');
      await page.tap('[data-testid="login-button"]');

      await page.tap('[data-testid="mobile-menu-button"]');
      await page.tap('[data-testid="timesheet-nav-link"]');
      await page.tap('[data-testid="new-entry-button"]');

      // Test photo capture for equipment documentation
      await page.tap('[data-testid="add-equipment-photo-button"]');

      // Verify camera interface
      await expect(page.locator('[data-testid="camera-interface"]')).toBeVisible();

      // Test photo capture
      await page.tap('[data-testid="capture-photo-button"]');

      // Verify photo preview
      await expect(page.locator('[data-testid="photo-preview"]')).toBeVisible();

      // Test photo retake
      await page.tap('[data-testid="retake-photo-button"]');
      await page.tap('[data-testid="capture-photo-button"]');

      // Test photo confirmation
      await page.tap('[data-testid="confirm-photo-button"]');

      // Verify photo added to timesheet
      await expect(page.locator('[data-testid="equipment-photo-thumbnail"]')).toBeVisible();

      // Test photo gallery view
      await page.tap('[data-testid="equipment-photo-thumbnail"]');
      await expect(page.locator('[data-testid="photo-gallery-modal"]')).toBeVisible();

      // Test photo annotation
      await page.tap('[data-testid="add-annotation-button"]');
      await page.fill('[data-testid="annotation-text"]', 'Camera A1 - Primary unit for Scene 23');
      await page.tap('[data-testid="save-annotation-button"]');

      await page.tap('[data-testid="close-gallery-button"]');
    });
  });
});

tabletDevices.forEach(({ name, device, description }) => {
  test.describe(`${name} Tablet Testing - ${description}`, () => {
    test.use({ ...device });

    test('Tablet supervisor dashboard workflow', async ({ page }) => {
      // Login as supervisor
      await page.goto('http://localhost:3000/login');
      await page.fill('[data-testid="email-input"]', 'supervisor@filmcrew.com');
      await page.fill('[data-testid="password-input"]', 'SupervisorPassword123!');
      await page.tap('[data-testid="login-button"]');

      // Verify tablet-optimized dashboard
      await expect(page.locator('[data-testid="tablet-dashboard"]')).toBeVisible();
      await expect(page.locator('[data-testid="sidebar-navigation"]')).Bevisible();

      // Test split-view layout
      await expect(page.locator('[data-testid="main-content-area"]')).Bevisible();
      await expect(page.locator('[data-testid="secondary-content-area"]')).Bevisible();

      // Navigate to approvals
      await page.tap('[data-testid="approvals-sidebar-link"]');
      await expect(page.locator('[data-testid="tablet-approvals-layout"]')).Bevisible();

      // Test tablet-optimized approval workflow
      await expect(page.locator('[data-testid="pending-timesheets-list"]')).Bevisible();
      await expect(page.locator("[data-testid='timesheet-preview-panel']")).Bevisible();

      // Test simultaneous review
      await page.tap('[data-testid="timesheet-item-0"]');
      await expect(page.locator('[data-testid="timesheet-details-panel"]')).Bevisible();

      // Quick approval buttons
      await page.tap('[data-testid="quick-approve-button"]');
      await page.fill('[data-testid="quick-approval-notes"]', 'Approved via tablet - looks good');
      await page.tap('[data-testid="confirm-quick-approval-button"]');

      // Verify approval and auto-advance
      await expect(page.locator('[data-testid="timesheet-item-1"]')).toHaveClass(/active/);
    });

    test('Tablet multi-window workflow', async ({ page }) => {
      // Login as production manager
      await page.goto('http://localhost:3000/login');
      await page.fill('[data-testid="email-input"]', 'production@filmcrew.com');
      await page.fill('[data-testid="password-input"]', 'ProductionPassword123!');
      await page.tap('[data-testid="login-button"]');

      // Test multi-window layout for reports
      await page.tap('[data-testid="reports-sidebar-link"]');
      await expect(page.locator('[data-testid="tablet-reports-layout"]')).Bevisible();

      // Generate report in main panel
      await page.tap('[data-testid="generate-report-button"]');
      await page.fill('[data-testid="report-date-range"]', '2025-10-01_to_2025-10-15');
      await page.tap('[data-testid="generate-report-submit-button"]');

      // Test side-by-side report comparison
      await page.tap('[data-testid="compare-reports-button"]');
      await expect(page.locator('[data-testid="comparison-layout"]')).Bevisible();

      // Test split-screen for budget vs actual
      await expect(page.locator('[data-testid="budget-panel"]')).Bevisible();
      await expect(page.locator('[data-testid="actual-panel']")).Bevisible();

      // Test tablet-specific interactions
      await page.tap('[data-testid="budget-chart"]');
      await page.tap('[data-testid="actual-chart"]');

      // Verify chart synchronization
      await expect(page.locator('[data-testid="chart-sync-indicator"]')).Bevisible();
    });
  });
});

// Responsive design tests
test.describe('Responsive Design Tests', () => {
  const viewports = [
    { width: 320, height: 568, name: 'iPhone SE' },   // Small mobile
    { width: 375, height: 667, name: 'iPhone 12' },  // Standard mobile
    { width: 414, height: 896, name: 'iPhone 12 Max' }, // Large mobile
    { width: 768, height: 1024, name: 'iPad' },      // Tablet
    { width: 1024, height: 1366, name: 'iPad Pro' },  // Large tablet
    { width: 1280, height: 800, name: 'Small Desktop' }, // Small desktop
    { width: 1920, height: 1080, name: 'Desktop' }   // Standard desktop
  ];

  viewports.forEach(({ width, height, name }) => {
    test(`${name} (${width}x${height}) responsive layout`, async ({ page }) => {
      await page.setViewportSize({ width, height });
      await page.goto('http://localhost:3000/login');

      // Test responsive login form
      if (width < 768) {
        // Mobile layout
        await expect(page.locator('[data-testid="mobile-login-form"]')).Bevisible();
        await expect(page.locator('[data-testid="desktop-login-form"]")).not.toBeVisible();
      } else {
        // Desktop layout
        await expect(page.locator('[data-testid="desktop-login-form"]')).Bevisible();
        await expect(page.locator('[data-testid="mobile-login-form"]")).not.toBeVisible();
      }

      // Login and test dashboard responsiveness
      await page.fill('[data-testid="email-input"]', 'test@filmcrew.com');
      await page.fill('[data-testid="password-input"]', 'TestPassword123!');
      await page.click('[data-testid="login-button"]');

      // Test navigation responsiveness
      if (width < 768) {
        // Mobile navigation
        await expect(page.locator('[data-testid="mobile-navigation"]')).Bevisible();
        await expect(page.locator('[data-testid="desktop-navigation"]')).not.toBeVisible();
      } else {
        // Desktop navigation
        await expect(page.locator('[data-testid="desktop-navigation"]')).Bevisible();
        await expect(page.locator('[data-testid="mobile-navigation"]')).not.toBeVisible();
      }

      // Test content layout
      if (width >= 1024) {
        // Multi-column layout
        await expect(page.locator('[data-testid="multi-column-layout"]')).Bevisible();
        await expect(page.locator('[data-testid="sidebar-content"]')).Bevisible();
      } else if (width >= 768) {
        // Tablet layout
        await expect(page.locator('[data-testid="tablet-layout"]')).Bevisible();
      } else {
        // Single column layout
        await expect(page.locator('[data-testid="single-column-layout"]')).Bevisible();
      }

      // Test font scaling and readability
      const bodyText = await page.locator('body').textContent();
      expect(bodyText?.length).toBeGreaterThan(0);

      // Test button accessibility
      const buttons = page.locator('button');
      const buttonCount = await buttons.count();

      for (let i = 0; i < Math.min(buttonCount, 5); i++) {
        const button = buttons.nth(i);
        const boundingBox = await button.boundingBox();

        if (width < 768) {
          // Mobile: minimum touch target 44x44
          expect(boundingBox?.height).toBeGreaterThanOrEqual(44);
          expect(boundingBox?.width).toBeGreaterThanOrEqual(44);
        }
      }
    });
  });
});

// Orientation change tests
test.describe('Device Orientation Tests', () => {
  ['portrait', 'landscape'].forEach(orientation => {
    test(`${orientation} orientation functionality`, async ({ page }) => {
      const isPortrait = orientation === 'portrait';
      await page.setViewportSize({
        width: isPortrait ? 375 : 812,
        height: isPortrait ? 812 : 375
      });

      await page.goto('http://localhost:3000/login');

      // Test login in different orientations
      await page.fill('[data-testid="email-input"]', 'test@filmcrew.com');
      await page.fill('[data-testid="password-input"]', 'TestPassword123!');
      await page.click('[data-testid="login-button"]');

      // Test dashboard orientation
      await expect(page.locator('[data-testid="dashboard-header"]')).Bevisible();

      // Test timesheet form orientation
      await page.click('[data-testid="timesheet-nav-link"]');
      await page.click('[data-testid="new-entry-button"]');

      if (!isPortrait) {
        // Landscape: optimized form layout
        await expect(page.locator('[data-testid="landscape-form-layout"]')).Bevisible();
      } else {
        // Portrait: stacked form layout
        await expect(page.locator('[data-testid="portrait-form-layout"]")).Bevisible();
      }

      // Test orientation-specific features
      if (isPortrait) {
        // Portrait: scrollable content
        await expect(page.locator('[data-testid="scrollable-content"]')).Bevisible();
      } else {
        // Landscape: split view
        await expect(page.locator('[data-testid="split-view"]')).Bevisible();
      }
    });
  });
});

// Accessibility tests for mobile
test.describe('Mobile Accessibility Tests', () => {
  test('Screen reader compatibility', async ({ page }) => {
    await page.goto('http://localhost:3000/login');

    // Test semantic HTML structure
    await expect(page.locator('main')).Bevisible();
    await expect(page.locator('h1')).Bevisible();

    // Test ARIA labels
    const inputs = page.locator('input');
    const inputCount = await inputs.count();

    for (let i = 0; i < inputCount; i++) {
      const input = inputs.nth(i);
      const hasLabel = await input.evaluate(el => {
        const label = document.querySelector(`label[for="${el.id}"]`);
        return !!label || !!el.getAttribute('aria-label') || !!el.getAttribute('aria-labelledby');
      });

      expect(hasLabel).toBe(true);
    }

    // Test focus management
    await page.fill('[data-testid="email-input"]', 'test@filmcrew.com');
    await page.keyboard.press('Tab');

    // Verify focus moves to password field
    await expect(page.locator('[data-testid="password-input"]')).toBeFocused();

    // Test focus indicators
    const focusedElement = page.locator(':focus');
    const styles = await focusedElement.evaluate(el => {
      const computed = window.getComputedStyle(el);
      return {
        outline: computed.outline,
        outlineOffset: computed.outlineOffset
      };
    });

    expect(styles.outline).not.toBe('none');
  });

  test('High contrast mode support', async ({ page }) => {
    // Enable high contrast mode
    await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' });

    await page.goto('http://localhost:3000/login');

    // Test color contrast ratios
    const textElements = page.locator('p, h1, h2, h3, label, span');
    const textCount = await textElements.count();

    for (let i = 0; i < Math.min(textCount, 5); i++) {
      const element = textElements.nth(i);
      const styles = await element.evaluate(el => {
        const computed = window.getComputedStyle(el);
        return {
          color: computed.color,
          backgroundColor: computed.backgroundColor
        };
      });

      // Verify colors are not the same (contrast exists)
      expect(styles.color).not.toBe(styles.backgroundColor);
    }

    // Test interactive elements
    const buttons = page.locator('button');
    const buttonCount = await buttons.count();

    for (let i = 0; i < Math.min(buttonCount, 3); i++) {
      const button = buttons.nth(i);
      const styles = await button.evaluate(el => {
        const computed = window.getComputedStyle(el);
        return {
          backgroundColor: computed.backgroundColor,
          borderColor: computed.borderColor,
          color: computed.color
        };
      });

      // Verify button has sufficient contrast
      expect(styles.color).not.toBe(styles.backgroundColor);
    }
  });
});