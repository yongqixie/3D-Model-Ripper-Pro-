@echo off
chcp 65001
cls
echo ==========================================
echo   3D Model Ripper Pro - 打包工具
echo ==========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [1/5] 检查依赖...
pip install pyinstaller playwright pyqt5 requests trimesh numpy pillow -q
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo [2/5] 安装浏览器...
playwright install chromium

echo [3/5] 转换图标...
python -c "from PIL import Image; img = Image.open('assets/icons/ripper-x_256.png'); img.save('assets/icons/ripper-x.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"

echo [4/5] 开始打包...
pyinstaller --clean --onefile --windowed --icon=assets/icons/ripper-x.ico --name "3D_Model_Ripper_Pro" --add-data "assets/icons;assets/icons" --add-data "downloaders;downloaders" main.py

echo [5/5] 打包完成！
echo.
echo 输出文件: dist\3D_Model_Ripper_Pro.exe
echo.
pause
