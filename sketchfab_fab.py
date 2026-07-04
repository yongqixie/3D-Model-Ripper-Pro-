#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sketchfab / Fab 真实下载器
核心技术: 浏览器内存拦截 + glTF二进制流捕获 + 重组保存
"""

import json
import base64
import struct
import logging
import time
import re
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Callable
from urllib.parse import urlparse

import requests
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

logger = logging.getLogger(__name__)


INTERCEPT_SCRIPT = """
(() => {
    if (window.__MODEL_DOWNLOADER_HOOKED) return;
    window.__MODEL_DOWNLOADER_HOOKED = true;

    window.__CAPTURED_DATA = {
        networkRequests: [],
        gltfBuffers: [],
        textures: [],
        modelMetadata: null,
        sceneGraph: null,
        bones: [],
        morphs: [],
        animations: [],
        startTime: Date.now()
    };

    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        const url = args[0];
        const urlStr = typeof url === 'string' ? url : url.url;

        try {
            const response = await originalFetch.apply(this, args);

            if (urlStr && (
                urlStr.match(/\\.(glb|gltf|bin)$/i) ||
                urlStr.includes('model') ||
                urlStr.includes('geometry') ||
                urlStr.includes('mesh') ||
                urlStr.includes('scene')
            )) {
                try {
                    const clone = response.clone();
                    const buffer = await clone.arrayBuffer();
                    const bytes = new Uint8Array(buffer);

                    const isGLB = bytes.length > 4 && 
                        bytes[0] === 0x67 && bytes[1] === 0x6C && 
                        bytes[2] === 0x54 && bytes[3] === 0x46;

                    window.__CAPTURED_DATA.gltfBuffers.push({
                        source: 'fetch',
                        url: urlStr,
                        data: Array.from(bytes),
                        size: bytes.length,
                        isGLB: isGLB,
                        timestamp: Date.now()
                    });

                    console.log('[ModelDownloader] 捕获 Fetch:', urlStr, '大小:', bytes.length, 'GLB:', isGLB);
                } catch(e) {}
            }

            if (urlStr && urlStr.match(/\\.(png|jpg|jpeg|webp|ktx2|dds)$/i)) {
                try {
                    const clone = response.clone();
                    const buffer = await clone.arrayBuffer();
                    window.__CAPTURED_DATA.textures.push({
                        url: urlStr,
                        data: Array.from(new Uint8Array(buffer)),
                        size: buffer.byteLength,
                        timestamp: Date.now()
                    });
                } catch(e) {}
            }

            return response;
        } catch(e) {
            return originalFetch.apply(this, args);
        }
    };

    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        this._md_url = url;
        this._md_method = method;
        return originalOpen.call(this, method, url, ...rest);
    };

    XMLHttpRequest.prototype.send = function(...args) {
        this.addEventListener('load', function() {
            if (!this._md_url) return;

            const url = this._md_url;
            if (url.match(/\\.(glb|gltf|bin)$/i) || 
                url.includes('model') ||
                url.includes('geometry')) {
                try {
                    if (this.response instanceof ArrayBuffer) {
                        const bytes = new Uint8Array(this.response);
                        const isGLB = bytes.length > 4 && 
                            bytes[0] === 0x67 && bytes[1] === 0x6C && 
                            bytes[2] === 0x54 && bytes[3] === 0x46;

                        window.__CAPTURED_DATA.gltfBuffers.push({
                            source: 'xhr',
                            url: url,
                            data: Array.from(bytes),
                            size: bytes.length,
                            isGLB: isGLB,
                            timestamp: Date.now()
                        });
                        console.log('[ModelDownloader] 捕获 XHR:', url, '大小:', bytes.length);
                    }
                } catch(e) {}
            }
        });
        return originalSend.apply(this, args);
    };

    const origGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(type, attrs) {
        const gl = origGetContext.call(this, type, attrs);
        if (!gl || (type !== 'webgl' && type !== 'webgl2')) return gl;

        const _bufferData = gl.bufferData;
        gl.bufferData = function(target, data, usage) {
            if (data && data.byteLength > 1000) {
                try {
                    const bytes = new Uint8Array(
                        data.buffer ? data.buffer : data,
                        data.byteOffset || 0,
                        data.byteLength
                    );
                    window.__CAPTURED_DATA.gltfBuffers.push({
                        source: 'webgl-buffer',
                        target: target === gl.ARRAY_BUFFER ? 'ARRAY_BUFFER' : 'ELEMENT_ARRAY_BUFFER',
                        data: Array.from(bytes.slice(0, Math.min(bytes.length, 5000000))),
                        size: bytes.length,
                        timestamp: Date.now()
                    });
                } catch(e) {}
            }
            return _bufferData.call(this, target, data, usage);
        };

        return gl;
    };

    setTimeout(() => {
        try {
            if (window.Sketchfab && window.Sketchfab.apiClient) {
                window.__CAPTURED_DATA.modelMetadata = {
                    source: 'sketchfab-api',
                    data: window.Sketchfab.apiClient._model
                };
            }
            if (window.gltfData) {
                window.__CAPTURED_DATA.modelMetadata = {
                    source: 'window.gltfData',
                    data: window.gltfData
                };
            }
            if (window.__threeScene) {
                window.__CAPTURED_DATA.sceneGraph = {
                    source: 'threejs',
                    meshes: window.__threeScene.children.filter(c => c.type === 'Mesh').length
                };
            }
            if (window.__babylonScene) {
                window.__CAPTURED_DATA.sceneGraph = {
                    source: 'babylon',
                    meshes: window.__babylonScene.meshes.length
                };
            }
        } catch(e) {}
    }, 5000);

    console.log('[ModelDownloader] 拦截器已安装');
})();
"""

EXTRACT_SCRIPT = "() => { return window.__CAPTURED_DATA || { networkRequests: [], gltfBuffers: [], textures: [] }; }"


class SketchfabFabDownloader:
    def __init__(self, output_dir: Path, platform: str = 'sketchfab',
                 headless: bool = True, timeout: int = 120):
        self.output_dir = output_dir
        self.platform = platform
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

    def download(self, url: str, output_format: str = '.glb',
                 keep_skeleton: bool = True, keep_morphs: bool = True) -> str:
        model_id = self._extract_model_id(url)
        self.log(f"模型ID: {model_id}")

        with sync_playwright() as p:
            browser = self._launch_browser(p)
            context = self._create_context(browser)
            page = context.new_page()

            try:
                page.add_init_script(INTERCEPT_SCRIPT)
                self.log("[拦截器] WebGL/Fetch/XHR 数据拦截器已注入")

                self.log(f"[浏览器] 正在加载页面: {url}")
                self.progress(5)
                page.goto(url, wait_until='networkidle', timeout=self.timeout * 1000)

                self._wait_for_model(page)
                self.progress(20)

                self._interact_with_model(page)
                self.progress(40)

                self.log("[拦截器] 等待数据捕获完成...")
                time.sleep(8)

                captured = page.evaluate(EXTRACT_SCRIPT)
                self.log(f"[拦截器] 捕获到 {len(captured['gltfBuffers'])} 个数据包")
                self.log(f"[拦截器] 捕获到 {len(captured['textures'])} 个贴图")
                self.progress(70)

                return self._process_and_save(
                    captured, model_id, output_format, 
                    keep_skeleton, keep_morphs
                )

            finally:
                context.close()
                browser.close()

    def _launch_browser(self, p):
        return p.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--window-size=1920,1080',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-component-extensions-with-background-pages',
            ]
        )

    def _create_context(self, browser):
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0',
            locale='en-US',
            timezone_id='America/New_York',
            color_scheme='light',
            reduced_motion='no-preference',
        )

        context.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
        })

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)

        return context

    def _extract_model_id(self, url: str) -> str:
        match = re.search(r'[a-f0-9]{32}', url)
        if match:
            return match.group(0)
        match = re.search(r'/s/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        return path_parts[-1] if path_parts else hashlib.md5(url.encode()).hexdigest()[:16]

    def _wait_for_model(self, page: Page):
        self.log("[加载] 等待3D模型加载...")
        try:
            page.wait_for_selector('canvas', timeout=30000)
            self.log("[加载] Canvas元素已加载")
        except:
            self.log("[加载] 未检测到Canvas，继续尝试...")

        loading_selectors = [
            '.loading', '.spinner', '.progress', '.loader',
            '[class*="loading"]', '[class*="spinner"]',
            '.sketchfab-spinner', '.model-loading'
        ]
        for selector in loading_selectors:
            try:
                page.wait_for_selector(selector, state='hidden', timeout=10000)
            except:
                pass

        time.sleep(5)
        self.log("[加载] 模型加载完成")

    def _interact_with_model(self, page: Page):
        self.log("[交互] 模拟用户交互以触发完整加载...")
        canvas = page.query_selector('canvas')
        if canvas:
            box = canvas.bounding_box()
            if box:
                cx = box['x'] + box['width'] / 2
                cy = box['y'] + box['height'] / 2

                page.mouse.move(cx, cy)
                time.sleep(0.5)

                page.mouse.down()
                page.mouse.move(cx + 100, cy, steps=10)
                time.sleep(0.5)
                page.mouse.move(cx - 100, cy, steps=10)
                time.sleep(0.5)
                page.mouse.up()

                page.mouse.wheel(0, -5)
                time.sleep(1)
                page.mouse.wheel(0, 5)
                time.sleep(1)

        self.log("[交互] 交互完成")
        time.sleep(3)

    def _process_and_save(self, captured: dict, model_id: str,
                          output_format: str, keep_skeleton: bool,
                          keep_morphs: bool) -> str:
        buffers = captured.get('gltfBuffers', [])
        textures = captured.get('textures', [])

        if not buffers:
            raise RuntimeError("未捕获到任何模型数据，可能页面加载失败或被反爬")

        self.log(f"[处理] 分析 {len(buffers)} 个数据包...")
        buffers.sort(key=lambda x: x.get('size', 0), reverse=True)

        glb_buffers = [b for b in buffers if b.get('isGLB')]

        if glb_buffers:
            main_glb = glb_buffers[0]
            self.log(f"[处理] 找到GLB数据: {main_glb['size']} bytes")
            self.progress(80)
            return self._save_glb(main_glb, model_id, output_format, keep_skeleton)

        gltf_json_buffers = []
        for buf in buffers:
            try:
                data = bytes(buf['data'][:1000])
                if b'"asset"' in data or b'"meshes"' in data or b'"nodes"' in data:
                    gltf_json_buffers.append(buf)
            except:
                pass

        if gltf_json_buffers:
            self.progress(80)
            return self._save_gltf_json(gltf_json_buffers[0], model_id, output_format)

        self.progress(80)
        return self._save_raw_binary(buffers[0], model_id, output_format)

    def _save_glb(self, buffer_data: dict, model_id: str, 
                  output_format: str, keep_skeleton: bool) -> str:
        raw_bytes = bytes(buffer_data['data'])

        if len(raw_bytes) < 12:
            raise RuntimeError("GLB数据太短")

        magic = raw_bytes[:4]
        if magic != b'glTF':
            self.log(f"[警告] GLB魔数不匹配: {magic}, 尝试修复...")

        version = struct.unpack('<I', raw_bytes[4:8])[0]
        length = struct.unpack('<I', raw_bytes[8:12])[0]
        self.log(f"[GLB] 版本: {version}, 声明长度: {length}, 实际长度: {len(raw_bytes)}")

        if length > len(raw_bytes):
            self.log("[警告] GLB声明长度大于实际数据，可能数据不完整")
        elif length < len(raw_bytes):
            raw_bytes = raw_bytes[:length]

        output_path = self.output_dir / f"{model_id}.glb"
        with open(output_path, 'wb') as f:
            f.write(raw_bytes)

        self.log(f"[保存] GLB已保存: {output_path} ({len(raw_bytes)} bytes)")
        self.progress(95)

        if output_format != '.glb':
            return self._convert_format(output_path, output_format, keep_skeleton)

        self.progress(100)
        return str(output_path)

    def _save_gltf_json(self, buffer_data: dict, model_id: str, 
                        output_format: str) -> str:
        raw_bytes = bytes(buffer_data['data'])

        try:
            gltf_json = json.loads(raw_bytes.decode('utf-8'))
        except:
            raise RuntimeError("无法解析glTF JSON")

        json_path = self.output_dir / f"{model_id}.gltf"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(gltf_json, f, indent=2)

        self.log(f"[保存] glTF JSON已保存: {json_path}")
        self.progress(100)
        return str(json_path)

    def _save_raw_binary(self, buffer_data: dict, model_id: str,
                         output_format: str) -> str:
        raw_bytes = bytes(buffer_data['data'])

        if raw_bytes[:4] == b'glTF':
            ext = '.glb'
        elif raw_bytes[:4] in [b'\\x89PNG', b'\\xff\\xd8\\xff']:
            ext = '.png'
        else:
            ext = '.bin'

        output_path = self.output_dir / f"{model_id}{ext}"
        with open(output_path, 'wb') as f:
            f.write(raw_bytes)

        self.log(f"[保存] 原始二进制已保存: {output_path}")
        self.progress(100)
        return str(output_path)

    def _convert_format(self, input_path: Path, output_format: str,
                        keep_skeleton: bool) -> str:
        output_path = input_path.with_suffix(output_format)

        try:
            import trimesh
            mesh = trimesh.load(str(input_path))
            mesh.export(str(output_path))
            self.log(f"[转换] 格式转换完成: {output_path}")
            self.progress(100)
            return str(output_path)
        except Exception as e:
            self.log(f"[警告] trimesh转换失败: {e}")

        self.log("[警告] 格式转换失败，返回原始GLB")
        self.progress(100)
        return str(input_path)
