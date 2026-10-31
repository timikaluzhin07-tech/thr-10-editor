@echo off
rem Сборка THR10 Editor для Windows: окружение, тесты, PyInstaller, самопроверка.
rem Нужен Python 3.12 (64-bit) из python.org с лаунчером "py".
setlocal
cd /d "%~dp0\.."

if not exist .venv (
    py -3.12 -m venv .venv || goto :error
)
call .venv\Scripts\activate.bat || goto :error
python -m pip install --upgrade pip || goto :error
python -m pip install -r requirements.txt || goto :error

python -m pytest || goto :error
python scripts\build_exe.py || goto :error

echo.
echo Готово: dist\THR10Editor.exe и dist\THR10Probe.exe
exit /b 0

:error
echo.
echo ОШИБКА сборки — смотрите сообщения выше.
exit /b 1
