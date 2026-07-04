@echo off
chcp 65001
cls
echo ==========================================
echo   3D Model Ripper Pro - 高级打包
echo ==========================================
echo.

REM 创建虚拟环境
echo [1/7] 创建虚拟环境...
python -m venv venv
venv\Scripts\pip install --upgrade pip

echo [2/7] 安装依赖...
venv\Scripts\pip install pyinstaller playwright pyqt5 requests trimesh numpy pillow

echo [3/7] 安装浏览器...
venv\Scripts\playwright install chromium

echo [4/7] 转换图标...
venv\Scripts\python -c "from PIL import Image; img = Image.open('assets/icons/ripper-x_256.png'); img.save('assets/icons/ripper-x.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"

echo [5/7] 下载 UPX (压缩工具)...
if not exist "upx" (
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/upx/upx/releases/download/v4.2.2/upx-4.2.2-win64.zip' -OutFile 'upx.zip'"
    powershell -Command "Expand-Archive -Path 'upx.zip' -DestinationPath '.' -Force"
    rename "upx-4.2.2-win64" "upx"
    del upx.zip
)

echo [6/7] 开始打包 (UPX压缩)...
venv\Scripts\pyinstaller --clean --onefile --windowed --icon=assets/icons/ripper-x.ico --name "3D_Model_Ripper_Pro" --upx-dir=upx --add-data "assets/icons;assets/icons" --add-data "downloaders;downloaders" main.py

echo [7/7] 清理临时文件...
rd /s /q build
rd /s /q venv

echo.
echo ==========================================
echo   打包完成！
echo   输出: dist\3D_Model_Ripper_Pro.exe
echo ==========================================
pause
