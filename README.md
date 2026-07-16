[![Українська](https://img.shields.io/badge/Language-Українська-yellow?style=for-the-badge)](README_UA.md) [![Русский](https://img.shields.io/badge/Language-Русский-blue?style=for-the-badge)](README_RU.md)
---
![Logo](logo.svg)

## DESCRIPTION
abc-pascal-tui is an IDE for Pascal based on the PascalABC.NET compiler, utilizing a Python-based TUI (Text User Interface).

## REQUIREMENTS
Before installing the IDE, ensure you have Python, Mono, Git, and the Textual library installed. DotNet is not required yet (it is needed for running binaries that do not work correctly under Mono).

<p align="center">
  <img src="https://github.com/kuzmak161-creator/abc-pascal-tui/blob/main/Ico/screenshot%20one.jpeg" alt="Pascal TUI Interface" width="400">
</p>

<p align="center">
  <img src="https://github.com/kuzmak161-creator/abc-pascal-tui/blob/main/Ico/screenshot%20two.jpg" alt="Interface in a graphical environment" width="400">
</p>

# Instructions for Termux

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

(It is advisable to install DotNet, but it is not required.)

```bash
pkg install dotnet-runtime-8.0
```

```bash
git clone https://github.com/kuzmak161-creator/abc-pascal-tui
```

```bash
cd abc-pascal-tui
```

Installation

After cloning, run the installer from the root of the repository:

```bash
bash install.sh
```

The script will ask you to select a language (English / Русский / Українська), then:

· Copy all project files (including the tui script) to /usr/local/share/abc-pascal-tui (or $PREFIX/share/abc-pascal-tui in Termux if $PREFIX is set).
· Create the pascal-tui command in /usr/local/bin (or $PREFIX/bin) that runs the installed tui script.
· Delete itself after successful installation.

After installation, you can run the IDE from anywhere using the command:

```bash
pascal-tui
```

Settings will be saved in:

```
~/.config/abc-pascal-tui/settings.json
```

Instructions for Debian

(tested only on Arm versions)

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

(It is advisable to install DotNet, but it is not required.)

```bash
sudo apt install dotnet-runtime-8.0
```

```bash
git clone https://github.com/kuzmak161-creator/abc-pascal-tui.git
```

```bash
cd abc-pascal-tui
```

Run the installer:

```bash
bash install.sh
```

---

Command to update the IDE folder:

```bash
cd ~/abc-pascal-tui && git pull
```

```bash
bash install.sh
```

Updates are released less frequently in official releases.

License

· PascalABC.NET Compiler — GNU Lesser General Public License v3 (LGPL v3) https://github.com/pascalabcnet/pascalabcnet

The interface code (tui) is distributed under the terms of the MIT License.
