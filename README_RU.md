[![English](https://img.shields.io/badge/Language-English-red?style=for-the-badge)](README.md) [![Українська](https://img.shields.io/badge/Language-Українська-yellow?style=for-the-badge)](README_UA.md)

## ОПИСАНИЕ 
abc-pascal - это IDE для Паскаля, основанная на компиляторе PascalABC.NET, но использующий TUI-интерфейс на Python.
## скачивание 
Для скачивания IDE необходимо сначала установить Python, Mono, Git и библиотеку Textual.

<p align="center">
  <img src="https://github.com/kuzmak161-creator/abc-pascal-tui/blob/main/Ico/screenshot%20one.jpeg" alt="Интерфейс Pascal TUI" width="400">
</p>

<p align="center">
  <img src="https://github.com/kuzmak161-creator/abc-pascal-tui/blob/main/Ico/screenshot%20two.jpg" alt="Интерфейс в граф окружении" width="400">
команды для установки в termux:


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
```bash
git clone https://github.com/kuzmak161-creator/abc-pascal-tui
```

```bash
cd abc-pascal-tui
```

Запускаем
```bash
python tui.py
```

команды для установки дебиан (проверено только на arm версии)


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
```bash
git clone https://github.com/kuzmak161-creator/abc-pascal-tui.git
```
```bash
cd abc-pascal-tui
```
запуск 
```bash
python3 tui.py
```

### в релизах более редко выходят обновления.

## Лицензия

- **Компилятор PascalABC.NET** - GNU Lesser General Public License v3 (LGPL v3) https://github.com/pascalabcnet/pascalabcnet

Код интерфейса (tui.py) распространяется на условиях MIT License.
