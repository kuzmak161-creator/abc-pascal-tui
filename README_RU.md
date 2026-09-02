[![Українська](https://img.shields.io/badge/Language-Українська-yellow?style=for-the-badge)](README_UA.md) [![English](https://img.shields.io/badge/Language-English-green?style=for-the-badge)](README.md)

---
![Logo](logo.svg)

## ОПИСАНИЕ
abc-pascal-tui — это IDE для Pascal на основе компилятора PascalABC.NET, использующая TUI (текстовый интерфейс) на Python.

## ТРЕБОВАНИЯ
Перед установкой IDE убедитесь, что у вас установлены Python, Mono, Git и библиотека Textual. DotNet не обязателен (он нужен для запуска бинарников, которые некорректно работают под Mono).

<p align="center">
  <img src="https://github.com/kuzmak161-creator/abc-pascal-tui/blob/main/Ico/screenshot%20one.jpeg" alt="Интерфейс Pascal TUI" width="400">
<p>

<p align="center">
  <img src="https://github.com/kuzmak161-creator/abc-pascal-tui/blob/main/Ico/screenshot%20two.jpg" alt="Интерфейс в граф окружении" width="400">
<p>

# Инструкция для Termux

```bash
pkg install mono -y
```

```bash
pkg install python -y
```

```bash
pkg install git -y
```

```bash
pip install textual
```
(Желательно установить DotNet, но это не обязательно.)
```bash
pkg install dotnet-runtime-8.0
```

```bash
git clone https://github.com/kuzmak161-creator/abc-pascal-tui
```

```bash
cd abc-pascal-tui
```

## Установка

После клонирования запустите установщик из корня репозитория:

```bash
bash install.sh
```

Скрипт попросит выбрать язык (English / Русский / Українська), после чего:
- скопирует все файлы проекта (включая скрипт `tui`) в `/usr/local/share/abc-pascal-tui` (или `$PREFIX/share/abc-pascal-tui` в Termux, если задана переменная `$PREFIX`),
- создаст команду `pascal-tui` в `/usr/local/bin` (или `$PREFIX/bin`), которая запускает установленный скрипт `tui`,
- удалит себя после успешной установки.

После установки вы сможете запускать IDE из любого места командой:

```bash
pascal-tui
```

Настройки будут сохраняться в:
```
~/.config/abc-pascal-tui/settings.json
```

# Инструкция для Debian
(протестировано только на Arm-версиях)


```bash
sudo apt install mono-complete 
```
```bash
sudo apt install git -y
```
```bash
sudo apt install python3 -y
```
```bash
pip3 install textual
```
(Желательно установить DotNet, но это не обязательно.)
```bash
sudo apt install dotnet-runtime-8.0
```

```bash
git clone https://github.com/kuzmak161-creator/abc-pascal-tui.git
```
```bash
cd abc-pascal-tui
```

Запустите установщик:
```bash
bash install.sh
```
---
### Команда для обновления папки с IDE.
```bash
cd ~/abc-pascal-tui && git pull
```
```ash
bash install.sh
```

### Обновления в официальных релизах выходят реже.

## Лицензия

- **Компилятор PascalABC.NET** — GNU Lesser General Public License v3 (LGPL v3) https://github.com/pascalabcnet/pascalabcnet

Код интерфейса (tui) распространяется на условиях лицензии MIT.

