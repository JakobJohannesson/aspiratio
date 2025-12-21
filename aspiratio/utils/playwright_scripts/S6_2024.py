import asyncio
import re
from playwright.async_api import Playwright, async_playwright, expect


async def run(playwright: Playwright) -> None:
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto("https://www.atlascopcogroup.com/en/investors")
    await page.locator(".onetrust-pc-dark-filter").click()
    await page.get_by_role("button", name="Allow only necessary").click()
    await page.get_by_role("link", name="Reports and presentations Download our financial documents").click()
    async with page.expect_popup() as page1_info:
        await page.get_by_role("link", name="Annual Report 2024 (PDF)").click()
    page1 = await page1_info.value

    # ---------------------
    await context.close()
    await browser.close()


async def main() -> None:
    async with async_playwright() as playwright:
        await run(playwright)


asyncio.run(main())
