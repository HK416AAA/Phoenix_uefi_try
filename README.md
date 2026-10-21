# uefi-port

可参数化的 UEFI 构建流水线：在 GitHub Actions 上编译 [Mu-Silicium](https://github.com/Project-Silicium/Mu-Silicium)，
产出 `SILICIUM_UEFI.fd` 与 `Mu-<device>.img/.bin`，并做一次固件卷结构校验。

## 现在能做什么

- `workflow_dispatch` 输入设备代号，CI 自动：浅克隆 Mu-Silicium（含子模块）→ `setup_env.sh -p apt` →
  `build_uefi.py -d <device> -r <mode> -m <model> -c` → 校验 FV → 上传 artifact。
- 默认 `giulia`（OnePlus 13R / Ace 5，骁龙 8 Gen 3）只是**用来证明流水线是绿的**，不是目标设备。
- 可选的 QEMU job 只能证明镜像能加载、CPU 开始执行；手机固件没有 `virt` 机器的驱动，跑不出画面。

## 目标设备：Huawei Mate 30 4G（TAS-AL00）

已确认：`bootlock=unlocked`、`verifiedbootstate=orange`、6 GB RAM、`androidboot.hardware=kirin990`。
内核镜像来自 LIO 源码，但板级配置由设备自己的 `dtbo` 分区提供（`dtbo_idx=292`）。

M0 的三个 gate 已过前两个（解锁、未签名镜像可启动）；`fastboot boot` 仍未单独验证。

M0 用到的脚本：

```bash
bash scripts/collect-device.sh              # adb / fastboot 两轮各跑一次
bash scripts/dump-dtb.sh mate30-dtb          # dtb/dtbo 分区 + /proc/device-tree
bash scripts/probe-kernel-source.sh <内核源码>  # 索引驱动与寄存器定义（本地或 CI）
python scripts/bootimg.py stock_boot.img     # 读 kernel_addr / page_size / header_version
python scripts/extract-dtbo.py stock_boot.img -o dtb-out  # DTBO 参考（非 TAS 板级来源）
python scripts/plan-layout.py --boot stock_boot.img --dtb dtb-out/fdt_000060.dtb
python scripts/make-test-bootimg.py stock_boot.img test.img
```

打包与刷入见 [docs/PACKAGING.md](docs/PACKAGING.md)，派生出的设备配置见
[config/tas.toml](config/tas.toml)。

## M1a：点屏 stub

没有可用的串口控制台，第一步先用屏幕验证启动链。`stub/` 是一个裸机 ARM64 载荷：
它伪装成合法的 ARM64 Image，往 logo 帧缓冲 `0x36500000` 写满一个颜色，然后死循环。

`.github/workflows/build-stub.yml` 负责构建，产物是 `stub.bin.gz`。本地打包：

```bash
python scripts/repack-bootimg.py \
  --stock stock_boot.img \
  --kernel stub.bin.gz \
  --out boot-stub.img
fastboot flash boot boot-stub.img
```

预期：屏幕变成纯色，设备挂住。长按电源重启即可恢复；恢复镜像就是 `stock_boot.img`。
屏幕没变化说明 ABL 没有让 panel 继续扫描这个缓冲，下一步换 pstore `0x2f000000`。

内核源码用 `HK416AAA/android_kernel_LIO_kirin990_103`（LIO，不是 TAS；**没有板级 dts**），
分析见 [docs/KERNEL-SOURCE.md](docs/KERNEL-SOURCE.md)。板级地址的取法见
[docs/BOARD-DATA.md](docs/BOARD-DATA.md)。源码索引可以直接跑 `probe-kernel` workflow。

## 现在不能做什么

**麒麟 9010 目前没有公开解锁方案，无法构建。** 麒麟 990 的缺口与推进方式见 [PORTING-KIRIN.md](PORTING-KIRIN.md)：

- Mu-Silicium 的 `Platforms/` 没有 HiSilicon 平台包（只有高通、三星、MTK、Tegra、华硕、LG、联想、摩托罗拉、
  任天堂、Nothing、一加、真我、小米、ZTE）。
- 麒麟 9010 没有公开的 bootloader 解锁方案；麒麟 990 只有部分 5G 机型（P40 / P40 Pro / P40 Pro+）在 2026 年
  出现了基于主板测试点 + 板级固件的永久解锁流程，990 4G 与 Mate 30 Pro 明确不支持。

没有解锁的 bootloader，`fastboot boot` 这一步就不成立，后面的 FV 再正确也加载不了。

## 快速开始

1. 把本目录推到一个 GitHub 仓库（默认分支 `main`）。
2. Actions → `build-uefi` → Run workflow：
   - `device`：Mu-Silicium 代号，必须是 `Resources/Configs/<device>.toml` 里存在的那个
   - `mu_ref`：默认 `main`，建议固定到某个 commit 以便复现
   - `mode`：`DEBUG`（带串口日志，bring-up 用）或 `RELEASE`
   - `model`：多机型设备的索引，单机型填 `0`
   - `qemu`：是否跑加载冒烟
3. 产物：`uefi-<device>-<mode>`，内含 `Mu-<device>[-<model>].img` / `.bin` 和 `SILICIUM_UEFI.fd`。

## 添加一台新设备

Mu-Silicium 的设备由四部分组成，缺一不可：

| 路径 | 内容 |
|---|---|
| `Platforms/<Vendor>/<codename>Pkg/` | 平台 DSC、`DeviceBuild.py`、ACPI、DXE 驱动、板级配置 |
| `Resources/Configs/<codename>.toml` | `uefi_fd` 的 base/size、boot image 参数、boot shim 开关、输出类型 |
| `Resources/DTBs/<codename>.dtb` | 设备树（`append_dtb` 为真时必需） |
| `Status.md` | 设备状态表，`build_active_devices.sh` 按 `**State:** Active` 抓取 |

最省力的路径是复制同 SoC 的现有 `*Pkg`，先改 FD base/size、UFS、GPIO、panel、UART，再逐步补 ACPI。

## 本地/CI 之外的验证

```bash
# Linux 或 WSL
git clone --recursive https://github.com/Project-Silicium/Mu-Silicium.git
cd Mu-Silicium
./setup_env.sh -p apt
python3 build_uefi.py -d giulia -r DEBUG -c
python3 ../uefi-port/scripts/verify-fv.py \
  Build/giuliaPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd
```

真机验证只有一条：解锁 bootloader 后 `fastboot boot Mu-<device>.img`，看串口或屏幕是否出现 UEFI 输出。
CI 无法替代这一步。

## 已知限制

- Mu-Silicium 全量源码约 5 GB，首次 clone 与构建都在分钟级；缓存命中可以显著缩短。
- `DEBUG` 构建体积更大，但 bring-up 阶段必须用 `DEBUG` 才能拿到串口日志。
- 固件卷校验只检查 FV 头与 block map，不检查 PE 入口、驱动是否齐全。
