# 板级数据：从 TAS-AL00 的 DTB 到 UEFI

## 1. 为什么盯住 DTB

实测事实：**LIO-AL00（Mate 30 Pro 4G）源码编出的 `Image.gz` 能在 TAS-AL00（Mate 30 4G）上正常开机，功能无异常。**

这说明：

- 内核镜像与板级解耦。同一份内核可以跨 990 4G / 5G、跨 TAS / LIO 启动。
- 板级差异由 bootloader 加载的 `dtb` / `dtbo` 提供，并在启动时打补丁。
- 因此 **UEFI 需要的地址表也只能来自这台机器的 DTB**，不可能从内核源码推出来。

## 2. 三个来源与优先级

| 优先级 | 来源 | 特点 |
|---|---|---|
| 1 | `dtc -I fs /proc/device-tree` → `runtime.dts` | 运行时视图，已含 ABL 对 `memory` / `reserved-memory` / `chosen` 的补丁，最准 |
| 2 | `dtb.img` / `dtbo.img` 分区 | 原始镜像，用于 diff、恢复、确认 overlay |
| 3 | 内核源码 | 只用于寄存器偏移、初始化时序、时钟/稳压器顺序 |

`dump-dtb.sh` 会同时产出三者。

## 3. 要提取的节点

| DTB 节点 | 字段 | UEFI 里的用途 |
|---|---|---|
| `/memory@*` | `reg` | 可用 DRAM 区间；决定 `FD_BASE` / `FD_SIZE` |
| `/reserved-memory/*` | `reg` | 必须排除：TEE、modem、NPU、ramoops、fb |
| `/psci` | `method`（smc/hvc）、`cpu_on`、`cpu_off` | SMP bring-up |
| `/cpus/cpu@*` | `reg`（MPIDR）、`enable-method` | 每核启动方式 |
| `/timer` | `interrupts` | ARM Generic Timer 的 PPI |
| `/interrupt-controller@*` | `reg`、`compatible` | GIC 基址与版本（GICv3/v4） |
| `/soc/serial@*` | `reg`、`clocks`、`interrupts` | UART 基址与波特率 |
| `/soc/ufs@*` / `hisi,ufs` | `reg`、`interrupts`、`clocks`、`phys` | UFS 主机控制器 |
| PMIC 节点（`hi6421` / `hi6422`） | 父总线、`reg`、`regulators` | 上电时序 |
| `/soc/gpio@*` | `reg`、`gpio-ranges` | GPIO 控制器分组与引脚数 |
| `ramoops` | `reg`、`record-size` | 无 UART 时的调试通道 |
| `/chosen` | `bootargs` | 内核启动参数，仅作参考 |

## 4. 从 DTB 推 FD_BASE

```
1. 取 /memory 的所有 bank，得到 [MemBase, MemEnd)
2. 扣掉 /reserved-memory 的所有子区间
3. 在剩下的空洞里，从 kernel_addr 之上找 4 MiB 对齐、连续 >= FD_SIZE 的位置
4. FD_BASE = 该空洞起点；FD_SIZE 先取 0x300000
5. 校验：FD_BASE + FD_SIZE 不与 ramdisk_addr、tags_addr、DTB 自身重叠
```

这些值最后写进 `Resources/Configs/tas.toml` 的 `uefi_fd.base` / `uefi_fd.size`。

这一步不用手算：

```bash
python scripts/plan-layout.py --boot stock_boot.img --dts mate30-dtb/runtime.dts
```

它会扣掉 `reserved-memory`、内核解压后的真实占用（gzip `ISIZE`）、ramdisk、tags，
输出可用空洞和 TOML 片段。

## 5. 把 runtime.dts 变成 Mu-Silicium 的 DTB

Mu-Silicium 需要的是 `Resources/DTBs/<codename>.dtb`，并把它 append 到 boot image。
可以直接以 `runtime.dts` 为起点：

保留：

- `/memory`、`/reserved-memory`
- `/psci`、`/cpus`、`/timer`
- `/interrupt-controller`
- `/soc/serial@*`
- `/soc/ufs@*`、GPIO、PMIC（UEFI 驱动会用到）

处理：

- 删除 Linux 专有、UEFI 不认识的节点（可选，EDK2 会忽略未知节点）
- 确认根节点有 `#address-cells = <2>`、`#size-cells = <2>`
- 给 `serial` 节点补 `clock-frequency`，或让 UEFI 驱动用固定值
- `dtc -I dts -O dtb -o tas.dtb tas.dts`

注意：`runtime.dts` 里的 `memory` 已经被 ABL 改过，和 `dtb.img` 可能不同。以 `runtime.dts` 为准。

## 6. 4G / 5G 的差异

TAS-AL00 是麒麟 990 4G，LIO 是 990 5G。虽然内核能通用，但：

- PMIC 通道、CPU 频率表、modem 相关节点不同
- panel / 触摸型号不同
- 5G 机型的 `reserved-memory` 里会有额外的 modem 区间

所以：**UEFI 的时钟、电源、显示初始化必须按 TAS 的 DTB，不要照抄 LIO 的任何板级数值。**

## 7. 一条命令拿到全部

```bash
bash scripts/dump-dtb.sh mate30-dtb
grep -nE 'memory@|reserved-memory|ramoops|serial@|ufs|pmic|gpio@|psci|timer|interrupt-controller|chosen' \
  mate30-dtb/runtime.dts
```

把这段输出发出来，就可以开始填 `tas.toml` 和平台骨架。
