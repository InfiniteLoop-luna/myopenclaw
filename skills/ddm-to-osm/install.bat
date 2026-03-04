@echo off
REM ddm-to-osm skill 安装脚本 (Windows)

echo 📦 安装 ddm-to-osm skill...
echo.

REM 检查 Python 版本
python --version
echo.

REM 安装依赖
echo 安装依赖...
pip install -r requirements.txt

if %errorlevel% equ 0 (
    echo.
    echo ✅ ddm-to-osm skill 安装成功！
    echo.
    echo 运行测试:
    echo   python test.py
    echo.
    echo 使用方法:
    echo   python convert.py ^<ddm_file^> ^<output_yaml^> [database_name]
    echo.
    echo 示例:
    echo   python convert.py sakila.ddm sakila_osm.yaml sakila
) else (
    echo.
    echo ❌ 安装失败
    echo 请检查错误信息或查看 docs\TROUBLESHOOTING.md
    exit /b 1
)
