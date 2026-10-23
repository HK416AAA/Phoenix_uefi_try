# charlotte kernel build (GitHub Actions)

Branch: `charlotte-kernel-build`

Workflow: `.github/workflows/build-charlotte-kernel.yml`

It builds the official Huawei 9010 kernel source with this repository's
`merge_charlotte_defconfig` (stock `config.gz` + KEXEC/KEXEC_FILE/DEVMEM,
MODULE_SIG off, EFI/ACE_ENABLE_TVM off) and publishes `Image.gz`.

## One-time setup

1. Create a GitHub **Release** in this repository and upload:
   - `MRO-W00_HarmonyOS4.2.0_Opensource.tar.gz`
   - optionally the stock `boot.img`
2. Copy the release asset URLs.

## Run

Actions -> `build-charlotte-kernel` -> Run workflow:

- `source_url`: the release asset URL of the source tar
- `stock_boot_url` (optional): the stock boot.img URL

Artifacts:

```
out-kernel/arch/arm64/boot/Image.gz
out-kernel/System.map
out-kernel/.config
out-kernel/build.log
boot-charlotte.img          (if stock_boot_url was provided)
```

## Toolchain

Matches `README_Kernel.txt`:

- `aarch64-linux-android-4.9` (HK416AAA mirror)
- `clang-r353983c` (Android prebuilt, sparse checkout)
- `CROSS_COMPILE=aarch64-linux-android-`, `CC=clang`,
  `CLANG_TRIPLE=aarch64-linux-gnu-`

## After the build

The stock boot.img kernel is a Huawei `_ARMd` secure image loaded by the TEE
UEFI `DLaKre`/`DecryptKernel`. `pack-charlotte-boot.sh` replaces only the
kernel field and preserves the stock ramdisk/DTB/AVB tail.

- Unlock/decrypt secboot first (`README_Version.txt`).
- `fastboot boot boot-charlotte.img` first, then flash if it boots.

## Next stage

The custom kernel has `KEXEC_FILE`/`DEVMEM` enabled, so its initramfs can
`kexec_file_load` an PE/COFF UEFI payload (EDK2/LinuxBoot), giving UEFI Boot
Services for DarwinBoot/UniXNU.

9010 HHEE is FF-A mediated (`CONFIG_FFA_SUPPORT`, `UFS_FFA`, `DPU_FFA`,
`CLOCK_SUPPORT_FFA`, `IP_REGULATOR_FFA`, `RPMB_FFA`); the UEFI payload and XNU
must use FF-A rather than raw MMIO for UFS/DPU/clock. The V500/LPM3 keepalive
(V500 `0xfae7c000`, IPC `0xff870000`) must keep running in the payload/XNU.
