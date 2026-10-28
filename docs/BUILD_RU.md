[![Українська](https://img.shields.io/badge/Language-Українська-yellow?style=for-the-badge)](/docs/BUILD_UA.md) 
[![English](https://img.shields.io/badge/Language-English-green?style=for-the-badge)](/docs/BUILD.md)

---

## Инструкция по компиляции PascalABC.NET для Debian

1. Скачиваем .NET SDK 10:
```bash
curl -sSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel 10.0
```

2. Клонируем репозиторий:
```bash
git clone https://github.com/pascalabcnet/pascalabcnet
```

3. Переходим в папку репозитория:
```bash
cd pascalabcnet
```

4. Компилируем (с совместимостью для Mono):
```bash
dotnet build pabcnetc.sln -c Release -p:PABCNET_LEGACY_ONLY=true -p:TargetFramework=net472 -o "abc-pascal-tui"
```

---

## Инструкция по компиляции PascalABC.NET для Termux

1. Скачиваем .NET SDK 10:
```bash
pkg install dotnet-sdk-10.0
```

2. Клонируем репозиторий:
```bash
git clone https://github.com/pascalabcnet/pascalabcnet
```

3. Переходим в папку репозитория:
```bash
cd pascalabcnet
```

4. Компилируем (с совместимостью для Mono):
```bash
dotnet build pabcnetc.sln -c Release -p:PABCNET_LEGACY_ONLY=true -p:TargetFramework=net472 -o "abc-pascal-tui"
```