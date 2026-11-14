# 主线 Linux 阶段归档

这个阶段的目标是让 GN3002 跑 Linux 主线内核（mt6735-mainline 的 `mt6735-staging`，
Linux 7.3.0-rc3）。**结论：在这台机器上不划算，已停止。** 以下是过程与结论，留作记录。

## 做到哪一步

- CI 用 GitHub Actions 编译，两个 job：`build`（出 boot.img）+ `qemu-smoke`（QEMU virt 启动验证）
- 内核配置裁剪脚本把编译压到约 6 分钟
- 内核能编译、能在 QEMU 里启动到 `/init`
- 真机刷入 `boot` / `recovery` 分区后**启动不了**，两次都被看门狗复位
- 最终通过刷回原厂包救砖，救援链验证通过

## 已修掉的问题（都是真问题）

**QEMU 冒烟测试的价值就在这里**——它拦下了三个会让首启必挂的 bug，而这三个都是
"本地环境有、CI 环境没有"的差异：

1. **initramfs 里没有 busybox** —— 从 Ubuntu ports 拉 aarch64 `busybox-static` 解决
2. **`/init` 丢了可执行位，且缺 `/bin/sh` 软链** —— 内核报 `Failed to execute /init (error -2)`，
   真实原因是解释器不存在。补 chmod + applet 软链
3. **initramfs 缺 `/dev` `/proc` `/sys` `/tmp` 挂载点** —— devtmpfs 挂不上，
   `/dev/console` 和 `/dev/kmsg` 都不存在，init 的输出全部丢失；
   在真机上这会导致 USB gadget 也建不起来

另外修了 QEMU 侧的两个环境问题：`-nic none`（默认 virtio 网卡要找 `efi-virtio.rom`）、
以及脚本可执行位在 git 里丢失。

## 真机为什么起不来

两次刷入后都是：**没有任何 USB 枚举、屏幕无输出、约 10 秒后被看门狗复位**
（下次开机在 cmdline 里能看到 `androidboot.bootreason=wdt_by_pass_pwk`）。

逐个排除过的嫌疑：

| 嫌疑 | 结论 |
|---|---|
| boot.img 布局不对 | 排除。原厂与我们的镜像都是 gzip 内核 + DTB 拼在流后、`dt_size=0`，`kernel_addr` 都是 `0x40080000` |
| 缺 MTK 512 字节头 | 排除。原厂镜像也没有 |
| gzip 头部字段被 LK 校验（`gunzip header is bigger than expectation`） | 排除。两边 FLG/OS/XFL 完全一致 |
| `text_offset` 假设（原厂 0x80000 vs 现代内核 0） | 嫌疑降低。7.3 的 `pi/create_init_idmap` 按 `_stext` 实际物理地址建恒等映射，能容忍偏移 |
| PSCI 坏实现（社区 `mt6735-smp-fix` 实锤 MT6735 的 PSCI 有缺陷） | 改掉了：删 `psci` 节点、cpu0 改 spin-table、`cpu-release-addr=<0 0>`、关 `ARM_PSCI_CPUIDLE`。仍未能启动 |
| 内存窗口声明过大 | 改成了社区 X5 Pro 验证过的 `0x40000000 + 0x3f000000`，仍未能启动 |
| 看门狗没人喂 | init 里加了 magic-close 和 devmem 写 WDT_MODE，但没有机会执行到 |

最后停留在"改了也没法验证"的状态——因为**没有任何观测通道**。

后来在原厂包里发现 `mt6735_atf_release_pad.img`，说明这台机器**带 ARM Trusted Firmware**，
PSCI 未必真的是坑，只是 LK 没按 PSCI 交接。这条线索如果将来有人接手，值得从这里往下查。

## 为什么停下来

1. **产出物没意义**：pmOS wiki 上 MT6735 的现状是 UART/显示(simple-framebuffer)/GPU/pinctrl 可用，
   存储与 USB 部分可用，而 **WiFi / 蓝牙 / 基带 / 音频 / 相机 / GPS / 待机 / SMP 全部损坏或部分损坏**。
   即使全绿，得到的也只是"单核、无网、无声、不能待机的开发板"
2. **没有眼睛**：板子没引出 UART，`printk.disable_uart=1`，失败的唯一信号是"它活下来了没有"。
   没有日志的调试只能靠猜
3. **没有料**：没有原厂 3.10 内核源码（只有 `vmlinux`），downstream 路线也走不通；
   社区自己也在往 U-Boot 替换 LK 的方向走，而 U-Boot 在 MT6735 上还没跑通

## 保留的资产（别丢）

| 资产 | 位置 | 价值 |
|---|---|---|
| 帧缓冲实测参数 | `0x7e000000` / 16MB / stride 2944 / 32bpp | 从原厂 DTB 与 fb0 sysfs 实测，任何显示相关工作都要用 |
| MTK boot.img 打包器 | `scripts/mkbootimg_mtk.py` | 用原厂件重打包可**逐字节一致**，格式理解已验证 |
| 内核配置裁剪脚本 | `scripts/trim-config.sh` | 砍掉 SND/DRM/MEDIA/WLAN/BT/SCSI/HID/netfilter/Xen，编译 6 分钟 |
| QEMU 冒烟测试 | `.github/workflows/build.yml` | 判据是内核级证据，可复用于任何内核改动 |
| 设备树 | `dts/mt6735-gionee-gn3002.dts` | 含 MTKFB、ramoops、面板参数 |
| initramfs | `initramfs/init` | 含 devtmpfs 挂载、看门狗解除、kmsg 标记 |

## 如果将来要重启这个方向

前置条件按顺序，一条都不能跳：

1. **焊出 UART**（SoC UART0 在 0x11002000）—— 没有这个就不要开始
2. 用社区 U-Boot 替换 LK（`gitlab.com/mt6735-mainline/u-boot`），拿到 `fastboot boot` 和串口控制台
3. 然后再谈 SMP、显示（DRM）、触摸
