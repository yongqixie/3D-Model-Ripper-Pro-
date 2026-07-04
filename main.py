#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D Model Ripper Pro v2.0
模仿 3D Ripper DX 经典界面风格
支持: Sketchfab, Fab, CGTrader
技术: 浏览器内存拦截 + WebGL数据流捕获 + 骨骼/变形键保留

打包命令:
    pyinstaller --clean --onefile --windowed --icon=assets/icons/ripper-x.ico main.py
"""

import sys
import os
import json
import time
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

# ============ PyInstaller 资源路径处理 ============
def resource_path(relative_path):
    """获取打包后的资源路径"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ============ PyQt5 导入 ============
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QLineEdit, QComboBox, QCheckBox, QGroupBox,
        QTextEdit, QProgressBar, QStatusBar, QFileDialog,
        QMessageBox, QSplitter, QFrame, QGridLayout, QSpinBox, QTabWidget,
        QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QDialogButtonBox,
        QSizePolicy, QAction
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QSettings
    from PyQt5.QtGui import QIcon, QFont, QPalette, QColor, QPixmap, QCursor
except ImportError:
    print("ERROR: 需要安装 PyQt5")
    print("pip install PyQt5")
    sys.exit(1)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# 3D Ripper Pro 经典风格样式表
# ============================================================
RIPPER_STYLE = """
QMainWindow {
    background-color: #D4D0C8;
}
QWidget {
    background-color: #D4D0C8;
    font-family: "Tahoma", "Microsoft Sans Serif", sans-serif;
    font-size: 11px;
}
#titleBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0A246A, stop:1 #0A246A);
    color: white;
    padding: 4px;
}
#titleLabel {
    color: white;
    font-size: 13px;
    font-weight: bold;
    font-family: "Arial", sans-serif;
}
#versionLabel {
    color: #A0C0FF;
    font-size: 10px;
}
#leftPanel {
    background-color: #4A4A4A;
    border-right: 2px solid #808080;
}
#leftPanel QPushButton {
    background-color: #5A5A5A;
    color: #E0E0E0;
    border: 1px solid #707070;
    border-radius: 2px;
    padding: 8px 4px;
    font-size: 10px;
    min-height: 40px;
}
#leftPanel QPushButton:hover {
    background-color: #6A6A6A;
    border-color: #888888;
}
#leftPanel QPushButton:pressed {
    background-color: #3A3A3A;
}
#leftPanel QPushButton:checked {
    background-color: #0A246A;
    border-color: #1A449A;
    color: white;
}
#settingsArea {
    background-color: #D4D0C8;
    border: 2px solid #808080;
    border-right-color: #FFFFFF;
    border-bottom-color: #FFFFFF;
}
QGroupBox {
    background-color: #D4D0C8;
    border: 2px solid #808080;
    border-right-color: #FFFFFF;
    border-bottom-color: #FFFFFF;
    margin-top: 8px;
    padding-top: 8px;
    font-weight: bold;
    font-size: 11px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #000000;
}
QLineEdit {
    background-color: #FFFFFF;
    border: 2px solid #808080;
    border-right-color: #FFFFFF;
    border-bottom-color: #FFFFFF;
    padding: 3px 5px;
    color: #000000;
}
QLineEdit:focus {
    border-color: #0A246A;
}
QComboBox {
    background-color: #FFFFFF;
    border: 2px solid #808080;
    border-right-color: #FFFFFF;
    border-bottom-color: #FFFFFF;
    padding: 2px 5px;
    min-height: 20px;
}
QComboBox::drop-down {
    border: 1px solid #808080;
    background-color: #D4D0C8;
    width: 18px;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #808080;
    selection-background-color: #0A246A;
}
QCheckBox {
    spacing: 4px;
    color: #000000;
}
QCheckBox::indicator {
    width: 13px;
    height: 13px;
    border: 2px solid #808080;
    border-right-color: #FFFFFF;
    border-bottom-color: #FFFFFF;
    background-color: #FFFFFF;
}
QCheckBox::indicator:checked {
    background-color: #0A246A;
    border-color: #0A246A;
}
QPushButton {
    background-color: #D4D0C8;
    border: 2px solid #808080;
    border-right-color: #FFFFFF;
    border-bottom-color: #FFFFFF;
    padding: 4px 12px;
    color: #000000;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #E4E0D8;
}
QPushButton:pressed {
    border: 2px solid #808080;
    border-left-color: #FFFFFF;
    border-top-color: #FFFFFF;
    border-right-color: #808080;
    border-bottom-color: #808080;
    background-color: #C4C0B8;
}
QPushButton:disabled {
    color: #808080;
    background-color: #CCCCCC;
}
#ripButton {
    background-color: #0A246A;
    color: white;
    font-weight: bold;
    font-size: 12px;
    border: 2px solid #1A449A;
    border-right-color: #0A144A;
    border-bottom-color: #0A144A;
    padding: 8px 24px;
    min-height: 32px;
}
#ripButton:hover {
    background-color: #1A449A;
}
#ripButton:pressed {
    background-color: #081A50;
    border: 2px solid #0A144A;
    border-left-color: #1A449A;
    border-top-color: #1A449A;
}
#ripButton:disabled {
    background-color: #6A7A9A;
    color: #CCCCCC;
}
#logArea {
    background-color: #000000;
    color: #00FF00;
    border: 2px solid #808080;
    border-right-color: #FFFFFF;
    border-bottom-color: #FFFFFF;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 10px;
    padding: 4px;
}
QProgressBar {
    border: 2px solid #808080;
    border-right-color: #FFFFFF;
    border-bottom-color: #FFFFFF;
    background-color: #FFFFFF;
    text-align: center;
    color: #000000;
    height: 18px;
}
QProgressBar::chunk {
    background-color: #0A246A;
}
QStatusBar {
    background-color: #D4D0C8;
    border-top: 2px solid #808080;
}
QLabel {
    color: #000000;
}
#statusLabel {
    color: #000000;
    font-weight: bold;
}
#statusLabel[status="ready"] {
    color: #006400;
}
#statusLabel[status="ripping"] {
    color: #0000FF;
}
#statusLabel[status="error"] {
    color: #FF0000;
}
QTableWidget {
    background-color: #FFFFFF;
    border: 2px solid #808080;
    border-right-color: #FFFFFF;
    border-bottom-color: #FFFFFF;
    gridline-color: #C0C0C0;
}
QTableWidget::item:selected {
    background-color: #0A246A;
    color: white;
}
QHeaderView::section {
    background-color: #D4D0C8;
    border: 1px solid #808080;
    border-right-color: #FFFFFF;
    border-bottom-color: #FFFFFF;
    padding: 3px;
    font-weight: bold;
}
QTabWidget::pane {
    border: 2px solid #808080;
    border-right-color: #FFFFFF;
    border-bottom-color: #FFFFFF;
    background-color: #D4D0C8;
}
QTabBar::tab {
    background-color: #D4D0C8;
    border: 2px solid #808080;
    border-right-color: #FFFFFF;
    border-bottom-color: #FFFFFF;
    padding: 4px 12px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #D4D0C8;
    border-bottom-color: #D4D0C8;
}
QTabBar::tab:hover {
    background-color: #E4E0D8;
}
QSpinBox {
    background-color: #FFFFFF;
    border: 2px solid #808080;
    border-right-color: #FFFFFF;
    border-bottom-color: #FFFFFF;
    padding: 2px;
}
"""


# ============================================================
# 下载工作线程
# ============================================================
class DownloadWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, url: str, output_dir: str, output_format: str,
                 keep_skeleton: bool, keep_morphs: bool, platform: str):
        super().__init__()
        self.url = url
        self.output_dir = output_dir
        self.output_format = output_format
        self.keep_skeleton = keep_skeleton
        self.keep_morphs = keep_morphs
        self.platform = platform
        self._is_running = True

    def run(self):
        try:
            self.status_signal.emit("ripping")
            self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 开始抓取模型...")
            self.log_signal.emit(f"  目标: {self.url}")
            self.log_signal.emit(f"  平台: {self.platform}")
            self.log_signal.emit(f"  格式: {self.output_format}")
            self.log_signal.emit(f"  保留骨骼: {self.keep_skeleton}")
            self.log_signal.emit(f"  保留变形键: {self.keep_morphs}")
            self.log_signal.emit("")

            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            if self.platform in ['sketchfab', 'fab']:
                from downloaders.sketchfab_fab import SketchfabFabDownloader
                downloader = SketchfabFabDownloader(
                    output_dir=output_path,
                    platform=self.platform,
                    headless=True,
                    timeout=120
                )
                downloader.log_callback = self.log_signal.emit
                downloader.progress_callback = self.progress_signal.emit

                result = downloader.download(
                    url=self.url,
                    output_format=self.output_format,
                    keep_skeleton=self.keep_skeleton,
                    keep_morphs=self.keep_morphs
                )
            elif self.platform == 'cgtrader':
                from downloaders.cgtrader import CGTraderDownloader
                downloader = CGTraderDownloader(
                    output_dir=output_path,
                    headless=True,
                    timeout=120
                )
                downloader.log_callback = self.log_signal.emit
                downloader.progress_callback = self.progress_signal.emit

                result = downloader.download(
                    url=self.url,
                    output_format=self.output_format,
                    keep_skeleton=self.keep_skeleton,
                    keep_morphs=self.keep_morphs
                )
            else:
                raise ValueError(f"不支持的平台: {self.platform}")

            if result and os.path.exists(result):
                size_mb = os.path.getsize(result) / 1024 / 1024
                self.log_signal.emit(f"")
                self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 抓取成功!")
                self.log_signal.emit(f"  文件: {result}")
                self.log_signal.emit(f"  大小: {size_mb:.2f} MB")
                self.progress_signal.emit(100)
                self.finished_signal.emit(True, result)
            else:
                raise RuntimeError("下载结果为空")

        except Exception as e:
            self.status_signal.emit("error")
            self.log_signal.emit(f"")
            self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 错误: {str(e)}")
            self.finished_signal.emit(False, str(e))

    def stop(self):
        self._is_running = False
        self.wait(1000)


# ============================================================
# 主窗口 - 3D Ripper Pro 风格
# ============================================================
class RipperMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("3DModelRipper", "Pro")
        self.worker = None
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.setWindowTitle("3D Model Ripper Pro v2.0")
        self.setMinimumSize(900, 650)
        self.resize(950, 700)

        # 设置图标
        icon_path = resource_path("assets/icons/ripper-x_256.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet(RIPPER_STYLE)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== 左侧工具面板 ==========
        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")
        left_panel.setFixedWidth(120)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 8, 4, 8)
        left_layout.setSpacing(4)

        self.tool_buttons = {}
        tools = [
            ("RIP", "抓取", "rip"),
            ("BAT", "批量", "batch"),
            ("SET", "设置", "settings"),
            ("OUT", "输出", "output"),
            ("HLP", "帮助", "help"),
        ]

        for icon, text, key in tools:
            btn = QPushButton(f"{icon}\n{text}")
            btn.setCheckable(True)
            btn.setObjectName(f"tool_{key}")
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(lambda checked, k=key: self.on_tool_clicked(k))
            self.tool_buttons[key] = btn
            left_layout.addWidget(btn)

        left_layout.addStretch()

        version_label = QLabel("v2.0.0")
        version_label.setStyleSheet("color: #888888; font-size: 9px;")
        version_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(version_label)

        main_layout.addWidget(left_panel)

        # ========== 右侧主区域 ==========
        right_area = QWidget()
        right_area.setObjectName("settingsArea")
        right_layout = QVBoxLayout(right_area)
        right_layout.setContentsMargins(12, 8, 12, 8)
        right_layout.setSpacing(8)

        # 标题栏
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 4, 8, 4)

        title_label = QLabel("3D Model Ripper Pro")
        title_label.setObjectName("titleLabel")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        version_label = QLabel("v2.0")
        version_label.setObjectName("versionLabel")
        title_layout.addWidget(version_label)

        right_layout.addWidget(title_bar)

        # 主Tab
        self.main_tabs = QTabWidget()

        # ===== Tab 1: 抓取 =====
        rip_tab = QWidget()
        rip_layout = QVBoxLayout(rip_tab)
        rip_layout.setContentsMargins(8, 8, 8, 8)
        rip_layout.setSpacing(10)

        # URL输入组
        url_group = QGroupBox("目标模型")
        url_layout = QGridLayout(url_group)
        url_layout.setSpacing(6)

        url_label = QLabel("模型页面 URL:")
        url_layout.addWidget(url_label, 0, 0)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://sketchfab.com/3d-models/...")
        self.url_input.setMinimumHeight(24)
        url_layout.addWidget(self.url_input, 0, 1)

        paste_btn = QPushButton("粘贴")
        paste_btn.setFixedWidth(50)
        paste_btn.clicked.connect(self.paste_url)
        url_layout.addWidget(paste_btn, 0, 2)

        detect_btn = QPushButton("检测")
        detect_btn.setFixedWidth(50)
        detect_btn.clicked.connect(self.detect_platform)
        url_layout.addWidget(detect_btn, 0, 3)

        platform_label = QLabel("平台:")
        url_layout.addWidget(platform_label, 1, 0)

        self.platform_combo = QComboBox()
        self.platform_combo.addItems([
            "自动检测",
            "Sketchfab",
            "Fab (Epic Games)",
            "CGTrader",
            "TurboSquid",
            "Free3D"
        ])
        self.platform_combo.setMinimumHeight(22)
        url_layout.addWidget(self.platform_combo, 1, 1)

        self.platform_status = QLabel("未检测")
        self.platform_status.setStyleSheet("color: #808080;")
        url_layout.addWidget(self.platform_status, 1, 2, 1, 2)

        rip_layout.addWidget(url_group)

        # 输出设置组
        output_group = QGroupBox("输出设置")
        output_layout = QGridLayout(output_group)
        output_layout.setSpacing(6)

        output_dir_label = QLabel("输出目录:")
        output_layout.addWidget(output_dir_label, 0, 0)

        self.output_dir_input = QLineEdit()
        default_dir = str(Path.home() / "3D_Ripped_Models")
        self.output_dir_input.setText(default_dir)
        output_layout.addWidget(self.output_dir_input, 0, 1)

        browse_btn = QPushButton("浏览...")
        browse_btn.setFixedWidth(60)
        browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(browse_btn, 0, 2)

        format_label = QLabel("输出格式:")
        output_layout.addWidget(format_label, 1, 0)

        self.format_combo = QComboBox()
        self.format_combo.addItems([
            ".glb  (推荐 - 保留骨骼+变形键)",
            ".gltf (JSON格式 - 保留骨骼+变形键)",
            ".fbx  (Autodesk - 保留骨骼)",
            ".obj  (仅网格 - 丢弃骨骼)"
        ])
        self.format_combo.setMinimumHeight(22)
        self.format_combo.currentIndexChanged.connect(self.on_format_changed)
        output_layout.addWidget(self.format_combo, 1, 1, 1, 2)

        rip_layout.addWidget(output_group)

        # 高级选项组
        adv_group = QGroupBox("高级选项")
        adv_layout = QGridLayout(adv_group)
        adv_layout.setSpacing(6)

        self.keep_skeleton_cb = QCheckBox("保留骨骼数据 (Rig/Skeleton)")
        self.keep_skeleton_cb.setChecked(True)
        adv_layout.addWidget(self.keep_skeleton_cb, 0, 0)

        self.keep_morphs_cb = QCheckBox("保留变形键 (Morph Targets/Blendshapes)")
        self.keep_morphs_cb.setChecked(True)
        adv_layout.addWidget(self.keep_morphs_cb, 0, 1)

        self.keep_textures_cb = QCheckBox("保留贴图/材质")
        self.keep_textures_cb.setChecked(True)
        adv_layout.addWidget(self.keep_textures_cb, 1, 0)

        self.headless_cb = QCheckBox("无头模式 (隐藏浏览器)")
        self.headless_cb.setChecked(True)
        adv_layout.addWidget(self.headless_cb, 1, 1)

        timeout_label = QLabel("超时 (秒):")
        adv_layout.addWidget(timeout_label, 2, 0)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(30, 600)
        self.timeout_spin.setValue(120)
        self.timeout_spin.setSuffix(" 秒")
        adv_layout.addWidget(self.timeout_spin, 2, 1)

        rip_layout.addWidget(adv_group)

        # 警告标签
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: #FF6600; font-weight: bold;")
        self.warning_label.setWordWrap(True)
        rip_layout.addWidget(self.warning_label)

        rip_layout.addStretch()

        # 抓取按钮区域
        btn_area = QHBoxLayout()
        btn_area.addStretch()

        self.rip_button = QPushButton("▶ 开始抓取 (RIP)")
        self.rip_button.setObjectName("ripButton")
        self.rip_button.setFixedSize(180, 40)
        self.rip_button.clicked.connect(self.start_rip)
        btn_area.addWidget(self.rip_button)

        self.stop_button = QPushButton("⏹ 停止")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_rip)
        btn_area.addWidget(self.stop_button)

        btn_area.addStretch()
        rip_layout.addLayout(btn_area)

        self.main_tabs.addTab(rip_tab, "抓取")

        # ===== Tab 2: 批量 =====
        batch_tab = QWidget()
        batch_layout = QVBoxLayout(batch_tab)

        batch_info = QLabel("批量抓取功能 - 从列表文件批量下载模型")
        batch_info.setStyleSheet("color: #808080; padding: 20px;")
        batch_layout.addWidget(batch_info)

        self.batch_table = QTableWidget()
        self.batch_table.setColumnCount(4)
        self.batch_table.setHorizontalHeaderLabels(["URL", "平台", "状态", "大小"])
        self.batch_table.horizontalHeader().setStretchLastSection(True)
        self.batch_table.setMinimumHeight(200)
        batch_layout.addWidget(self.batch_table)

        batch_btn_layout = QHBoxLayout()
        load_list_btn = QPushButton("加载列表文件")
        load_list_btn.clicked.connect(self.load_batch_list)
        batch_btn_layout.addWidget(load_list_btn)

        clear_btn = QPushButton("清空列表")
        clear_btn.clicked.connect(self.clear_batch_list)
        batch_btn_layout.addWidget(clear_btn)

        batch_btn_layout.addStretch()

        self.batch_rip_btn = QPushButton("▶ 批量抓取")
        self.batch_rip_btn.setObjectName("ripButton")
        self.batch_rip_btn.clicked.connect(self.start_batch_rip)
        batch_btn_layout.addWidget(self.batch_rip_btn)

        batch_layout.addLayout(batch_btn_layout)
        batch_layout.addStretch()

        self.main_tabs.addTab(batch_tab, "批量")

        # ===== Tab 3: 日志 =====
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        log_layout.setContentsMargins(4, 4, 4, 4)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("logArea")
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        self.log_text.setMinimumHeight(200)
        log_layout.addWidget(self.log_text)

        log_btn_layout = QHBoxLayout()

        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self.clear_log)
        log_btn_layout.addWidget(clear_log_btn)

        save_log_btn = QPushButton("保存日志")
        save_log_btn.clicked.connect(self.save_log)
        log_btn_layout.addWidget(save_log_btn)

        log_btn_layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        log_btn_layout.addWidget(self.progress_bar)

        log_layout.addLayout(log_btn_layout)

        self.main_tabs.addTab(log_tab, "日志")

        # ===== Tab 4: 帮助 =====
        help_tab = QWidget()
        help_layout = QVBoxLayout(help_tab)
        help_layout.setContentsMargins(12, 12, 12, 12)

        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                color: #000000;
                border: 2px solid #808080;
                border-right-color: #FFFFFF;
                border-bottom-color: #FFFFFF;
                font-family: "Tahoma", sans-serif;
                font-size: 11px;
                padding: 8px;
            }
        """)
        help_text.setHtml("""
        <h2>3D Model Ripper Pro v2.0</h2>
        <p><b>技术原理:</b> 伪装浏览 → 拦截WebGL数据流 → 逆向解析二进制节点 → 提取骨骼与变形键索引 → 重新封装</p>
        <h3>支持平台</h3>
        <ul>
        <li><b>Sketchfab</b> - 拦截浏览器内存中的glTF数据流</li>
        <li><b>Fab (Epic Games)</b> - 拦截WebGL bufferData</li>
        <li><b>CGTrader</b> - 模拟点击下载按钮</li>
        </ul>
        <h3>输出格式</h3>
        <ul>
        <li><b>.glb/.gltf</b> - 推荐，完整保留骨骼和变形键</li>
        <li><b>.fbx</b> - 保留骨骼，兼容性广</li>
        <li><b>.obj</b> - 仅网格，<span style="color:red">强制丢弃骨骼</span></li>
        </ul>
        <h3>使用步骤</h3>
        <ol>
        <li>复制模型页面URL到输入框</li>
        <li>点击"检测"自动识别平台</li>
        <li>选择输出格式和目录</li>
        <li>勾选需要保留的数据类型</li>
        <li>点击"开始抓取"</li>
        </ol>
        <h3>注意事项</h3>
        <p style="color:red">⚠️ 仅下载你有权限访问的免费模型！<br>
        ⚠️ 付费/私有模型无法绕过权限验证。<br>
        ⚠️ 平台会更新反爬策略，如遇失效请更新工具。</p>
        """)
        help_layout.addWidget(help_text)

        self.main_tabs.addTab(help_tab, "帮助")

        right_layout.addWidget(self.main_tabs)

        # 状态栏
        self.status_bar = QStatusBar()
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setProperty("status", "ready")
        self.status_bar.addWidget(self.status_label)

        self.status_bar.addPermanentWidget(QLabel(" | "))
        self.file_count_label = QLabel("已抓取: 0")
        self.status_bar.addPermanentWidget(self.file_count_label)

        self.status_bar.addPermanentWidget(QLabel(" | "))
        self.total_size_label = QLabel("总大小: 0 MB")
        self.status_bar.addPermanentWidget(self.total_size_label)

        self.setStatusBar(self.status_bar)

        main_layout.addWidget(right_area, stretch=1)

        self.tool_buttons["rip"].setChecked(True)

        self.log("3D Model Ripper Pro v2.0 已启动")
        self.log("支持平台: Sketchfab, Fab, CGTrader")
        self.log("技术: 浏览器内存拦截 + WebGL数据流捕获")
        self.log("-" * 50)

    def on_tool_clicked(self, key: str):
        for k, btn in self.tool_buttons.items():
            if k != key:
                btn.setChecked(False)

        if key == "rip":
            self.main_tabs.setCurrentIndex(0)
        elif key == "batch":
            self.main_tabs.setCurrentIndex(1)
        elif key == "output":
            self.main_tabs.setCurrentIndex(2)
        elif key == "help":
            self.main_tabs.setCurrentIndex(3)

    def on_format_changed(self, index: int):
        if index == 3:  # .obj
            self.warning_label.setText("⚠️ 警告: .obj格式不支持骨骼和变形键！将强制丢弃骨骼数据。")
            self.keep_skeleton_cb.setEnabled(False)
            self.keep_morphs_cb.setEnabled(False)
        else:
            self.warning_label.setText("")
            self.keep_skeleton_cb.setEnabled(True)
            self.keep_morphs_cb.setEnabled(True)

    def detect_platform(self):
        url = self.url_input.text().strip()
        if not url:
            self.platform_status.setText("请输入URL")
            self.platform_status.setStyleSheet("color: #FF0000;")
            return

        url_lower = url.lower()
        if 'sketchfab.com' in url_lower or 'skfb.ly' in url_lower:
            platform = "Sketchfab"
            idx = 1
        elif 'fab.com' in url_lower:
            platform = "Fab (Epic Games)"
            idx = 2
        elif 'cgtrader.com' in url_lower:
            platform = "CGTrader"
            idx = 3
        elif 'turbosquid.com' in url_lower:
            platform = "TurboSquid"
            idx = 4
        elif 'free3d.com' in url_lower:
            platform = "Free3D"
            idx = 5
        else:
            platform = "未知"
            idx = 0

        self.platform_combo.setCurrentIndex(idx)
        self.platform_status.setText(f"已识别: {platform}")
        self.platform_status.setStyleSheet("color: #006400; font-weight: bold;")
        self.log(f"平台检测: {platform}")

    def paste_url(self):
        clipboard = QApplication.clipboard()
        self.url_input.setText(clipboard.text())
        self.detect_platform()

    def browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录", 
                                                       self.output_dir_input.text())
        if dir_path:
            self.output_dir_input.setText(dir_path)

    def start_rip(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入模型URL")
            return

        output_dir = self.output_dir_input.text().strip()
        format_idx = self.format_combo.currentIndex()
        formats = ['.glb', '.gltf', '.fbx', '.obj']
        output_format = formats[format_idx]

        keep_skeleton = self.keep_skeleton_cb.isChecked() and format_idx != 3
        keep_morphs = self.keep_morphs_cb.isChecked() and format_idx != 3

        url_lower = url.lower()
        if 'sketchfab' in url_lower:
            platform = 'sketchfab'
        elif 'fab.com' in url_lower:
            platform = 'fab'
        elif 'cgtrader' in url_lower:
            platform = 'cgtrader'
        else:
            platform = 'sketchfab'

        self.rip_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在抓取...")
        self.status_label.setProperty("status", "ripping")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

        self.main_tabs.setCurrentIndex(2)

        self.worker = DownloadWorker(
            url=url,
            output_dir=output_dir,
            output_format=output_format,
            keep_skeleton=keep_skeleton,
            keep_morphs=keep_morphs,
            platform=platform
        )
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.status_signal.connect(self.update_status)
        self.worker.finished_signal.connect(self.on_rip_finished)
        self.worker.start()

    def stop_rip(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.log("用户取消抓取")
            self.on_rip_finished(False, "用户取消")

    def on_rip_finished(self, success: bool, result: str):
        self.rip_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        if success:
            self.status_label.setText("抓取完成")
            self.status_label.setProperty("status", "ready")
            count = int(self.file_count_label.text().split(': ')[1]) + 1
            self.file_count_label.setText(f"已抓取: {count}")

            reply = QMessageBox.question(self, "完成", 
                f"抓取成功!\n文件: {result}\n\n是否打开输出目录?",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                import subprocess
                if sys.platform == 'win32':
                    subprocess.run(['explorer', os.path.dirname(result)])
                elif sys.platform == 'darwin':
                    subprocess.run(['open', os.path.dirname(result)])
                else:
                    subprocess.run(['xdg-open', os.path.dirname(result)])
        else:
            self.status_label.setText("抓取失败")
            self.status_label.setProperty("status", "error")

        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.progress_bar.setValue(100 if success else 0)

    def update_progress(self, value: int):
        self.progress_bar.setValue(value)

    def update_status(self, status: str):
        self.status_label.setProperty("status", status)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def log(self, message: str):
        self.log_text.append(message)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self):
        self.log_text.clear()

    def save_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存日志", "ripper_log.txt", "Text Files (*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())

    def load_batch_list(self):
        path, _ = QFileDialog.getOpenFileName(self, "加载URL列表", "", "Text Files (*.txt)")
        if path:
            with open(path, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            self.batch_table.setRowCount(len(urls))
            for i, url in enumerate(urls):
                self.batch_table.setItem(i, 0, QTableWidgetItem(url))
                self.batch_table.setItem(i, 1, QTableWidgetItem("待检测"))
                self.batch_table.setItem(i, 2, QTableWidgetItem("等待"))
                self.batch_table.setItem(i, 3, QTableWidgetItem("-"))

    def clear_batch_list(self):
        self.batch_table.setRowCount(0)

    def start_batch_rip(self):
        QMessageBox.information(self, "提示", "批量抓取功能开发中...")

    def load_settings(self):
        output_dir = self.settings.value("output_dir", str(Path.home() / "3D_Ripped_Models"))
        self.output_dir_input.setText(output_dir)

    def save_settings(self):
        self.settings.setValue("output_dir", self.output_dir_input.text())

    def closeEvent(self, event):
        self.save_settings()
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    font = QFont("Tahoma", 9)
    app.setFont(font)

    window = RipperMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
