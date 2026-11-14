# Gionee GN3002 (F306) — Linux 主线移植

MT6735 / 3GB LPDDR3 / 32GB eMMC / 5" 720x1280 / MT6328 PMIC

---

## 1. 关于 lk2nd 的结论（重要）

**lk2nd 是 Qualcomm 专用，MT6735 用不了。**

lk2nd 建立在 Qualcomm 的 LK/aboot 之上，依赖：

- Qualcomm 的 `aboot` 引导协议与 QCDT 设备树打包
- `fastboot boot` 从内存引导
- msm8916/8974 等平台的时钟、电源、存储初始化代码

MT6735 的引导链是 **preloader → LK（MTK 版）**，LK 是 MTK 自己的代码库，
与 Qualcomm LK 只是同名，寄存器、启动参数、设备树传递方式全都不同。
把 lk2nd 编译到 MT6735 上没有可运行的硬件抽象层。

社区里对应的东西是 mt6735-mainline 的 **U-Boot 移植**
（`gitlab.com/mt6735-mainline/u-boot`，目前只有 grandpplte 一个板子），
作用类似 lk2nd：提供 fastboot / 菜单 / 从内存引导。但它**不是必需品**——
这颗 SoC 的原厂 LK 本身能直接引导 arm64 内核。

所以本项目的路线是：

```
preloader -> LK -> [Image.gz + DTB] (boot 分区) -> mainline
```

U-Boot 留作后续可选项（想要 `fastboot boot` 反复试内核时再上）。

## 2. 已经确认的事实（从原厂固件里挖出来的）

| 项目 | 值 | 来源 |
|---|---|---|
| SoC | MT6735（Denali-1，4×A53@1.3G，Mali-T720 MP2） | scatter / preloader 名 |
| 平台工程名 | `gionee6735_66t_l1` | `MT6735_Android_scatter.txt` |
| 原厂内核 | Linux **3.10.65**，gcc 4.9，2016-05-12 | `vmlinux` / boot.img |
| boot 分区 | 8 MB（0x1D80000，大小 0x1000000） | scatter |
| 页大小 | 2048 | boot.img header |
| 内核布局 | `Image.gz` + **DTB 直接拼在 gzip 流之后**（dt_size 字段=0） | 实测 boot.img |
| 启动模式串 | `bootopt=64S3,32N2,64N2` → LK **会**做 AArch64 切换，不需要 bootshim | boot.img cmdline |
| 内存 | 3GB（待设备实测确认映射） | PDAdb |
| 屏幕 | 720×1280 IPS，面板三选一：`tcl_db7400` / `tianma+FT8606` / `tcl_xinsi xs4100` | LK 字符串 |
| 触摸 | EINT = GPIO10；控制器 FocalTech FT5x26/FT8606 或 Solomon SSD6600（跟面板走） | 原厂 DTB + 内核字符串 |
| 传感器 | MC3410(加速度) / ITG1010(陀螺) / AKM09911(磁力) / CM36652(光距)，都在 i2c2 | 原厂 DTB |
| SD 卡检测 | EINT5 | 原厂 DTB(`MSDC1_INS@5`) |
| PMIC | MT6328（电源键在 PMIC 内） | 原厂 DTB + dtsi |
| 不支持 | WiFi/BT(MT6630)、Modem、音频、摄像头、GPU 加速 | mainline 现状 |

**打包器已验证**：`scripts/mkbootimg_mtk.py` 用原厂 Image.gz + DTB + ramdisk
重新打包，输出与原厂 `boot.img` **逐字节一致**（8110080 字节），
说明对 MTK boot image 格式的理解是对的。

## 3. 主线内核现状（mt6735-staging, Linux 7.3.0-rc3）

上游主线**没有** mt6735 支持，社区树 `gitlab.com/mt6735-mainline/linux`
分支 `mt6735-staging` 才有 `mt6735.dtsi` / `mt6328.dtsi` 和驱动补丁。

已有的：UART、eMMC/SD、I2C、pinctrl、PMIC(MT6328 稳压器/RTC/按键)、
USB(musb)、SMP、cpufreq、cpuidle、simple-framebuffer。

缺的：显示控制器(DRM)、WiFi、音频、摄像头、充电、温控。

所以现实目标：**启动到 initramfs + USB 串口 shell**，再逐步补显示/触摸。

## 4. 路线

### v1（首启，安全优先）
- 内核：7.3.0-rc3 + mt6735-staging
- 设备树：`mt6735-gionee-gn3002.dts`
- initramfs **编进内核**（不依赖 LK 是否正确传 initrd）
- 显示**先关掉**（simple-framebuffer 地址没实测，写错会破坏内存）
- 判据：USB 上出现 `/dev/ttyACM*`，能进 shell；pstore 有上次日志

### v2（有实测数据后）
- 填入 FB 基址 / stride，打开 simple-framebuffer → 屏幕出 console
- 触摸：确认 i2c 总线/地址/reset GPIO → 打开 `edt-ft5x06`
- 音量键：确认是 GPIO 还是 KP 矩阵
- 内存大小按 `/proc/iomem` 修正

### v3（可选）
- U-Boot 二级引导（≈ lk2nd 的用法），`fastboot boot` 免刷机试内核
- 真 rootfs（postmarketOS / Alpine）从 SD 卡或 userdata 启动
- GPU/DRM 等长期项

## 5. 风险与恢复

- 只动 **boot 分区**，system/userdata 不碰
- 刷之前先备份：`adb shell su -c 'dd if=/dev/block/by-name/boot of=/sdcard/boot-stock.img'`
- 挂了就 `fastboot flash boot boot-stock.img`，或用 SP Flash Tool 只勾 boot
- 不要刷 preloader / lk / tee —— 那是变砖区
