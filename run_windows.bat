@echo off
chcp 65001 >nul
title Playerok Vortex
setlocal enabledelayedexpansion

:: ==========================================================
::   Playerok Vortex — запуск на Windows (локальный ПК)
::   Канал: @Vortexplayrock | Юз: @Iucdip
::
::   Бот работает как обычный процесс на твоём компьютере —
::   использует ресурсы (CPU/RAM/сеть) именно этого ПК, поэтому
::   компьютер должен быть включён и подключён к интернету всё
::   время, пока бот должен работать. Для работы 24/7 либо не
::   выключай ПК, либо запускай бота на хостинге через main.py
::   (см. install.sh / README на Linux-сервере).
:: ==========================================================

cd /d "%~dp0"

echo.
echo   ================================
echo     PLAYEROK VORTEX - Windows launcher
echo   ================================
echo.

:: ---- Проверка Python ----
where python >nul 2>nul
if errorlevel 1 (
    echo [!] Python не найден в PATH.
    echo     Скачай и установи Python 3.10+ с https://www.python.org/downloads/
    echo     При установке ОБЯЗАТЕЛЬНО поставь галочку "Add Python to PATH".
    pause
    exit /b 1
)

:: ---- Виртуальное окружение ----
if not exist ".venv\Scripts\python.exe" (
    echo [*] Создаю виртуальное окружение...
    python -m venv .venv
    if errorlevel 1 (
        echo [!] Не удалось создать venv. Проверь установку Python.
        pause
        exit /b 1
    )
)

set "PY=.venv\Scripts\python.exe"
set "PIP=.venv\Scripts\pip.exe"

:: ---- Зависимости (ставим один раз, дальше пропускаем для быстрого старта) ----
if not exist ".venv\installed.ok" (
    echo [*] Устанавливаю зависимости, это займёт немного времени...
    "%PIP%" install --upgrade pip -q
    "%PIP%" install -q -r requirements.txt
    if errorlevel 1 (
        echo [!] Ошибка установки зависимостей. Смотри текст выше.
        pause
        exit /b 1
    )
    echo ok > ".venv\installed.ok"
    echo [+] Зависимости установлены.
)

if not exist "logs" mkdir logs
if not exist "data" mkdir data

:: ---- Какой конфиг использовать ----
set "CONFIG=config.yaml"
if not "%~1"=="" set "CONFIG=%~1"

echo.
echo [*] Конфиг: %CONFIG%
echo [*] Если он не заполнен — бот сам спросит недостающие данные прямо здесь, в этом окне.
echo.

:: ---- Приоритет процесса ВЫШЕ обычного, чтобы бот не "тормозил" на слабом ПК ----
:: (не realtime, чтобы не подвесить систему; просто "above normal")
echo [*] Запускаю Playerok Vortex...
echo     Не закрывай это окно, пока бот должен работать.
echo     Для остановки — просто закрой окно или нажми Ctrl+C.
echo.

start "Playerok Vortex" /ABOVENORMAL /WAIT "%PY%" main.py "%CONFIG%"

echo.
echo [!] Playerok Vortex остановлен.
pause
