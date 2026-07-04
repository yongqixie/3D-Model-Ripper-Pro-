#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CGTrader 下载器
技术核心: 模拟点击下载按钮 → 获取原始工程文件 (FBX/Blender源文件)
"""

import re
import time
import logging
import os
from pathlib import Path
from typing import Optional, Callable
from urllib.parse import urlparse

import requests
from playwright.sync_api import sync_playwright, Page

logger = logging.getLogger(__name__)


class CGTraderDownloader:
    def __init__(self, output_dir: Path, headless: bool = True, timeout: int = 120):
        self.output_dir = output_dir
        self.headless = headless
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0'
        })
        self.log_callback: Optional[Callable[[str], None]] = None
        self.progress_callback: Optional[Callable[[int], None]] = None

    def log(self, msg: str):
        if self.log_callback:
            self.log_callback(msg)
        logger.info(msg)

    def progress(self, value: int):
        if self.progress_callback:
            self.progress_callback(value)

    def download(self, url: str, output_format: str = '.fbx',
                 keep_skeleton: bool = True, keep_morphs: bool = True) -> str:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--window-size=1920,1080',
                ]
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0',
                accept_downloads=True,
            )

            context.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            })

            page = context.new_page()

            try:
                self.log(f"[CGTrader] 加载页面: {url}")
                self.progress(10)
                page.goto(url, wait_until='networkidle', timeout=self.timeout * 1000)
                time.sleep(3)
                self.progress(30)

                download_info = self._find_download_button(page)

                if download_info:
                    self.log(f"[CGTrader] 找到下载按钮: {download_info['text']}")
                    self.progress(50)
                    return self._click_download(page, download_info)
                else:
                    self.log("[CGTrader] 未找到下载按钮，尝试提取直接链接...")
                    direct_link = self._extract_direct_link(page)
                    if direct_link:
                        self.progress(60)
                        return self._download_direct(direct_link)
                    else:
                        raise RuntimeError("未找到下载按钮或链接，可能需要登录或付费")

            finally:
                context.close()
                browser.close()

    def _find_download_button(self, page: Page) -> dict:
        selectors = [
            'a[href*="download"]',
            'button:has-text("Download")',
            'button:has-text("Free download")',
            '.download-button',
            '[data-action="download"]',
            'a:has-text("Download")',
            'a:has-text("Free Download")',
            '.btn-download',
            '.product-download',
            'button:has-text("download")',
            'a[href*="free"]',
        ]

        for selector in selectors:
            try:
                element = page.query_selector(selector)
                if element:
                    text = element.inner_text().strip()[:50]
                    return {'selector': selector, 'element': element, 'text': text}
            except:
                continue

        return None

    def _click_download(self, page: Page, download_info: dict) -> str:
        with page.expect_download(timeout=120000) as download_info_ctx:
            page.click(download_info['selector'])

        download = download_info_ctx.value
        suggested_name = download.suggested_filename

        output_path = self.output_dir / suggested_name
        download.save_as(str(output_path))

        self.log(f"[CGTrader] 下载完成: {output_path}")
        self.progress(100)
        return str(output_path)

    def _extract_direct_link(self, page: Page) -> str:
        scripts = page.query_selector_all('script')
        for script in scripts:
            try:
                content = script.inner_text()
                patterns = [
                    r'https?://[^"\']+\.(?:fbx|blend|obj|glb|gltf|zip)[^"\']*',
                    r'downloadUrl["\']?\s*:\s*["\']([^"\']+)["\']',
                    r'fileUrl["\']?\s*:\s*["\']([^"\']+)["\']',
                ]
                for pattern in patterns:
                    match = re.search(pattern, content)
                    if match:
                        url = match.group(0) if 'http' in match.group(0) else match.group(1)
                        if url.startswith('http'):
                            return url
            except:
                continue

        return None

    def _download_direct(self, url: str) -> str:
        self.log(f"[CGTrader] 直接下载: {url}")
        resp = self.session.get(url, stream=True)
        filename = url.split('/')[-1].split('?')[0] or "model.zip"

        output_path = self.output_dir / filename
        total = int(resp.headers.get('content-length', 0))
        downloaded = 0

        with open(output_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        self.progress(60 + int((downloaded / total) * 40))

        self.log(f"[CGTrader] 直接下载完成: {output_path}")
        self.progress(100)
        return str(output_path)
