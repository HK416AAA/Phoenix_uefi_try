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
- `Library/PstoreSerialPortLib` — pmsg at `0x2fce0000` (ramoops: 0x2fc40000 + record 0x80000 + console 0x20000)
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

## Official kernel Image replacement (charlotte-mainline style)

The stock 9010 boot.img kernel is a Huawei `_ARMd` secure image loaded by the
TEE UEFI `DLaKre`/`DecryptKernel`. A custom kernel is booted by replacing the
kernel field of the stock boot.img with a self-built `Image.gz`.

Official build inputs:

```
Code_Opensource/kernel                      # Huawei HarmonyOS 4.2 source
arch/arm64/configs/merge_charlotte_defconfig
make ARCH=arm64 O=../out merge_charlotte_defconfig
make ARCH=arm64 O=../out -j8
=> out/arch/arm64/boot/Image.gz
```

This tree ships `Resources/merge_charlotte_defconfig`, generated from the
stock `/proc/config.gz` (`MRO-W00` 2024-10-09 build) with:

```
CONFIG_KEXEC=y
CONFIG_KEXEC_FILE=y
CONFIG_DEVMEM=y
# CONFIG_MODULE_SIG is not set
# CONFIG_EFI is not set
# CONFIG_ACE_ENABLE_TVM is not set
```

- `KEXEC_FILE`/`DEVMEM` are for the second stage (LinuxBoot/UEFI payload).
- `EFI` stays off: the TEE UEFI loads the raw Image, not an EFI stub.
- `MODULE_SIG` is off so the custom build does not need Huawei's signing key.
- `ACE_ENABLE_TVM` stays off: the 9010 uses FF-A/HHEE, unlike the 9000S
  charlotte/TAS TVM path.

Scripts:

```
./scripts/build-charlotte-kernel.sh <Code_Opensource/kernel> [out]
./scripts/pack-charlotte-boot.sh <stock-boot.img> <out>/arch/arm64/boot/Image.gz
```

`pack-charlotte-boot.sh` uses `repack-bootimg.py --keep-tail`, preserving the
stock ramdisk, DTB and AVB footer. The TEE UEFI's `hvb`/`DecryptKernel` may
still reject the modified kernel; unlock/decrypt secboot first
(`README_Version.txt`), and keep the image in the stock boot.img layout.

## HHEE on 9010: FF-A, not TVM

Official config:

```
CONFIG_ARM_FFA_TRANSPORT=y
CONFIG_ARM_FFA_SMCCC=y
CONFIG_FFA_SUPPORT=y
CONFIG_UFS_FFA_SUPPORT=y
CONFIG_DPU_FFA_SUPPORT=y
CONFIG_CLOCK_SUPPORT_FFA=y
CONFIG_IP_REGULATOR_SUPPORT_FFA=y
CONFIG_RPMB_FFA_SUPPORT=y
CONFIG_EFUSE_SUPPORT_FFA=y
CONFIG_DDRC_SUPPORT_FFA=y
CONFIG_NPU_FFA_SUPPORT=y
```

`hkip_hhee.h` still defines `HHEE_HVC_ENABLE_TVM 0xC600108A`, but the 9010
`merge_charlotte_defconfig` has `CONFIG_ACE_ENABLE_TVM` **off**, and its
`head.S` does not call `hkip_tvm_enable`. The 9010 HHEE mediation is via
**FF-A** for UFS/DPU/clock/regulator/RPMB, not the 9000S/TAS TVM handshake.

Reference (9000S charlotte early boot):

```
msr  daifset, #0x4        // SError 0xbe000011
...
bl   __cpu_setup
bl   hkip_tvm_enable      // CONFIG_ACE_ENABLE_TVM
b    __primary_switch
```

`hkip_hvc.S` dispatches HHEE HVCs only when `ARM64_HAS_HHEE` is present.

## UEFI/UEFI payload second stage

The UEFI cannot be parasitized in the stock kernel: `KEXEC=n`, `EFI=n`,
`DEVMEM=n`, `MODULE_SIG_FORCE=y`. The custom Image, however, is our build and
can enable `KEXEC_FILE`/`DEVMEM`:

```
stock TEE UEFI
  -> custom Image.gz (boot.img kernel)
  -> initramfs
  -> kexec_file_load(UEFI payload, PE/COFF)
  -> EDK2 UEFI Boot Services
  -> DarwinBoot / UniXNU
```

HHEE/FF-A considerations for the payload:

- The 9010 UFS/DPU/clock/regulator/RPMB are FF-A mediated; the UEFI payload
  needs the corresponding FF-A drivers, not just raw MMIO.
- The fixed framebuffer stays usable: 2800x1840, stride 11200, `x8b8g8r8`
  (logo buffer `0x36AD3850` in the live FDT).
- The keepalive must run in the payload/XNU: V500 `0xfae7c000` and LPM3 IPC
  `0xff870000` (same as charlotte, 24 s timeout).

