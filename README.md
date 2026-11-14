# GIONEE GN3002 (GBL7356) 移植记录

金立 GN3002，代号 `GIONEE_GBL7356`，MediaTek **MT6735**，出厂 Android 5.1。

这个仓库记录这台机器的移植过程：**主线 Linux 部分已归档（结论是不划算），当前方向是 Android 8.1 / 9 的系统移植。**

## 现在在做什么

| 阶段 | 内容 | 状态 |
|---|---|---|
| 主线 Linux | 7.3 内核 + QEMU 冒烟验证 | **已归档**，见 [`docs/mainline-archive.md`](docs/mainline-archive.md) |
| Android 8.1（LineageOS 15.1） | 源码编译框架 + 原厂 5.1 vendor blobs | 进行中，见 [`docs/PLAN.md`](docs/PLAN.md) |
| Android 9（LineageOS 16.0） | 在 15.1 跑通后推进 | 待启动 |

主线为什么停：MT6735 的主线支持缺 WiFi / 蓝牙 / 基带 / 音频 / 相机 / 待机，只能做出"单核、无网、无声"的开发板；而这台机器没有引出 UART，失败时没有任何日志可看，等于蒙眼改代码。两次刷机失败都是这个原因，不是配置写错。

**Android 移植不存在这个问题**：驱动全在原厂内核里，框架层跑起来后 `logcat` 就是完整的观测通道，而且有同 SoC 的成熟设备树可以参照。

## 硬件速查

| 项目 | 值 |
|---|---|
| SoC | MT6735（4×Cortex-A53 @1.3GHz，Mali-T720 MP2） |
| 内存 / 存储 | 3GB LPDDR3 / 32GB eMMC |
| 屏幕 | 5" 720×1280，面板 `tm_ft8606`（天马 + 汇顶 FT8606） |
| 用户空间 | **64 位**（`ro.zygote=zygote64_32`） |
| 通信 | 双卡 dsda，MTK CCCI 基带；WiFi/BT 走 MTK WMT combo |
| 原厂内核 | Linux 3.10.65，无独立模块（全内建） |
| boot / recovery 分区 | 各 16MB（`mmcblk0p7` / `mmcblk0p8`） |

完整清单（含分区表、HAL 列表、传感器型号）见 [`docs/hardware.md`](docs/hardware.md)。

## 仓库结构

```
docs/
  hardware.md          硬件档案（从原厂固件实测得出）
  PLAN.md              Android 移植计划与里程碑
  FLASH.md             刷机与救砖手册（含已验证的救援流程）
  mainline-archive.md  主线阶段归档：做过什么、发现了什么、为什么停
config/                主线内核配置（归档）
dts/                   主线设备树（归档）
initramfs/             主线 initramfs（归档）
scripts/               主线打包与裁剪脚本（归档）
.github/workflows/     主线 CI（仍可手动触发，用 QEMU 验证内核）
```

## 主线部分怎么用（归档）

推送到 `main` 或手动触发 workflow，Actions 会用 `mt6735-mainline/linux` 的
`mt6735-staging`（7.3.0-rc3）编译 `Image.gz` + DTB，并在 QEMU `virt` 上做冒烟测试
（判据：`Run /init as init process` + 无 `Failed to execute` + 无 panic）。
一次约 6 分钟。

产物 `boot-gz.img` 与原厂 boot.img 同构，`scripts/mkbootimg_mtk.py` 用原厂件重打包
可得到逐字节一致的结果。

## 刷机前必读

**先确认救援链可用，再动任何分区。** 这台机器已经验证过 SP Flash Tool 全量刷原厂包能救砖。

详见 [`docs/FLASH.md`](docs/FLASH.md)。摘要：

- 只动 `boot` / `recovery`，**绝不碰** `preloader` / `lk` / `tee`
- 原厂包 `gionee-gn3002_SV1.0_5.1_2017.10.11.zip` 必须留着，那是唯一可靠的救援手段
- LK 的 `fastboot boot` 会因为"低电量误报"被拒绝，别在这上面浪费时间
- 进 fastboot 要按物理键，`adb reboot bootloader` 不可靠

## 许可

- 本仓库脚本与文档：BSD-3-Clause，见 `LICENSE`
- 引用的内核源码（mt6735-mainline/linux）为 GPL-2.0-only
- 移植所用的原厂 blobs 版权归联发科 / 金立所有，不随本仓库分发
