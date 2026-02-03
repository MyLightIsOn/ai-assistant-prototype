# Pull Request

## Description

<!-- Provide a brief description of the changes in this PR -->

## Type of Change

<!-- Mark the relevant option with an "x" -->

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🎨 Style/UI update (no functional changes)
- [ ] ♻️ Code refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] ✅ Test update

## Related Issues

<!-- Link to related issues using #issue-number -->

Closes #

## Changes Made

<!-- List the key changes made in this PR -->

-
-
-

## Testing Instructions

<!--
  IMPORTANT: This section is used by the automated PR review agent.
  Provide clear, step-by-step instructions for testing UI changes.
  Include URLs, test data, and expected outcomes.
-->

### Prerequisites

<!-- List any setup needed before testing -->

- [ ] Dependencies installed (`npm install`)
- [ ] Environment variables configured
- [ ] Database seeded with test data
- [ ] Services running: Frontend (port 3000), Backend (port 8000)

### Scenario 1: [Name of User Flow]

**Purpose:** [What this scenario tests]

**Steps:**
1. Navigate to `http://localhost:3000/[path]`
2. [Action to perform - e.g., "Click the 'New Task' button"]
3. [Next action - e.g., "Fill in the form with test data"]
4. [Final action - e.g., "Click Submit"]

**Expected Results:**
- [ ] [Expected outcome 1 - e.g., "Task appears in the list"]
- [ ] [Expected outcome 2 - e.g., "Success notification displays"]
- [ ] [Visual check - e.g., "No layout shifts or visual bugs"]

**Test Data:**
```json
{
  "field1": "value1",
  "field2": "value2"
}
```

### Scenario 2: [Another User Flow]

[Repeat structure for additional scenarios]

### Edge Cases to Test

<!-- List any edge cases or error scenarios -->

- [ ] [Edge case 1 - e.g., "Submit form with empty required fields"]
- [ ] [Edge case 2 - e.g., "Test with very long input text"]
- [ ] [Edge case 3 - e.g., "Test network error handling"]

### Visual Checks

<!-- Important for UI changes -->

- [ ] Responsive design (mobile, tablet, desktop)
- [ ] Dark mode (if applicable)
- [ ] Loading states
- [ ] Error states
- [ ] Accessibility (keyboard navigation, screen reader)

### Performance Checks

- [ ] No console errors
- [ ] Page loads in < 2 seconds
- [ ] Smooth animations (60fps)
- [ ] No memory leaks

## Screenshots

<!-- Add screenshots or GIFs showing the changes (especially for UI changes) -->

### Before

[Screenshot or description]

### After

[Screenshot or description]

## Checklist

<!-- Mark completed items with an "x" -->

- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented complex logic or algorithms
- [ ] I have updated documentation (if applicable)
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or feature works
- [ ] New and existing unit tests pass locally
- [ ] Any dependent changes have been merged and published

## Additional Notes

<!-- Any additional context, concerns, or questions -->

---

<!--
  When you're ready for review, run:
  /review-pr [pr-number]

  This will trigger the automated review agent that will:
  1. Run the test suite
  2. Test all scenarios in "Testing Instructions"
  3. Perform code quality analysis
  4. Generate a comprehensive review
-->
