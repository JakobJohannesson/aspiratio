# Playwright Recorder Integration Guide

## Overview
The Streamlit app now includes Playwright's codegen recorder, allowing you to manually demonstrate how to download an annual report. The system records your actions and can potentially automate them for future downloads.

## How It Works

### 1. Recording Mode
- Click **"📹 Record with Playwright"** in the sidebar
- The app enters recording mode
- Click **"🚀 Start Recording Session"** to launch the Playwright browser

### 2. Recording Your Actions
When the browser opens:
1. **Navigate** to the annual reports section
2. **Click** on links, buttons, dropdown menus
3. **Interact** with any elements needed to reach the PDF
4. **Download** or click the PDF link
5. **Close** the browser when done

### 3. What Gets Recorded
Playwright's codegen automatically captures:
- All clicks and navigation
- Form inputs and selections
- Best locators for resilience:
  - Role-based selectors (`role="button"`)
  - Text content selectors
  - Test ID attributes
- Resilient element identification

### 4. Loading the Script
After closing the browser:
- Click **"📥 Load Recorded Script"**
- The script appears in the sidebar
- Review the Python code generated
- Save it for future use with **"💾 Save Script for Future Use"**

## Script Storage
Recorded scripts are saved to:
```
aspiratio/utils/playwright_scripts/{company_id}_download.py
```

## Example Workflow

### Scenario: NIBE Annual Report 2024
The automatic search fails because reports are behind a JavaScript-heavy interface.

**Steps:**
1. Select "NIBE" and year "2024"
2. Enable recording mode
3. Launch recorder with NIBE's IR URL
4. In the browser:
   - Click "Financial Reports" menu
   - Select "Annual Reports" from dropdown
   - Click on "2024 Annual Report"
   - Wait for PDF to load/download
5. Close browser
6. Load and review the recorded script
7. Save for future use

## Benefits

### For Users
- **Visual demonstration** of download path
- **No coding required** - just show how you'd do it manually
- **Captures complex interactions** (dropdowns, modals, dynamic content)

### For System
- **Best-practice locators** - Playwright prioritizes robust selectors
- **Resilient scripts** - Less likely to break with minor UI changes
- **Automation potential** - Scripts can be reviewed and integrated
- **Learning** - System can analyze patterns across companies

## Review Process

After recording, you can:
1. **Review** the generated Python code
2. **Identify patterns** - similar UI structures across companies
3. **Refactor** - extract common download patterns
4. **Integrate** - add to automated download logic
5. **Test** - run the script to verify it works

## Technical Details

### Generated Script Format
```python
import asyncio
from playwright.async_api import async_playwright

async def run(playwright):
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    
    # Your recorded actions here
    await page.goto("https://...")
    await page.get_by_role("button", name="Reports").click()
    # ... more actions
    
    await browser.close()

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

asyncio.run(main())
```

### Locator Strategy
Playwright prioritizes locators in this order:
1. **Role** - `get_by_role("button", name="Download")`
2. **Text** - `get_by_text("Annual Report 2024")`
3. **Test ID** - `get_by_test_id("download-btn")`
4. **CSS** - Only as last resort

## Future Enhancements

### Potential Automations
1. **Pattern detection** - Identify common download patterns
2. **Smart replay** - Automatically run recorded scripts
3. **Parameterization** - Replace year/company-specific values
4. **Error handling** - Add retries and fallbacks
5. **Validation** - Verify downloads succeeded

### Integration Ideas
1. Auto-run recorded scripts when automatic search fails
2. Build a library of company-specific download scripts
3. Use ML to identify similar UI patterns
4. Generate documentation from recorded actions

## Troubleshooting

### Browser doesn't open
- Check Playwright browsers are installed: `playwright install`
- Verify Python path: `.venv/bin/playwright --version`

### Script is empty
- Make sure you performed some actions before closing
- Recording only captures user interactions, not page loads

### Recording doesn't capture downloads
- This is normal - Playwright focuses on navigation and clicks
- The script will show you how to reach the download link
- Actual file download happens separately

## Best Practices

1. **Be deliberate** - Click clearly on the elements you need
2. **Wait for loads** - Give pages time to fully load before clicking
3. **Minimize actions** - Take the shortest path to the report
4. **Test the path** - Make sure your route works before recording
5. **Document tricky steps** - Note any timing or special requirements
