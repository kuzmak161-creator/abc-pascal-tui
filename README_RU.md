[![English](https://img.shields.io/badge/Language-English-red?style=for-the-badge)](README.md) [![Українська](https://img.shields.io/badge/Language-Українська-yellow?style=for-the-badge)](README_UA.md)

---

## ОПИСАНИЕ

abc-pascal-tui — это IDE для Паскаля, основанная на компиляторе PascalABC.NET, использующая TUI-интерфейс на Python.

## СКАЧИВАНИЕ

Для скачивания IDE необходимо сначала установить Python, Mono, Git и библиотеку Textual. DotNet пока не обязателен (нужен для запуска бинарников, которые нормально не работают на Mono).

<p align="center">
  <img src="https://github.com/kuzmak161-creator/abc-pascal-tui/blob/main/Ico/screenshot%20one.jpeg" alt="Интерфейс Pascal TUI" width="400">
</p>

<p align="center">
  <img src="https://github.com/kuzmak161-creator/abc-pascal-tui/blob/main/Ico/screenshot%20two.jpg" alt="Интерфейс в граф окружении" width="400">
</p>

---

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

(Желательно установить DotNet, но не обязательно.)
```bash
pkg install dotnet-runtime-8.0
```

```bash
git clone https://github.com/kuzmak161-creator/abc-pascal-tui
```

```bash
cd abc-pascal-tui
```

Запуск:
```bash
python tui.py
```

---

# Инструкция для Debian

(Проверено только на ARM-версии.)

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

(Желательно установить DotNet, но не обязательно.)
```bash
sudo apt install dotnet-runtime-8.0
```

```bash
git clone https://github.com/kuzmak161-creator/abc-pascal-tui.git
```

```bash
cd abc-pascal-tui
```

Запуск:
```bash
python3 tui.py
```

---

### Команда для обновления папки с IDE

(Удаляет все файлы в папке projects.)
```bash
cd ~/abc-pascal-tui && git pull
```

### В официальных релизах обновления выходят реже.

---

## Лицензия

- **Компилятор PascalABC.NET** — GNU Lesser General Public License v3 (LGPL v3) https://github.com/pascalabcnet/pascalabcnet

Код интерфейса (tui.py) распространяется на условиях MIT License.
