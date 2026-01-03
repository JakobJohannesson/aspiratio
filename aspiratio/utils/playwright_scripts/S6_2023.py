import asyncio
import re
from playwright.async_api import Playwright, async_playwright, expect


async def run(playwright: Playwright) -> None:
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto("https://www.atlascopcogroup.com/en/investors")
    await page.get_by_role("button", name="Allow only necessary").click()
    await page.get_by_role("link", name="Reports and presentations Download our financial documents").click()
    await page.get_by_role("tab", name="2023").click()
    await page.get_by_role("button", name="Annual Report").click()
    await page.get_by_role("link", name="Atlas Copco Group publishes").click()
    async with page.expect_download() as download_info:
        await page.get_by_role("link", name="20240321 Annual report incl.").click()
    download = await download_info.value

    # ---------------------
    await context.close()
    await browser.close()


async def main() -> None:
    async with async_playwright() as playwright:
        await run(playwright)


asyncio.run(main())
