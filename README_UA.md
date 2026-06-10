[![English](https://img.shields.io/badge/Language-English-red?style=for-the-badge)](README.md) [![Русский](https://img.shields.io/badge/Language-Русский-blue?style=for-the-badge)](README_RU.md)

## опис 
abc-pascal-tui-termux - це IDE для Паскаля, зароблений на компіляторі PascalABC.NET, але використовує TUI-інтерфейс на Python.
## завантаження 
Для завантаження IDE необхідно встановить Python, Mono, Git й библіотеку Textual.

<p align="center">
  <img src="https://github.com/kuzmak161-creator/abc-pascal-tui/blob/main/Ico/screenshot%20one.jpeg" alt="Интерфейс Pascal TUI" width="400">
</p>

<p align="center">
  <img src="https://github.com/kuzmak161-creator/abc-pascal-tui/blob/main/Ico/screenshot%20two.jpg" alt="Интерфейс в граф окружении" width="400">

команди для встановлення у termux:


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

запуск 
```bash
python tui.py
```

команди для встановлення у Debian (перевірено тільки на arm версії)

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

### в релизах більш рідко виходять оновлення.

## ліцензія 

- **компілятор PascalABC.NET** - GNU Lesser General Public License v3 (LGPL v3) https://github.com/pascalabcnet/pascalabcnet

Код інтерфейсу (tui.py) поширюється на умовах MIT License.
