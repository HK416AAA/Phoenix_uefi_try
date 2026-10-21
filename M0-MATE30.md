# Mate 30 (TAS) — M0 可行性验证

目标只有一个：**在写任何 Kirin 驱动之前，确认这台机器能不能跑自制固件。**
M0 不产出 UEFI，只产出三个 yes/no。

> 已知：你已经在 TAS-AL00 上成功启动 LIO 源码编出的内核。如果用的是 `fastboot flash boot`，
> 说明未签名镜像已经被接受，Gate 3 的签名风险基本排除；但仍需单独确认 `fastboot boot`
> 这个临时启动命令是否可用，以及它的加载地址。

## 0. 先确认机型

| 型号 | 市场名 | SoC | 能否用同一解锁方案 |
|---|---|---|---|
| TAS-AN00 / TAS-TN00 | Mate 30 5G | 麒麟 990 5G | 社区方案覆盖 5G 机型，但 TAS 属“未验证” |
| TAS-AL00 / TAS-L09 / TAS-L29 | Mate 30 4G | 麒麟 990 4G | 已实测解锁（`bootlock=unlocked`） |

> 实测：LIO-AL00（Mate 30 Pro 4G）源码编出的内核可在 TAS-AL00 上正常开机，说明内核镜像与板级解耦。
> 但 UEFI 的时钟、PMIC、显示必须按 TAS 自己的 DTB 来，不能套 LIO 的板级配置（见 [docs/BOARD-DATA.md](docs/BOARD-DATA.md)）。

`adb shell getprop ro.product.model` 与 `ro.boot.hardware` 各跑一次，确认到底是 4G 还是 5G。
4G 机型如果已经解锁，也继续走下面的流程，但不要套用 5G 的板级固件。

## 1. 采集（先做，不碰设备状态）

```bash
# Android 已启动
bash scripts/collect-device.sh mate30-adb

# 重启到 fastboot 再跑一次
adb reboot bootloader
bash scripts/collect-device.sh mate30-fastboot
```

重点看：

- `fastboot-getvar.txt`：`unlocked`、`secure`、`current-slot`、`partition-size:boot`
- `by-name.txt`：`boot`、`vbmeta`、`super`、`userdata` 的实际块设备
- `cmdline.txt`：`androidboot.*`、`skip_initramfs`、`slot_suffix`
- `iomem.txt` / dmesg：DRAM 与 reserved 区的实际布局

## 2. Gate 1：解锁与 fastboot 能力

```bash
fastboot oem get-bootinfo
fastboot oem lock-state info
fastboot getvar unlocked
```

判定：

- `unlocked: yes` → 继续
- `unlocked: no` 或命令不存在 → 停，先解决解锁
- `fastboot boot` 返回 `unknown command` → 华为 ABL 没有临时启动命令，Mu-Silicium 的整条路径失效

## 3. Gate 2：`fastboot boot` 能不能加载原厂镜像

```bash
fastboot boot stock_boot.img
```

`stock_boot.img` 从 `collect-device.sh` 的 root dump 拿，或从官方固件包里解出来。

- 能正常进 Android → ABL 的临时启动路径是通的
- 卡住/黑屏但 fastboot 仍然响应 → 可能只接受特定 header，继续 Gate 3 再判断
- `FAILED (remote: ...)` → 记录完整错误，基本可以停

## 4. Gate 3：ABL 接不接受未签名镜像

这一步用**无限循环**的内核替换原厂内核，镜像只在内存里跑，不写任何分区。
设备会挂住，长按电源键重启即可回到 Android。

```bash
python scripts/bootimg.py stock_boot.img
python scripts/make-test-bootimg.py stock_boot.img test-header.img
fastboot boot test-header.img
```

如果返回签名/校验错误，再试不带 ARM64 header 的版本：

```bash
python scripts/make-test-bootimg.py stock_boot.img test-raw.img --no-kernel-header
fastboot boot test-raw.img
```

判定：

| 现象 | 含义 | 下一步 |
|---|---|---|
| 设备挂起，按键无反应 | 未签名镜像被接受 | M1 可做 |
| `FAILED (remote: 'signature ...')` / `verify fail` | AVB 仍强制 | 尝试关闭校验；关不掉就停 |
| 立刻回到 fastboot / 反复重启 | 镜像被接受但入口不对 | 调整 header 与加载地址 |
| `unknown command` | 无 `fastboot boot` | 停 |

**不要用 `fastboot flash boot` 做这个测试。** 一旦写坏 boot 分区，恢复要靠完整固件包甚至拆机。

## 5. 从 boot.img 推 FD_BASE / FD_SIZE

`bootimg.py` 会打印 `kernel_addr`。Mu-Silicium 的加载方式是：

```
ABL 解压 boot.img 的 kernel 到 kernel_addr
  → 跳到 kernel_addr（BootShim 开头）
    → BootShim 把 FD_SIZE 字节从 _Payload 复制到 FD_BASE
      → 跳到 FD_BASE（UEFI FV 入口）
```

所以：

- `FD_BASE` 不能等于 `kernel_addr`（FV 在 64 字节 header 之后）
- `FD_BASE + FD_SIZE` 不能碰到 `ramdisk_addr`、`tags_addr`、DTB 和 `reserved-memory`
- 第一次建议 `FD_SIZE = 0x300000`（3 MiB），`FD_BASE` 取 `kernel_addr` 上方一个
  4 MiB 对齐、且落在 `/memory` 可用区间内的空洞

直接让脚本算：

```bash
python scripts/plan-layout.py --boot stock_boot.img --dts mate30-dtb/runtime.dts
```

它会打印 `kernel_addr`、gzip 解压后的真实占用（`ISIZE`）、`/memory`、`reserved-memory`、
可用空洞，以及可直接填进 `tas.toml` 的 `[uefi_fd]` 片段。注意用的是**解压后**的内核占用，
不是 boot header 里的压缩大小。

用**设备自己的 dtb** 交叉验证，不要从 LIO 内核源码找——那份源码没有麒麟 990 板级 dts
（见 [docs/KERNEL-SOURCE.md](docs/KERNEL-SOURCE.md)）：

```bash
bash scripts/dump-dtb.sh mate30-dtb
grep -nE 'memory@|reserved-memory|ramoops|serial@|ufs|pmic|gpio@|psci' mate30-dtb/dtb.dts
```

`dtb.dts` 里的 `memory@` 与 `reserved-memory` 才是这台机器真实的可用区间。

## 6. 没有串口，怎么拿到第一行日志

Mate 30 没有外露 UART。M1 之前先把调试通道定下来，否则固件跑飞了也不知道死在哪。

按可行性排序：

1. **ramoops / pstore**：从 `dtb.dts` 的 `ramoops` 节点拿物理地址，stub 往固定偏移写 ASCII 标记，
   重启进 Android 后 `su -c 'cat /sys/fs/pstore/console-ramoops*'`。
   先用一次真实的内核 panic 验证 pstore 会不会在启动时被清空——会清空就不能用。
2. **USB device mode**：让 stub 初始化 DWC3，枚举成 CDC-ACM。工作量大，但不依赖分区。
3. **显示**：点亮 DSI 并画色块。需要 panel 初始化序列，属于 M3 的工作。
4. **Huawei COM1**：解锁时用过的 testpoint/COM1 通道是否支持读内存，取决于 kirintool，未必可用。

## 7. M0 通过后的顺序

1. 用 BootShim + 一个只写 ramoops 的最小 FV 验证 M1（能执行、能留下日志）
2. 把 `Platforms/Huawei/tasPkg` 与 `Silicon/HiSilicon/kirin990Pkg` 建起来，只做 UART/GPIO/timer
3. 再往上才是 UFS、GOP、输入

## 8. 现在就能确定的事

- Mate 30 5G：麒麟 990 5G，2×A76 2.86G + 2×A76 2.36G + 4×A55 1.95G，Mali-G76 MP16，LPDDR4X，UFS 3.0，1080×2340
- BootShim 的复制循环按 16 字节走，`FD_SIZE` 必须是 16 的倍数
- `REQUIRES_KERNEL_HEADER=1` 会在开头插入 64 字节 ARM64 Image header；
  华为 ABL 是否需要它，正是 Gate 3 要回答的问题

## 9. 风险

- TAS 不在 XDA 帖的“100% 支持”列表里，解锁可能不完整（分区可写但启动校验仍在）
- 板级固件解锁后常见副作用：USB 失效、分区表异常、无法回锁
- 任何 `flash` 操作都可能让设备回不到 Android；M0 阶段只允许 `fastboot boot`
