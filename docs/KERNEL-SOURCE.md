# 麒麟 990 内核源码分析

对象：`HK416AAA/android_kernel_LIO_kirin990_103`（fork 自 `wutaijieing/android_kernel_LIO_kirin990_103`）

## 1. 仓库事实

| 项 | 值 |
|---|---|
| 上游描述 | `LIO-LGRP1_HarmonyOS103.0_opensource` |
| 对应软件版本 | 2022-12-28 |
| 默认分支 | `main` |
| 当前 HEAD | `2f71c5e433024c76412bab655e6ff54b3e656ca8`（2024-08-09，KernelSU 提交） |
| 体积 | 约 247 MB |
| 构建目标 | `arch/arm64/boot/Image.gz` + 各目录 `.ko` |
| defconfig | `merge_kirin990_defconfig` |
| 工具链 | `aarch64-linux-android-4.9` + `clang-r353983c` |
| 附加 | KernelSU 子模块（`wutaijieing/KernelSU`，`huawei` 分支） |

## 2. 两个必须先接受的限制

### 2.1 它是 LIO，不是 TAS

LIO = Mate 30 Pro 系列（LIO-AL00 4G / LIO-AN00 5G）与 Mate 30 RS；
TAS = Mate 30 系列（TAS-AL00 4G / TAS-AN00 5G）。两者同属麒麟 990 平台，但：

- SoC 级驱动（UFS、PMIC、GPIO、DSI、时钟）基本通用
- 板级差异（panel、触摸、PMIC 通道、GPIO 分配、分区布局）不通用

拿 LIO 源码给 TAS 用，只能取“SoC 怎么做”，不能取“这块板怎么接”。

### 2.2 没有麒麟 990 的板级设备树

`arch/arm64/boot/dts/hisilicon/` 里只有：

- `hi3660`（麒麟 960 / HiKey960）
- `hi3670`（麒麟 970 / HiKey970）
- `hi6220`（麒麟 620 / HiKey）
- `hi3798cv200`、`hip05/06/07`（服务器/机顶盒）

`arch/arm64/boot/dts/Makefile` 也只挂了这些目录，没有 `huawei`，没有 `hi3690`，`hisilicon/Makefile` 只编 7 个开发板 dtb。

**结论：内存布局、UART 基址、UFS 控制器、PMIC、GPIO、ramoops，这些板级信息不在这份源码里。**

### 2.3 实测：LIO 内核可在 TAS-AL00 上启动

已确认：这份源码编出的 `Image.gz` 在 **TAS-AL00（Mate 30 4G，麒麟 990 4G）** 上正常开机，功能无异常。

这条实测把两件事同时确定了：

- 内核镜像与板级解耦，同一份内核可以跨 990 4G / 5G、跨 TAS / LIO 启动
- 板级配置由 bootloader 从 `dtb` / `dtbo` 分区加载并在启动时打补丁

所以它反过来证明了 2.2 的结论：**UEFI 的地址表必须从设备 DTB 取，不能从这份源码推。**
具体提取方法见 [BOARD-DATA.md](BOARD-DATA.md)。

## 3. 从这份源码能拿到什么

| 需要的东西 | 在这份源码里的位置 | 可用性 |
|---|---|---|
| UFS 主机控制器寄存器与初始化序列 | `drivers/` 与 `platform_source/` 下的 `*ufs*` | 高 |
| PMIC / 稳压器时序 | `*pmic*`、`regulator` 相关 | 高 |
| GPIO 控制器与 pinctrl 写法 | `*gpio*`、`pinctrl` | 高 |
| DSI / 显示控制器 | `platform_source/display`、`*dsi*` | 中高 |
| Mali GPU 电源/时钟序列 | `platform_source/maligpu` | 中 |
| 中断控制器与 PSCI 调用方式 | `drivers/irqchip`、`firmware/psci` | 高 |
| 启用了哪些控制器 | `merge_kirin990_defconfig`（约 200 KB） | 高 |
| 板级地址与内存映射 | 无 | **缺失** |
| ABL / ATF / 安全启动 | 无 | **缺失** |

## 4. 板级信息从哪里来

优先级从高到低：

1. **设备自己的 `dtb` / `dtbo` 分区**（最权威，和当前固件完全匹配）
2. `/proc/device-tree`（运行时视图，可交叉验证）
3. `adb shell cat /proc/iomem`（物理内存窗口）
4. 官方固件包里的 `dtbo.img`

用 `scripts/dump-dtb.sh` 一次拿全：

```bash
bash scripts/dump-dtb.sh mate30-dtb
```

产出：

- `dtb.img` / `dtbo.img`
- 反编译后的 `dtb.dts`、`dtbo/*.dts`
- `device-tree-regs.txt`（`/proc/device-tree` 里所有 `reg` 的十六进制）
- `dtbo` 若被 `mkdtimg` 拆开，会得到每个 overlay 的 dts

然后在 dts 里找这些节点：

```bash
grep -nE 'memory@|reserved-memory|ramoops|serial@|ufs|hisi,ufs|pmic|gpio@|dsi|psci' dtb.dts
```

## 5. 在 CI 上跑源码索引

不用本地拉 247 MB：

```bash
# 本地
bash scripts/probe-kernel-source.sh /path/to/android_kernel_LIO_kirin990_103 kernel-probe
```

或者直接跑 `.github/workflows/probe-kernel.yml`（默认固定到 `2f71c5e...`），
产物 `kernel-probe` 里有：

- `summary.txt`：内核版本、dts 数量、Kirin dts 命中数、defconfig 列表
- `kirin-dts.txt`：预期为空，为空就说明必须走 dtb 分区
- `related-files.txt`：UFS/PMIC/GPIO/DSI 相关文件索引
- `register-bases.txt`：`*_BASE` 形式的寄存器定义

## 6. 构建（仅用于确认源码可用）

```bash
export CROSS_COMPILE=aarch64-linux-android-
mkdir -p ../out
make ARCH=arm64 O=../out merge_kirin990_defconfig
make ARCH=arm64 O=../out -j8
# 产物：../out/arch/arm64/boot/Image.gz
```

这份源码“已验证可用”指的是能编出 `Image.gz` 并启动，不代表它包含 UEFI 需要的信息。
UEFI 阶段不跑 Linux，只用它查寄存器和初始化顺序。
