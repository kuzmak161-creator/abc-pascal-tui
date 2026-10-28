[![English](https://img.shields.io/badge/Language-English-green?style=for-the-badge)](/docs/BUILD.md)
[![Русский](https://img.shields.io/badge/Language-Русский-blue?style=for-the-badge)](/docs/BUILD_RU.md)

---

## Інструкція з компіляції PascalABC.NET для Debian

1. Завантажуємо .NET SDK 10:
```bash
curl -sSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel 10.0
```

2. Клонуємо репозиторій:
```bash
git clone https://github.com/pascalabcnet/pascalabcnet
```

3. Переходимо до папки репозиторію:
```bash
cd pascalabcnet
```

4. Компілюємо (з сумісністю для Mono):
```bash
dotnet build pabcnetc.sln -c Release -p:PABCNET_LEGACY_ONLY=true -p:TargetFramework=net472 -o "abc-pascal-tui"
```

---

## Інструкція з компіляції PascalABC.NET для Termux

1. Завантажуємо .NET SDK 10:
```bash
pkg install dotnet-sdk-10.0
```

2. Клонуємо репозиторій:
```bash
git clone https://github.com/pascalabcnet/pascalabcnet
```

3. Переходимо до папки репозиторію:
```bash
cd pascalabcnet
```

4. Компілюємо (з сумісністю для Mono):
```bash
dotnet build pabcnetc.sln -c Release -p:PABCNET_LEGACY_ONLY=true -p:TargetFramework=net472 -o "abc-pascal-tui"
```
