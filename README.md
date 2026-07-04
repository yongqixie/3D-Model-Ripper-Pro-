# 3D Model Ripper Pro v2.0

![3D Ripper Pro Style](https://img.shields.io/badge/Style-3D%20Ripper%20DX-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)

模仿经典 **3D Ripper DX** 界面风格的3D模型下载工具。

## 界面预览

- 左侧深色工具面板 (仿3D Ripper DX)
- 右侧经典Win32灰色设置区域
- 黑色日志终端 (绿色文字)
- 蓝色状态栏和进度条

## 两种使用方式

### 方式一: 直接运行 Python (开发/调试)

```bash
pip install -r requirements.txt
playwright install chromium
python main.py
```

### 方式二: 打包成 EXE (推荐给用户)

**简单打包 (快速)**:
```bash
cd build_tools
build.bat
```

**高级打包 (UPX压缩，体积更小)**:
```bash
cd build_tools
build_advanced.bat
```

打包完成后，在 `dist/` 目录下找到 `3D_Model_Ripper_Pro.exe`，
双击即可运行，**不需要安装 Python**！

## 手动打包命令

```bash
# 基础打包
pyinstaller --clean --onefile --windowed --icon=assets/icons/ripper-x.ico main.py

# 包含数据文件
pyinstaller --clean --onefile --windowed --icon=assets/icons/ripper-x.ico \
    --add-data "assets/icons;assets/icons" \
    --add-data "downloaders;downloaders" \
    main.py
```

## 技术原理

```
伪装浏览 → 拦截WebGL数据流/模拟点击 → 逆向解析二进制节点 → 提取骨骼与变形键索引 → 重新封装为FBX/glTF
```

## 使用步骤

1. 复制模型页面URL到输入框
2. 点击"检测"自动识别平台
3. 选择输出格式和目录
4. 勾选需要保留的数据类型
5. 点击"开始抓取"

## 支持平台

| 平台 | 技术方式 | 骨骼保留 | 变形键保留 |
|------|---------|---------|-----------|
| Sketchfab | WebGL内存拦截 | ✅ | ✅ |
| Fab (Epic) | WebGL内存拦截 | ✅ | ✅ |
| CGTrader | 模拟点击下载 | ✅ | ✅ |

## 输出格式

- **.glb** - 推荐，完整保留骨骼和变形键
- **.gltf** - JSON格式，同样保留完整数据
- **.fbx** - Autodesk格式，保留骨骼
- **.obj** - ⚠️ 仅网格，丢弃骨骼和变形键

## 注意事项

⚠️ **仅下载你有权限访问的免费模型！**

⚠️ 付费/私有模型无法绕过权限验证

⚠️ 平台会更新反爬策略，如遇失效请更新工具

⚠️ `.obj` 格式会强制丢弃骨骼数据

## 文件说明

```
3D_Model_Ripper_Pro/
├── main.py                          # 主程序 (GUI)
├── downloaders/
│   ├── __init__.py
│   ├── sketchfab_fab.py             # Sketchfab/Fab 下载器
│   └── cgtrader.py                  # CGTrader 下载器
├── assets/
│   └── icons/
│       ├── ripper-x_16.png          # 图标 (16x16)
│       ├── ripper-x_32.png          # 图标 (32x32)
│       ├── ripper-x_48.png          # 图标 (48x48)
│       ├── ripper-x_64.png          # 图标 (64x64)
│       ├── ripper-x_128.png         # 图标 (128x128)
│       ├── ripper-x_256.png         # 图标 (256x256)
│       ├── ripper-x_512.png         # 图标 (512x512)
│       └── ripper-x_1024.png        # 图标 (1024x1024)
├── build_tools/
│   ├── build.bat                    # 简单打包脚本
│   ├── build_advanced.bat           # 高级打包脚本 (UPX压缩)
│   └── 3D_Model_Ripper_Pro.spec     # PyInstaller 配置
├── requirements.txt                 # Python依赖
└── README.md                        # 说明文档
```
