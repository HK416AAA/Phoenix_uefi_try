# TAS-AL00 DTBO 分析（overlay 292）

`dtbo.img` 是 Huawei 的 DTBO 表：

- magic `0xd7b7ab1e`，大端
- 330 个 entry，每个 entry 是 **gzip 压缩的 FDT**
- entry 292 = `androidboot.dtbo_idx=292` 选中的 TAS 板级 overlay

## 面板

| 节点 | 值 |
|---|---|
| `lcd_kit_taurus_samsung_ea8079` | `SAMSUNG_EA8079 6.62" CMD TFT 1080 x 2340` |
| `lcd_kit_taurus_visi_rm692c9_tas` | `VISI_RM692C9 6.62" CMD TFT 1080 x 2340` |
| 分辨率 | 1080 × 2340 |
| MIPI lanes | 3 |
| `panel-pxl-clk` | `0xaf` |
| `mipi-dsi-bit-clk` | `0x202` |
| `lcd_panel_type` | `gpio_id = <0xf6 0x0e>`，`product_id = 0x7d1`（2001）→ Samsung EA8079 |

bootloader 日志里的 `product_id = 2001` 与 fragment@202 对上，本机是 **Samsung EA8079**。

## UART

overlay 把两个 PL011 从 disabled 改成 okay：

| 节点 | 地址 | IRQ | clock | 用途 |
|---|---|---|---|---|
| `uart@fa054000` | `0xfa054000` | 74 | `clk_uart0_fac` | **UART0，最可能是调试口** |
| `uart@fa041000` | `0xfa041000` | 77 | `clk_uart4` | HI1105 GPS，4 Mbaud（dmesg 里 ttyAMA4） |

之前只查了 `ttyS0`，没有查 `ttyAMA*`。`fa054000` 是 PL011，内核很可能注册成 `ttyAMA0`。

## IOMCU / 看门狗

| 节点 | 地址 | 说明 |
|---|---|---|
| `hisilicon,iomcuctrl` | `0xfa87e000` | IOMCU 控制寄存器 |
| `hisilicon,iomcu-watchdog` | `0xfa87c000` | **LPM3 24 秒复位的来源** |
| `hisilicon,sochifi-watchdog` | IRQ 213 | Wi-Fi 看门狗 |

DFX 里的 `reboot_type 0x46 (LPM3_S_LPMCURST)` 就是 `iomcu-watchdog` 触发的。UEFI 要么喂它，要么在早期关掉它。

## 其他

- 触摸：`tp,goodix` 和 `tp,synaptics` 都 status okay，按 `gpio_id`/`sensor_type` 选择
- PMIC：`pmic@0` + 多路 LDO（`ldo12/22/34/38` 等）
- 基带/Wi-Fi：`HI1105`（PCIe）
- 基 DTB 的 `psci` 在 LIO 版本里写的是 `smc`，但 TAS 运行时 `/proc/device-tree/psci/method` 是 **`hvc`**；以运行时为准

## 与 charlotte 的对应关系

| charlotte | TAS |
|---|---|
| `psci { method = "hvc"; }` | 运行时 `hvc`，一致 |
| HHEE TVM 握手 HVC `0xC600108A` | 已在 trampoline 中实现 |
| `charlotte-keepalive` 喂 LPM3 | 对应 `iomcu-watchdog@0xfa87c000` |
| `uart_v500` @ `0xffb82000` | TAS 是 **PL011** @ `0xfa054000` |
| simplefb @ `0x34380000` | TAS logo buffer @ `0x36500000` |
| `hhee@113c0000` | TAS 的 HHEE 内存未在 overlay 中暴露 |

## 下一步

1. 确认 UART0：
   ```cmd
   adb shell "su -c 'ls -l /sys/class/tty | findstr ttyAMA'"
   adb shell "su -c 'cat /sys/class/tty/ttyAMA0/device/uevent'"
   ```
   如果 `ttyAMA0` 对应 `fa054000.uart`，UEFI 可以直接用 PL011 @ `0xfa054000` 打日志，摆脱对 pstore 的依赖。

2. 取 UART 时钟：
   ```cmd
   adb shell "su -c 'find /sys/kernel/debug/clk -name \"*uart0*\"'"
   ```
   读 `clk_rate` 后就能算 115200 的 IBRD/FBRD。

3. 找 `iomcu-watchdog` 的喂狗寄存器：在内核源码里 `grep -R "iomcu-watchdog"`，对应驱动通常在
   `drivers/watchdog/hisi_iomcu_wdt.c` 或 `drivers/misc/hisi_iomcu.c`。

4. 继续验证 `boot-carrier-uefi4.img` 的 pmsg checkpoint：
   ```cmd
   adb shell "su -c 'ls -l /sys/fs/pstore'"
   adb shell "su -c 'cat /sys/fs/pstore/pmsg-ramoops-0'" > uefi-pmsg.txt
   findstr /C:"TAS-TRAMP-OK" uefi-pmsg.txt
   ```
