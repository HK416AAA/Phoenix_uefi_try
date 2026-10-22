# charlotte / Kirin 9010 — UniXNU UEFI bring-up

Branch: `charlotte-9010-unixnu`

Base: `UniXNU/uefi-sheng` (Mu-Silicium fork) + `UniXNU/UniXNU` (`package/`).

This branch starts a **Kirin 9010 (charlotte)** port. It is a scaffolding
port, not a flashable image yet. The platform package is derived from the
working TAS Mu-Silicium skeleton and the 9000S charlotte DTS.

## Hardware baseline (9000S charlotte DTS, used until a 9010 DTS is supplied)

| Item | Value |
|---|---|
| PSCI | `method = "hvc"`, CPU_SUSPEND `0xc4000001`, CPU_OFF `0x84000002` |
| GIC | GICD `0xff000000`, GICR `0xff040000` + `0x180000` |
| UART | `0xffb82000` (serial0, 115200) |
| UFS | `0xfa500000` (HCI), `0xfa400000` (PHY/ctrl) |
| HHEE | `0x113c0000` + `0x800000` |
| DP DHCP | `0x11340000` + `0x80000` |
| pstore | `0x2fc40000` + `0x100000` |
| logo / FB | `0x34380000`, `0x7080000`, 1840x2800, stride 7360, `x8b8g8r8` |
| DPU | `0xe8800000` |
| RAM | `0x00400000 + 0xdfc00000`, `0x100000000 + 0x100000000`, `0x800000000 + 0x20000000` |

## Current scaffold

- `charlotte.dsc/fdf`, `DeviceBuild.py`, `Include/*`
- `Library/MemoryMapLib` — FD `0x80000000`/3 MiB, stack `0x80300000`, heap `0x80400000`/64 MiB
- `Library/PstoreSerialPortLib` — pmsg at `0x2fd20000`
- `Drivers/FiqMaskDxe` — SError + FIQ mask only (no TAS IOMCU/SMC)
- `UniXNU` components wired into DSC/FDF:
  - `UniXNUPkg/Application/UniXNU/UniXNU.inf`
  - `UniXNUPkg/Driver/UniXNUDxe/UniXNUDxe.inf`
  - `DarwinBootPkg/Driver/DarwinBoot.inf`
  - `UniXNULib|UniXNUPkg/Library/UniXNULib/UniXNULib.inf`

## TODO

1. **9010 device tree / boot image** — replace the 9000S approximates with the
   real TGR/9010 DTS and the stock boot image header.
2. **Stock UEFI vendor import** — the sheng port imports 53 vendor modules
   (UFS, display, PMIC, clocks) from the stock UEFI into `Binaries/<device>`.
   For charlotte, extract the stock 9010 UEFI and import the same way.
3. **Display** — `SimpleFbDxe` on the logo buffer first; stock DisplayDxe only
   after the vendor PMIC/clock/DSI stack is imported.
4. **UART** — `0xffb82000` is `hisilicon,uart`/uart_v500, not PL011; pstore is
   the only console until a uart_v500 SerialPortLib exists.
5. **Secure watchdog/FIQ** — 9010 IOMCU/SP805 is different from TAS; do not
   reuse the TAS `0xfa87c000` access path.
6. **ABL container** — the branch assumes `requires_kernel_header` and a v2
   boot image; verify the actual charlotte ABL header/offset.

## Build (scaffold)

The intended workflow clones:

- `UniXNU/uefi-sheng` (branch `sheng`) → `uefi-sheng/`
- `UniXNU/UniXNU` (branch `main`) → `UniXNU/`

then overlays this package to `uefi-sheng/Platforms/Huawei/charlottePkg` and
`config/charlotte.toml` to `uefi-sheng/Resources/Configs/charlotte.toml`.

`UNIXNU_ROOT` must point at the `UniXNU` checkout so `DeviceBuild.py` can add
`UniXNU/package` to the package path.

The first build is expected to need the vendor module import before it can
produce a bootable image.
