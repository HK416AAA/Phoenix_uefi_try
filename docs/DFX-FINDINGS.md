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

## 5. 下一步

既然 ABL/HHEE 已经跳转，先验证“代码到底有没有执行”：

- **reset-only stub**：只发 PSCI `SYSTEM_RESET`（`0x84000009`）。设备若在 1 秒内自己重启，说明 stub 执行了；若一直停在解锁警告，说明 HHEE 没有把控制权交给非 Linux 镜像。
- **write+reset stub**：先写 `0x36500000` 和 `0x36ea3f80`，再发 PSCI reset。出现颜色闪烁后重启 = 写屏成功；只重启不出色 = 写屏成功但 DPU 没扫描这两个缓冲；不重启 = 写入触发异常。
