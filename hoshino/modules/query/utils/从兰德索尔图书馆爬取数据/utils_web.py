import asyncio
from pathlib import Path
import logging

from playwright.async_api import async_playwright

gs_proxy = {"server": "http://127.0.0.1:7897"}
gs_default_use_proxy: bool = True

async def fetch_html_async(url: str, use_proxy: bool = gs_default_use_proxy) -> str:
    """
    may raise TimeoutError
    """
    logging.debug(f"fetch_html_async [{url}] started")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy=gs_proxy if use_proxy else None)
        page = await browser.new_page()
        await page.goto(url, timeout=10000) # May raise TimeoutError
        await page.wait_for_load_state('networkidle')
        page_html = await page.content()
        await page.close()
        await browser.close()
    return page_html

async def fetch_html_and_save_async(url: str, filepath: Path, download_if_exists: bool, use_proxy: bool = gs_default_use_proxy) -> str:
    if download_if_exists or not filepath.exists():
        logging.debug(f"fetch_html_and_save_async [{url}, {filepath}] started")
        page_html = await fetch_html_async(url, use_proxy)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as fp:
            fp.write(page_html)
        return page_html
    else:
        with open(filepath, "r", encoding="utf-8") as fp:
            page_html = fp.read()
        return page_html

async def fetch_htmls_and_save_sequential_async(url2filepath: dict[str, Path], download_if_exists: bool, use_proxy: bool = gs_default_use_proxy) -> dict[str, str]:
    """
    Args:
        url2filepath: Dict[url: str, filepath: Path]
        download_if_exists: If True, will download the html even if the file exists.
    Returns:
        Dict[url: str, html_content: str]
    """
    logging.debug(f"fetch_htmls_and_save_async_old [<{len(url2filepath)} urls>, download_if_exists={download_if_exists}, use_proxy={use_proxy}] started")
    url2html = {}
    for url, filepath in url2filepath.items():
        url2html[url] = await fetch_html_and_save_async(url, filepath, download_if_exists, use_proxy)
    return url2html

async def fetch_htmls_and_save_async(url2filepath: dict[str, Path], download_if_exists: bool, use_proxy: bool = gs_default_use_proxy) -> dict[str, str]:
    """
    Args:
        url2filepath: Dict[url: str, filepath: Path]
        download_if_exists: 如果为 True，则即使文件存在也会下载
        use_proxy: 是否使用代理
    Returns:
        Dict[url: str, html_content: str]
    """
    logging.debug(f"fetch_htmls_and_save_async [<{len(url2filepath)} urls>, download_if_exists={download_if_exists}, use_proxy={use_proxy}] started")
    
    async def fetch_page(url: str, filepath: Path, semaphore: asyncio.Semaphore, context, download_if_exists: bool) -> tuple[str, str]:
        async with semaphore:
            if download_if_exists or not filepath.exists():
                logging.debug(f"(fetch_htmls_and_save_async) subtask [{url}] started")
                page = await context.new_page()
                try:
                    await page.goto(url, timeout=10000) # May raise TimeoutError
                    html_content = await page.content()
                except Exception as e:
                    logging.error(f"(fetch_htmls_and_save_async) Error fetching [{url}]: {e}")
                    return url, ""
                else:
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    with open(filepath, 'w', encoding='utf-8') as fp:
                        fp.write(html_content)
                    return url, html_content
                finally:
                    await page.close()
            else:
                with open(filepath, 'r', encoding='utf-8') as fp:
                    html_content = fp.read()
                return url, html_content

    semaphore = asyncio.Semaphore(4)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy=gs_proxy if use_proxy else None)
        context = await browser.new_context()
        
        tasks = []
        for url, filepath in url2filepath.items():
            tasks.append(fetch_page(url, filepath, semaphore, context, download_if_exists))
        results = await asyncio.gather(*tasks)
        
        await context.close()
        await browser.close()
        
        return {url: html_content for url, html_content in results}