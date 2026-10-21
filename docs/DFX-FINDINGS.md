# DFX 日志分析（16 MiB dump）

`dfx` 是 Huawei 的 DFX 分区转储，里面按启动次数保存了多份 bootloader 日志。
本次关键结论来自其中的 v1 / v2 stub 启动记录。

## 1. v1（100 字节载荷）

```
[cpu0][7968 ms] load_kernel: boot load @ 0x80000 (0x56 bytes)
[cpu0][7968 ms] load_kernel: Decompressed kernel size is 0x64
[cpu0][7968 ms] load_kernel: load kernel image end
[cpu0][8657 ms] load_kernel: ----boot time is 8657 ms----
[cpu0][8659 ms] load_kernel: boot from hhee.
```

## 2. v2（2 MiB 填充载荷）

```
[cpu0][12006 ms] load_kernel: avb verify failed: 3
[cpu0][12006 ms] load_kernel: boot load @ 0x80000 (0x865 bytes)
[cpu0][12011 ms] load_kernel: Decompressed kernel size is 0x200000
[cpu0][12011 ms] load_kernel: load kernel image end
[cpu0][12699 ms] load_kernel: boot from hhee.
```

**两次都完成了加载、解压，并走到 `boot from hhee`。**
所以镜像大小、AVB 尾部、boot image 布局都不是阻塞点；问题发生在 HHEE 接手之后。

## 3. HHEE 状态

```
load_hhee: hhee will be loaded
secureboot: hhee secboot_power_up_verify ok!
load_hhee: xom_enable = 1
load_hhee: mntnxom = 49
load_hhee: load_hhee end
```

HHEE 已加载并通过校验，XOM 开启。运行期内核日志里也能看到 `hhee irq handler`。

## 4. 显示缓冲

bootloader 的 GUI 日志：

```
gui: [gui_main]: disp_info is 1080 and 2340.
gui: [gui_main]: lcd_dispbuf:0x36500000, canvas_buf:0x36ea3f80
display: [LOGO I] logo_data->fb_base = 0x36500000
display: [LOGO I] logo_data->fb_size = 0x03f00000
display: [LCD_KIT/I] lcd_kit_panel_on: fb0
```

- `lcd_dispbuf` = `0x36500000`
- `canvas_buf` = `0x36ea3f80`
- 分辨率 1080×2340，panel 为 `lcd_kit_taurus_samsung_ea8079`
- bootloader 在 239525 ms 时执行过 `watchdog: Enable watchdog start`

## 6. 执行证明（2026-10-22）

`boot-carrier-pstore.img`：`code0` → payload @ `0x31e0000`（写 pstore 标记）→ 跳回原厂 `stext`。
启动 Android 后 `/sys/fs/pstore/console-ramoops-0` 第一行：

```
TAS-STEP1-PSTORE-OK
```

结论：

- HHEE 执行 `code0`
- 追加在 `image_size` 之后的 payload 不会被 BSS 清零
- 写回 `stext` 后 Android 正常启动
- 之前 reset 不生效是 **SMC** 的问题，不是入口问题
- TAS 的 pstore console zone 在 `0x2f060000`（ramoops: record 0x20000 / console 0x80000 / pmsg 0x20000）

参考 charlotte 的 HHEE 处理：`psci { method = "hvc"; }`、TVM 握手 HVC `0xC600108A`、
HHEE 日志 HVC `0xC9000005`/`0xC9000006`、LPM3 watchdog `0x46`。

## 7. 下一步

- 确认 TAS 的 PSCI conduit：`/proc/device-tree/psci/method`（预期 `hvc`）
- UEFI 入口 payload 必须先发 TVM 握手 HVC `0xC600108A`
- PSCI 使用 HVC，不再用 SMC
- 单核起步；LPM3 watchdog 需要喂，或把首轮启动控制在 24 秒内
- 用 pstore / HHEE log 作为早期调试通道
