# 打包：把 UEFI 装进华为 boot.img

## 1. 这个 boot.img 告诉了我们什么

解析 `kirin990_Lio-al00_HM103_ksu_101.img` 的结果：

| 字段 | 值 |
|---|---|
| header_version | 2 |
| page_size | 2048 |
| kernel_addr | `0x80000` |
| kernel_size | `0x10b4104`（gzip） |
| Image header | `image_size=0x31e0000`（49.9 MiB，含 BSS）、`text_offset=0`、PIE=1、4K 页 |
| 内核占用 | `0x80000` - `0x3260000`（按 Image 头，不是 gzip 的 41.7 MiB） |
| ramdisk_addr / size | `0x66200000` / `0x1ef`（几乎为空） |
| tags_addr | `0x66000000` |
| dtb_addr / size | `0x1f00000` / `0x14c180` |
| dtb 实际格式 | **DTBO 表**（magic `0xd7b7ab1e`，含 base + overlay 两份 FDT） |

DTBO 里的两份 FDT 给出：

| 项 | 值 |
|---|---|
| GIC | `0xfe400000`（dist）、`0xfe440000`（redist），GICv3 |
| Generic Timer | 1.92 MHz，PPI 13/14/11/10 |
| PSCI | `smc` |
| UFS | `0xf8200000` + PHY `0xf81ff000`，IRQ 278 / 137 |
| UART 候选 | `0xfa054000`、`0xfa040000`、`0xfa044000`、`0xfa041000`、`0xfa045000`、`0xfa874000`、`0xfff02000` |
| ramoops / pstore | `0x2f000000` - `0x2f100000`（1 MiB） |
| logo framebuffer | `0x36500000` - `0x3a400000`（63 MiB，bootloader 已点亮） |
| dtb / ramdisk 预留 | `0x66000000` / `0x66200000` |
| 可用空洞 | `0x03260000` - `0x10000000`（205 MiB） |
| FD_BASE 候选 | `0x3400000`，`FD_SIZE = 0x300000` |

### 运行时确认（TAS-AL00，`/proc/iomem`）

```
00080000-0214ffff : Kernel code
02150000-0223ffff : reserved
02240000-0325ffff : Kernel data
```

- 内核实际占用 `0x80000` - `0x3260000`，与 Image 头 `image_size=0x31e0000` 完全吻合
- `0x03260000` - `0x10000000` 是 System RAM 空闲区
- **FD_BASE = `0x3400000` 已确认**，不需要 `--kernel-base` 覆盖
- cmdline 里 `dtbo_idx=292`：ABL 从 `dtbo` 分区选板级 overlay，boot.img 内的 DTBO 表不是板级来源
- cmdline 里 `console=ttyS0`，但运行时没有 `/sys/class/tty/ttyS0`、没有 `/proc/tty/driver/serial`，
  dmesg 里也没有 `ttyS`：**串口控制台不可用**，M1 只能靠屏幕或 pstore

### Bootloader 实测（`last_bootloader_log`）

| 项 | 值 |
|---|---|
| boot 加载 | `boot load @ 0x80000`，`0x10b4104` 字节 |
| 解压 | `0x29bc008`；Image 头 `image_size = 0x31e0000` |
| 最终 DTB | `0x3bc01000`，737,966 字节 |
| DTBO | 330 个 entry；`apply [dtbo] patch failed`，但 base DTB 已含 TAS 配置 |
| logo fb | base `0x36500000`，size `0x03f00000`，1080×2340 |
| panel | `lcd_kit_taurus_samsung_ea8079`（本机），`product_id = 2001` |
| ramdisk | `0x66200000` - `0x66a00000` |
| AVB | `avb verify failed: 3`（`HASH_MISMATCH`），ABL 继续启动 |
| UART | `uart_mode_is_off: not support usb switch` |
| 安全环境 | HHEE / BL31 / TEEOS 已加载，PSCI 走 SMC |

`avb verify failed` 之后仍然执行 `load_kernel` 并跳转，这就是自制内核能启动的原因。
`0x3bc01000` 是交给内核的 DTB 指针，BootShim 不碰 `x0`，UEFI 可以直接用它。

### 抓早期 dmesg

上传的 dmesg 最早一行已经是 209s，早期启动日志被 vendor 日志冲掉了。两种办法：

```cmd
:: 1. 重启后立刻抓，通常在缓冲区被冲掉之前
adb reboot
adb wait-for-device
adb shell "su -c 'dmesg'" > dmesg-early.txt
```

```cmd
:: 2. 加大环形缓冲区（会改 cmdline，仍然只写 boot 分区）
python scripts\repack-bootimg.py --stock stock_boot.img --kernel kernel.gz ^
  --out boot-log.img --cmdline-append log_buf_len=8M
fastboot flash boot boot-log.img
```

`repack-bootimg.py --cmdline-append` 只改 boot header 里的 512 字节 cmdline 字段，
不动 DTBO、地址和内核。

`logo-buffer` 很关键：ABL 已经把 panel 点亮并留下帧缓冲，M2 可以先往这里画字，
不必等 DSI 驱动。

## 2. 为什么不直接用 Mu-Silicium 生成的 boot.img

Huawei 的 `dtb` 字段不是一个 FDT，而是 DTBO 表。Mu-Silicium 的 `append_dtb`
会追加单个 FDT，直接刷会破坏板级配置。

正确做法：

```
Mu-Silicium 构建 → 从生成的 .img 里取出 kernel（BootShim + FV，gzip）
                 → 用 repack 工具塞回原厂 boot.img，保留原 DTBO 表
```

## 3. 步骤

```bash
# 1. 从构建产物里取出 kernel
python scripts/bootimg.py Mu-lio.img --extract-kernel kernel.gz

# 2. 塞回原厂镜像（保留 DTBO、地址、cmdline）
python scripts/repack-bootimg.py \
  --stock stock_boot.img \
  --kernel kernel.gz \
  --out boot-uefi.img

# 3. 确认输出
python scripts/bootimg.py boot-uefi.img --json

# 4. 刷入
fastboot flash boot boot-uefi.img
```

`repack-bootimg.py` 会：

- 保留 `kernel_addr` / `ramdisk_addr` / `tags_addr` / `dtb_addr` / `cmdline`
- 原样复制 DTBO 表
- 默认把输出补齐到原文件大小，覆盖分区里可能残留的 AVB 尾部
- 重新计算 `kernel_size` / `ramdisk_size` / `dtb_size`

## 4. 恢复

始终保留一份原厂 `stock_boot.img`：

```bash
fastboot flash boot stock_boot.img
```

只要 bootloader 还能进 fastboot，就能恢复。**不要碰 `boot` 以外的分区。**

## 5. 已知风险

- 镜像没有有效 AVB 签名。设备已能刷入自制内核，说明校验已关闭；如果更换固件版本后
  校验被重新打开，这个镜像会被拒绝。
- `id` 字段沿用原厂值，没有重算。如果 ABL 校验它，需要改成新 kernel 的 SHA-1；
  目前的实测表明它不校验。
- DTBO 表来自 LIO-AL00。ABL 实际按 `dtbo_idx=292` 从 `dtbo` 分区选板级 DTB，
  boot.img 里的表不参与启动；保留它只是为了不破坏镜像格式。
- `console=ttyS0` 已存在，但华为是否把该 UART 引出到可接触的焊盘/触点未知。

## 镜像清理

每生成一个新的 boot 镜像后，只保留最新一个：

```bash
python scripts/clean-images.py
# 或显式指定
python scripts/clean-images.py --keep boot-carrier-uefi7.img
```

`boot-*.img` 已被 `.gitignore` 忽略，清理只影响本地文件。

