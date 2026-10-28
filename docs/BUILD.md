[![Українська](https://img.shields.io/badge/Language-Українська-yellow?style=for-the-badge)](/docs/BUILD_UA.md)
[![Русский](https://img.shields.io/badge/Language-Русский-blue?style=for-the-badge)](/docs/BUILD_RU.md)

---

## Instructions for compiling PascalABC.NET on Debian

1. Download .NET SDK 10:
```bash
curl -sSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel 10.0
```

2. Clone the repository:
```bash
git clone https://github.com/pascalabcnet/pascalabcnet
```

3. Navigate to the repository folder:
```bash
cd pascalabcnet
```

4. Compile (with Mono compatibility):
```bash
dotnet build pabcnetc.sln -c Release -p:PABCNET_LEGACY_ONLY=true -p:TargetFramework=net472 -o "abc-pascal-tui"
```

---

## Instructions for compiling PascalABC.NET on Termux

1. Download .NET SDK 10:
```bash
pkg install dotnet-sdk-10.0
```

2. Clone the repository:
```bash
git clone https://github.com/pascalabcnet/pascalabcnet
```

3. Navigate to the repository folder:
```bash
cd pascalabcnet
```

4. Compile (with Mono compatibility):
```bash
dotnet build pabcnetc.sln -c Release -p:PABCNET_LEGACY_ONLY=true -p:TargetFramework=net472 -o "abc-pascal-tui"
```
```
