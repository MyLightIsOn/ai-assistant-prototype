# PR Review Workflow with Playwright UI Testing

## Visual Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DEVELOPER: Create PR                            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Uses PR template
                                  │ Includes Testing Instructions
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Pull Request Created                                               │
│  ├── Code changes                                                   │
│  ├── Description                                                    │
│  └── Testing Instructions (UI test scenarios)                       │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Trigger: /review-pr 42
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│              CLAUDE CODE: PR Review Agent                           │
└─────────────────────────────────────────────────────────────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
            ▼                     ▼                     ▼
┌───────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│   Phase 1:        │  │   Phase 2:       │  │   Phase 3:      │
│   Fetch PR        │  │   Setup          │  │   Run Tests     │
│                   │  │                   │  │                 │
│ • Get PR details  │  │ • Checkout branch │  │ • npm test      │
│ • Parse Testing   │  │ • npm install     │  │ • Capture       │
│   Instructions    │  │ • Start servers   │  │   results       │
│ • Analyze changes │  │   (port 3000)     │  │ • Note failures │
└───────────────────┘  └──────────────────┘  └─────────────────┘
            │                     │                     │
            └─────────────────────┼─────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Phase 4: UI Testing with Playwright 🎭                 │
│                                                                     │
│  For each scenario in Testing Instructions:                        │
│                                                                     │
│  1. Navigate to URL                                                │
│     → playwright_navigate("http://localhost:3000/tasks")           │
│     → Screenshot: 01-initial-load.png                              │
│                                                                     │
│  2. Perform user interactions                                      │
│     → playwright_click("button#new-task")                          │
│     → Screenshot: 02-modal-opened.png                              │
│     → playwright_fill("input[name='title']", "Test Task")          │
│     → Screenshot: 03-form-filled.png                               │
│                                                                     │
│  3. Submit and verify                                              │
│     → playwright_click("button[type='submit']")                    │
│     → playwright_wait_for("text='Task created'")                   │
│     → Screenshot: 04-task-created.png                              │
│                                                                     │
│  4. Check for errors                                               │
│     → playwright_console_messages()                                │
│     → Capture any errors or warnings                               │
│                                                                     │
│  5. Test responsive design                                         │
│     → playwright_set_viewport(375, 667)  // Mobile                 │
│     → Screenshot: 05-mobile-view.png                               │
│                                                                     │
│  Result: ✅ Pass / ❌ Fail / ⚠️ Issues                            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Phase 5: Code Quality Analysis                         │
│                                                                     │
│  • Architecture & Design                                           │
│  • Code Quality & Style                                            │
│  • Security Vulnerabilities                                        │
│  • Performance Issues                                              │
│  • Documentation                                                   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Phase 6: Generate Review Report                        │
│                                                                     │
│  📄 /tmp/pr-review-42/review.md                                    │
│  ├── Summary                                                       │
│  ├── Test Results                                                  │
│  ├── UI Testing Results (with screenshots)                         │
│  ├── Code Analysis                                                 │
│  ├── Security & Performance                                        │
│  └── Verdict: ✅ Approve / ⚠️ Needs Work / ❌ Changes Needed      │
│                                                                     │
│  📸 /tmp/pr-review-42/screenshots/                                 │
│  ├── 01-initial-load.png                                           │
│  ├── 02-modal-opened.png                                           │
│  ├── 03-form-filled.png                                            │
│  └── ... (all screenshots)                                         │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Optional: Post to PR
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│              gh pr comment 42 --body-file review.md                 │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. PR Template (`.github/PULL_REQUEST_TEMPLATE.md`)

Standardized format with **Testing Instructions** section:
```markdown
## Testing Instructions

### Scenario: User Login Flow
1. Navigate to `http://localhost:3000/login`
2. Fill email: `test@example.com`, password: `password123`
3. Click "Login" button
4. Verify redirect to dashboard

**Expected:** User logged in, no errors
```

### 2. Review Skill (`~/.claude/skills/review-pr/SKILL.md`)

Claude Code skill that orchestrates the entire review process:
- Fetches PR details
- Sets up environment
- Runs tests
- Uses Playwright MCP for UI testing
- Analyzes code
- Generates comprehensive report

### 3. Playwright MCP Server

Browser automation that enables:
- Real user interactions (clicks, typing, navigation)
- Screenshots at each step
- Console error monitoring
- Responsive design testing
- Visual verification

## What Makes This Special

### Traditional Code Review
```
✅ Code quality analysis
✅ Security check
✅ Architecture review
❌ No hands-on testing
❌ No visual verification
❌ No user flow validation
```

### This PR Review Agent
```
✅ Code quality analysis
✅ Security check
✅ Architecture review
✅ Automated test suite execution
✅ Hands-on UI testing (Playwright)
✅ Visual verification (screenshots)
✅ User flow validation
✅ Console error detection
✅ Responsive design testing
```

## Example: Bug Caught by UI Testing

**PR:** "Add task filtering feature"

**Code Review:** ✅ Looks good
- Clean code
- Tests pass
- No obvious bugs

**UI Testing with Playwright:** ❌ Found issue
```
Scenario: Filter by Priority

Step 3: Selected "High Priority" from dropdown
Step 4: Expected filtered list
Actual: List not filtered, all tasks still visible

Screenshot: 03-filter-not-working.png
Console: TypeError: Cannot read property 'priority' of undefined
```

**Result:** Bug caught before merge! 🎉

## Usage Examples

### Basic Usage
```bash
# Review any PR
/review-pr 42

# Or naturally
"Review PR #42"
```

### What Happens
```
Fetching PR #42...
Checking out feature/task-filtering...
Installing dependencies...
Starting dev servers...
Running test suite... 42 passed
Testing UI scenarios...
  ✅ Scenario 1: Create Task
  ❌ Scenario 2: Filter Tasks (found issue)
  ✅ Scenario 3: Delete Task
Analyzing code...
Generating review...

Review saved to: /tmp/pr-review-42/review.md
Screenshots saved to: /tmp/pr-review-42/screenshots/

Post review? [y/n]
```

### Review Output Structure
```markdown
# PR Review: #42 - Add task filtering

## Summary
Adds dropdown filter for task priority levels.

## Automated Tests
✅ 42 passed, 0 failed
📊 Coverage: 85%

## UI Testing Results

### Scenario: Filter by Priority - ❌ FAILED
**Issue:** Filter not applying to task list
**Screenshot:** 03-filter-not-working.png
**Console Error:** TypeError: Cannot read property...
**Fix Needed:** src/TaskList.tsx:42

### Scenario: Create Task - ✅ PASSED
**Screenshots:** 01-form.png, 02-created.png
**Result:** Task created successfully

## Code Analysis
### What's Good ✅
- Clean component structure
- Good prop types

### Concerns ⚠️
- Missing null check in filter logic
- Performance: Re-renders on every keystroke

### Suggestions 💡
[Specific code examples with before/after]

## Verdict: ⚠️ Needs Work

**Required Changes:**
- [ ] Fix filter logic (TaskList.tsx:42)
- [ ] Add null check for task.priority
```

## Integration Points

### Your AI Assistant Project

This integrates perfectly with your planned system:
```
Frontend (Next.js)
    ↓
Backend (FastAPI)
    ↓
Task Scheduler (APScheduler)
    ↓
Trigger PR Review ← Can be automated on cron
    ↓
Claude Code + Playwright
    ↓
Notification via ntfy.sh
    ↓
Detailed report to Gmail
```

**Scheduled PR Reviews:**
```python
# backend/scheduler.py
@scheduler.scheduled_job('cron', hour=9, minute=0)
def daily_pr_review():
    """Review all open PRs every morning"""
    prs = get_open_prs()
    for pr in prs:
        result = run_claude_code(f"/review-pr {pr.number}")
        send_notification(f"PR #{pr.number} reviewed", result)
        send_email(pr.author, result)
```

## Files Created

```
~/.claude/skills/review-pr/          # Global skill
├── SKILL.md                         # Main skill definition
├── README.md                        # Overview
├── USAGE_GUIDE.md                   # Detailed guide
├── PLAYWRIGHT_REFERENCE.md          # Command reference
└── review-template.md               # Output template

.github/                              # Project templates
├── PULL_REQUEST_TEMPLATE.md         # PR template
└── PR_REVIEW_WORKFLOW.md            # This file
```

## Next Steps

1. **Test the skill:**
   ```bash
   # Create a test PR
   git checkout -b test/review-agent
   # Make a small change
   git commit -m "test: Test PR review agent"
   git push
   gh pr create --fill

   # Review it
   /review-pr [pr-number]
   ```

2. **Customize for your project:**
   - Edit `SKILL.md` to add project-specific checks
   - Modify `review-template.md` for your preferred format
   - Add custom assertions in `PLAYWRIGHT_REFERENCE.md`

3. **Integrate with your AI assistant:**
   - Add scheduled PR reviews
   - Send notifications via ntfy.sh
   - Email detailed reports via Gmail
   - Track reviews in database

4. **Iterate and improve:**
   - Review several PRs
   - Adjust prompts based on quality
   - Add more test patterns
   - Build test scenario library

## Tips for Success

1. **Write clear testing instructions** - The agent follows them literally
2. **Include test data** - Makes testing more realistic
3. **Specify expected outcomes** - Helps agent verify correctness
4. **Use descriptive selectors** - Makes UI testing more reliable
5. **Test edge cases** - Don't just test the happy path

## Support & Documentation

- **Quick Reference:** `README.md`
- **Detailed Guide:** `USAGE_GUIDE.md`
- **Playwright Commands:** `PLAYWRIGHT_REFERENCE.md`
- **Skill Definition:** `SKILL.md`
- **PR Template:** `.github/PULL_REQUEST_TEMPLATE.md`

---

**Ready to use!** Run `/review-pr [pr-number]` on your next PR.
