[![Українська](https://img.shields.io/badge/Language-Українська-yellow?style=for-the-badge)](README_UA.md) [![Русский](https://img.shields.io/badge/Language-Русский-blue?style=for-the-badge)](README_RU.md)

---


## DESCRIPTION
abc-pascal-tui is an IDE for Pascal based on the PascalABC.NET compiler, utilizing a Python-based TUI (Text User Interface).

## DOWNLOAD
To download the IDE, you must first install Python, Mono, Git, and the Textual library.

<p align="center">
  <img src="https://github.com/kuzmak161-creator/abc-pascal-tui/blob/main/Ico/screenshot%20one.jpeg" alt="Интерфейс Pascal TUI" width="400">
</p>

<p align="center">
  <img src="https://private-user-images.githubusercontent.com/285278862/593754255-de2eea2e-cbe2-4556-8149-7508e17753b7.jpg?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NzkwNTEyNTQsIm5iZiI6MTc3OTA1MDk1NCwicGF0aCI6Ii8yODUyNzg4NjIvNTkzNzU0MjU1LWRlMmVlYTJlLWNiZTItNDU1Ni04MTQ5LTc1MDhlMTc3NTNiNy5qcGc_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1BS0lBVkNPRFlMU0E1M1BRSzRaQSUyRjIwMjYwNTE3JTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI2MDUxN1QyMDQ5MTRaJlgtQW16LUV4cGlyZXM9MzAwJlgtQW16LVNpZ25hdHVyZT1iMTY5NDZmYWIzNTVjZmJkNzdlMDc0YzQ3OTZiYTZlNGE0ZjA2NWQ5OTE0N2NmYjc5MDU1MTZlNTM1MGRhZWUwJlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCZyZXNwb25zZS1jb250ZW50LXR5cGU9aW1hZ2UlMkZqcGVnIn0.1SIcbI-UnMthAN7KT2s_euBF8jmwKXsZxAO5Mwr5ZSU" alt="Интерфейс в граф окружении" width="400">

Enter these commands if you are downloading in termux:

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

Launch:
```bash
python tui.py
```
commands for installation in Debian (only tested with Arm versions)


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
launch
```bash
python3 tui.py
```

### Updates are released less frequently in official releases.

## License

- **PascalABC.NET Compiler** - GNU Lesser General Public License v3 (LGPL v3) https://github.com/pascalabcnet/pascalabcnet

The interface code (tui.py) is distributed under the terms of the MIT License.
