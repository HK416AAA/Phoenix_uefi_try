# 麒麟 990 / 9010 的 UEFI 移植可行性

> 结论：**现在无法用 Mu-Silicium 构建出能跑的 UEFI。** 不是代码没写，而是前置条件不成立。
> 本文把“缺什么、能不能补、补的代价”列清楚，避免在错误的方向上先写几千行。

## 1. 硬前置：bootloader

Mu-Silicium 的启动方式是 `fastboot boot <img>`：把 BootShim + UEFI FV 当内核塞进 Android boot image，
由设备自己的 ABL 加载到内存。**要求 bootloader 已解锁，且 ABL 接受 `fastboot boot`。**

麒麟平台的现状（2026-10）：

| SoC | 代表机型 | 公开解锁方案 |
|---|---|---|
| 麒麟 990 5G | P40 5G (ANA)、P40 Pro 5G (ELS)、P40 Pro+ 5G (ELSP) | 有：拆机短接 testpoint + 板级固件 + Harmony TP 线，2026-06 起在 XDA 流通；**不是所有机器都成功**，SN 带 `C` 的 P40/Pro 已被修补 |
| 麒麟 990 5G | Mate 30 5G (TAS) | 未验证 |
| 麒麟 990 5G | Mate 30 Pro 5G / RS (LIO) | **明确不支持** |
| 麒麟 990 4G | Mate 30 4G、P40 4G 等 | 无公开方案 |
| 麒麟 9010 | Pura 70 系列 | **无公开方案**；810 及以上平台在社区清单里长期标记为 “no public tool” |

参考：

- XDA：`PERMENANT BOOTLOADER UNLOCK FOR MOST KIRIN 990 5G`（2026-06 发布，2026-10 仍在更新）
- `zenfyrdev/bootloader-unlock-wall-of-shame`：Kirin 810+ / 990+ 条目为 “No public tool (BootROM exploits in development)”

即使拿到 unlock，XDA 帖里也有 P40 Pro 用户报告刷 `boot` 失败（`partition is too small`）后卡在 fastboot。
所以还要单独确认目标机型的 `fastboot boot` 是否可用、能加载多大的镜像。

## 2. Mu-Silicium 没有 HiSilicon 平台包

`Platforms/` 现有厂商：Asus、LG、Lenovo、Motorola、Nintendo、Nothing、OnePlus、Qualcomm、Realme、Samsung、Xiaomi、ZTE。
没有任何 Huawei/HiSilicon 目录，`Silicon/` 下也没有 Kirin 的 SoC 包。

公开代码里唯一能参考的麒麟 UEFI 是 **edk2-platforms 的 HiKey960（麒麟 960 开发板）**：

- 它是标准 EDK2 平台，有 `Platform/Hisilicon/HiKey960`、`Silicon/Hisilicon/Hi3660` 一类的实现
- 但麒麟 960 与 990/9010 的 UFS、PMIC、GPIO、显示、PSCI 都不同，只能借结构，不能直接搬
- 而且 HiKey960 是开发板，bootloader 本身开放；零售手机没有这个前提

## 3. 从零 port 需要补齐的层

| 层 | 具体内容 | 难度 |
|---|---|---|
| 启动 | BootShim 在华为 ABL 下的加载地址、镜像大小上限、`fastboot boot` 行为 | 高（无文档） |
| 内存 | DRAM base/size、TEE/modem/NPU 预留区、FD base/size 不冲突 | 中（可从 kernel dts 推） |
| 中断/CPU | GIC 版本与基址、PSCI method、SMP bring-up、timer 频率 | 中 |
| 存储 | HiSilicon UFS 主机控制器、PHY、时钟、分区表 | 高 |
| 电源 | PMIC（Hi6421/Hi6422 系列）、稳压时序、watchdog | 高 |
| 显示 | DSI 控制器、panel 初始化序列、GOP 帧缓冲 | 中高 |
| 输入 | 触摸 IC（SPI/I2C）、GPIO 中断、SimpleTextIn | 中 |
| 串口 | UART 基址/波特率，或 USB CDC-ACM | 低（但没有它后面都做不了） |
| ACPI | DSDT/SSDT、MADT、GTDT、IORT、PPTT | 高 |
| 固件协议 | GOP、SimpleTextIn、SimpleFS、BlockIO、SerialIO、ACPI、FV2 | 中 |

## 4. 设备内核源码能给你什么

**能：**

- `arch/arm64/boot/dts/hisilicon/` 或 vendor dts：UART、I2C、SPI、GPIO、UFS、PMIC、panel 的寄存器基址与中断号
- defconfig 与驱动源码：时钟树、稳压器、UFS PHY 参数、触摸复位时序
- 分区表与 `cmdline`：`androidboot.*`、slot 布局

**不能：**

- ABL / XLOADER / ATF 的实现与加载地址
- 安全启动链、vbmeta、解锁状态机
- PSCI 固件行为、CPU 进入 EL2/EL1 的约定
- UFS 在 UEFI 阶段（还没有 Linux 驱动模型时）的初始化序列

也就是说：内核源码解决“寄存器在哪”，不解决“固件怎么被加载、怎么在 EL1 之前把硬件点亮”。

## 5. 如果坚持做，里程碑应该这样切

| 阶段 | 目标 | 完成信号 | 前置 |
|---|---|---|---|
| M0 | 确认可解锁、可 `fastboot boot` | `fastboot getvar unlocked` 为 yes，且能 boot 一个自制的 1 MB 镜像 | 拆机短接 + 板级固件 |
| M1 | BootShim 执行 | 串口打印一行自有标记 | UART 可用；FD 加载地址正确 |
| M2 | FV 被加载、进入 UEFI | 串口出现 EDK2 版本号或菜单 | BootShim 跳转正确 |
| M3 | 存储 + 显示 + 输入 | 能读分区、屏幕有输出、按键/触摸有响应 | SoC 包与驱动 |
| M4 | 交给 UniXNU | DarwinBoot 能拿到 ADT 与内核 | M3 全部完成 |

M1 之前不要写 SoC 驱动——因为你还不知道固件会不会被执行。

## 6. 开工前必须采集的信息

- 机型、代号、SoC 具体型号（990 5G / 990 4G / 990E / 9010）
- 解锁状态、解锁方式、是否还能进 fastboot、`fastboot getvar all` 全量输出
- UART 测试点位置与波特率（或是否有 USB 串口）
- 分区表（`by-name` 列表、boot 分区大小）
- 内核源码版本、defconfig、dts 路径
- 屏幕分辨率与 panel 型号
- 触摸 IC 型号与总线
- 是否 A/B、是否有 vbmeta/AVB

## 7. 风险

- 麒麟 9010 在当前公开资料下**没有可行路径**，不建议投入。
- 麒麟 990 5G 的解锁依赖板级固件与硬件短接，失败可能导致设备无法开机。
- 即使解锁，华为 ABL 对非签名镜像的容忍度未知，`fastboot boot` 可能直接被拒绝。
- 从零写一个 Kirin SoC 包是月级工作量，且没有第二个开发者可以对照。

## 8. 更快的替代路径

1. 换一台**已解锁 + Mu-Silicium 已支持**的机器（OnePlus 13R/13、Poco F6/F7、Realme GT Neo6、小米平板 7 Pro 等），
   本仓库的 CI 当天就能出 `.fd` 和 `boot.img`。
2. 如果目标是研究 UniXNU，而不是这台麒麟设备，用上面任意一台跑通 Stage 1–5，再回头评估麒麟。
3. 如果目标是麒麟本身，先只做 M0：确认解锁与 `fastboot boot`，再决定要不要写 M1。
