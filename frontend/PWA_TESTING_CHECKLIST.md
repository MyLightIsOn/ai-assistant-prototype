# PWA Testing Checklist

This document provides a comprehensive testing checklist for verifying Progressive Web App functionality.

## Prerequisites

Before testing PWA features, ensure:

- [ ] App is built for production: `npm run build`
- [ ] App is served via HTTPS or localhost
- [ ] Modern browser with PWA support (Chrome, Edge, Safari, Firefox)

## Automated Tests

### Run PWA Test Suite

```bash
npm test -- lib/__tests__/pwa.test.ts
```

Expected: All 11 tests should pass:
- Service worker registration tests
- Manifest validation tests
- Installation event handling tests
- Offline support tests

## Manual Testing

### 1. Service Worker Registration

**Chrome/Edge DevTools:**
1. Build and start app: `npm run build && npm start`
2. Open DevTools (F12)
3. Navigate to Application > Service Workers
4. Verify service worker is registered and activated
5. Check service worker URL: `/sw.js`

**Status:** [ ] Pass / [ ] Fail

### 2. Manifest Validation

**Chrome/Edge DevTools:**
1. Open DevTools (F12)
2. Navigate to Application > Manifest
3. Verify all fields are present:
   - Name: "AI Assistant"
   - Start URL: "/"
   - Display: "standalone"
   - Theme Color: "#000000"
   - Icons: 192x192 and 512x512
4. Check for warnings/errors

**Status:** [ ] Pass / [ ] Fail

### 3. iOS Installation (Safari)

**Steps:**
1. Open app in Safari on iOS device
2. Tap Share button (square with arrow)
3. Scroll and tap "Add to Home Screen"
4. Verify icon appears correctly
5. Tap icon to launch app
6. Verify app opens in standalone mode (no Safari UI)
7. Verify app icon and splash screen

**Status:** [ ] Pass / [ ] Fail / [ ] N/A

### 4. Android Installation (Chrome)

**Steps:**
1. Open app in Chrome on Android device
2. Look for install banner or tap menu (three dots)
3. Tap "Install app" or "Add to Home Screen"
4. Verify icon appears correctly
5. Tap icon to launch app
6. Verify app opens in standalone mode (no browser UI)

**Status:** [ ] Pass / [ ] Fail / [ ] N/A

### 5. Desktop Installation (Chrome/Edge)

**Steps:**
1. Open app in Chrome or Edge
2. Look for install icon in address bar (⊕ or computer icon)
3. Click install icon or use browser menu > "Install AI Assistant"
4. Verify installation dialog shows correct app info
5. Click "Install"
6. Verify app opens in standalone window
7. Check app appears in Start Menu/Launchpad

**Status:** [ ] Pass / [ ] Fail / [ ] N/A

### 6. Offline Functionality

**Test Static Assets:**
1. Open app while online
2. Open DevTools > Network tab
3. Navigate through app pages
4. Set throttling to "Offline"
5. Refresh page
6. Verify static assets load from service worker
7. Verify basic UI renders correctly

**Status:** [ ] Pass / [ ] Fail

**Test API Caching:**
1. Load app with network online
2. Navigate to Tasks page (triggers API calls)
3. Open DevTools > Network tab
4. Set throttling to "Offline"
5. Verify cached API responses are used (check Network tab for "(from ServiceWorker)")
6. Note: Fresh API calls will fail offline (expected behavior)

**Status:** [ ] Pass / [ ] Fail

### 7. Caching Strategy Verification

**Test Font Caching (CacheFirst):**
1. Open DevTools > Network tab
2. Load app (fonts should load from network)
3. Reload page
4. Verify Google Fonts load from cache (Status: "(from ServiceWorker)")

**Status:** [ ] Pass / [ ] Fail

**Test Image Caching (StaleWhileRevalidate):**
1. Open DevTools > Network tab
2. Load app with images
3. Reload page
4. Verify images load from cache but also revalidate in background

**Status:** [ ] Pass / [ ] Fail

**Test API Caching (NetworkFirst):**
1. Open DevTools > Network tab
2. Load Tasks page
3. Go offline (throttling)
4. Reload page
5. Verify API responses from cache (5-minute expiration)
6. Go back online
7. Verify network is preferred when available

**Status:** [ ] Pass / [ ] Fail

### 8. Update Mechanism

**Test Service Worker Update:**
1. Make a small change to app (e.g., change text)
2. Build new version: `npm run build`
3. Deploy/restart server
4. Open app in browser
5. Hard refresh (Cmd+Shift+R / Ctrl+Shift+F5)
6. Verify update is applied
7. Check DevTools > Application > Service Workers for update status

**Status:** [ ] Pass / [ ] Fail

### 9. App Shortcuts

**Desktop (Chrome/Edge):**
1. Install app on desktop
2. Right-click app icon in taskbar/dock
3. Verify shortcuts appear:
   - Dashboard
   - Tasks
4. Click a shortcut
5. Verify app opens to correct page

**Status:** [ ] Pass / [ ] Fail / [ ] N/A

**Android:**
1. Long-press app icon on home screen
2. Verify shortcuts appear
3. Tap a shortcut
4. Verify app opens to correct page

**Status:** [ ] Pass / [ ] Fail / [ ] N/A

### 10. Theme and Display

**Verify Theme Color:**
1. Install app on mobile device
2. Open app
3. Verify status bar matches theme color (#000000 - black)

**Status:** [ ] Pass / [ ] Fail / [ ] N/A

**Verify Standalone Display:**
1. Install app
2. Launch from home screen/app list
3. Verify no browser UI (address bar, tabs, etc.)
4. Verify full-screen app experience

**Status:** [ ] Pass / [ ] Fail

### 11. Responsive Design

**Mobile:**
1. Open app on mobile device
2. Test portrait and landscape orientations
3. Verify UI adapts correctly
4. Check all interactive elements are accessible

**Status:** [ ] Pass / [ ] Fail

**Desktop:**
1. Install app on desktop
2. Resize window (small, medium, large)
3. Verify responsive breakpoints work
4. Check sidebar, content area adapt correctly

**Status:** [ ] Pass / [ ] Fail

### 12. Performance

**Lighthouse Audit:**
1. Open app in Chrome
2. Open DevTools > Lighthouse
3. Select "Progressive Web App" category
4. Run audit
5. Verify score >= 90
6. Check for any PWA-specific issues

**Expected Passing Criteria:**
- [x] Installable
- [x] Provides a valid manifest
- [x] Registers a service worker
- [x] Uses HTTPS (or localhost)
- [x] Fast load times
- [x] Responsive design

**Score:** [ ] ___ / 100

**Status:** [ ] Pass (>= 90) / [ ] Needs Improvement (< 90)

## Browser Compatibility

Test PWA features on multiple browsers:

### Chrome/Chromium
- [ ] Installation works
- [ ] Service worker registers
- [ ] Offline mode works
- [ ] Caching strategy works

### Edge
- [ ] Installation works
- [ ] Service worker registers
- [ ] Offline mode works
- [ ] Caching strategy works

### Safari (macOS)
- [ ] Installation works
- [ ] Service worker registers
- [ ] Offline mode works
- [ ] Caching strategy works

### Safari (iOS)
- [ ] "Add to Home Screen" works
- [ ] Icon displays correctly
- [ ] Standalone mode works
- [ ] Status bar styling correct

### Firefox
- [ ] Installation works (if supported)
- [ ] Service worker registers
- [ ] Offline mode works
- [ ] Caching strategy works

## Troubleshooting

### Service Worker Not Registering

**Symptoms:**
- No service worker in DevTools
- PWA not installable

**Solutions:**
1. Verify production build: `NODE_ENV=production npm run build`
2. Check browser console for errors
3. Verify HTTPS or localhost
4. Clear browser cache and reload

### App Not Installable

**Symptoms:**
- No install prompt/icon appears
- Install option not in browser menu

**Solutions:**
1. Verify manifest.json is accessible: `http://localhost:3000/manifest.json`
2. Check all required manifest fields are present
3. Verify icons exist: `/icon-192x192.png`, `/icon-512x512.png`
4. Ensure service worker is registered
5. Try hard refresh (Cmd+Shift+R / Ctrl+Shift+F5)

### Caching Issues

**Symptoms:**
- Old content still showing after update
- Changes not appearing

**Solutions:**
1. Unregister service worker in DevTools
2. Clear cache: DevTools > Application > Storage > Clear site data
3. Hard reload: Cmd+Shift+R / Ctrl+Shift+F5
4. Rebuild app: `npm run build`

### Offline Mode Not Working

**Symptoms:**
- App shows error when offline
- No cached content available

**Solutions:**
1. Verify service worker is active
2. Check cache storage in DevTools > Application > Cache Storage
3. Ensure app was loaded online first (to populate cache)
4. Check network tab for service worker responses

## Sign-off

### Test Summary

- **Total Tests:** ___ / 12 core features
- **Passed:** ___
- **Failed:** ___
- **Skipped:** ___

### Tester Information

- **Name:** _______________
- **Date:** _______________
- **Browser Versions Tested:** _______________
- **Devices Tested:** _______________

### Notes

_______________________________________________
_______________________________________________
_______________________________________________

### Final Approval

- [ ] All critical PWA features working
- [ ] No blocking issues found
- [ ] Ready for production deployment

**Approved By:** _______________
**Date:** _______________
