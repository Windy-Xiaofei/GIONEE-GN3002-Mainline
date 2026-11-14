# GIONEE GN3002 mainline

金立 GN3002（F306，MediaTek MT6735）跑 Linux 主线内核。

用 GitHub Actions 交叉编译，产出可直接刷入 `boot` 分区的镜像。

## 这个项目里没有 lk2nd

lk2nd 是 Qualcomm 专用的二级引导器，依赖 aboot / QCDT / Qualcomm LK 的 fastboot
协议。MT6735 的引导链是 `preloader → MTK LK`，两套 LK 只是同名，寄存器、
启动参数、设备树传递方式全都不同。

这颗 SoC 的原厂 LK 自己就能引导 arm64 内核 —— 原厂 boot.img 的 cmdline 是
`bootopt=64S3,32N2,64N2`，最后一段就是让 LK 把内核切到 AArch64。所以不需要
bootshim，也不需要 lk2nd。

社区对应物是 [mt6735-mainline 的 U-Boot](https://gitlab.com/mt6735-mainline/u-boot)，
作用类似 lk2nd（fastboot / 菜单 / 从内存引导），但不是必需品，留作后续可选项。

## 硬件

| 项目 | 值 |
|---|---|
| SoC | MT6735（4×Cortex-A53 @1.3GHz，Mali-T720 MP2） |
| 内存 / 存储 | 3GB LPDDR3 / 32GB eMMC |
| 屏幕 | 5" 720×1280 IPS（面板三选一：tcl_db7400 / tianma+FT8606 / tcl_xinsi xs4100） |
| PMIC | MT6328 |
| 触摸 | FocalTech FT5x26/FT8606 或 Solomon SSD6600，EINT=GPIO10 |
| 传感器 | MC3410 / ITG1010 / AKM09911 / CM36652（i2c2） |

完整清单见 `docs/PLAN.md`。

## 构建

推送到 `main` 或手动 `workflow_dispatch`，Actions 会：

1. 拉取锁定 commit 的内核源码（mt6735-mainline/linux `mt6735-staging`，7.3.0-rc3）
2. 套上本仓库的设备树 `dts/mt6735-gionee-gn3002.dts`
3. 用 `config/pmos-mt6735.config` 做基线 + 打开必要选项
4. 编译 `Image.gz` 与 DTB，打成 MTK 布局的 boot 镜像
5. 上传 `gn3002-boot` artifact

产物：

| 文件 | 说明 |
|---|---|
| `boot-gz.img` | Image.gz + DTB 拼接，与原厂同构，**优先用这个** |
| `boot-raw.img` | 裸 Image + DTB，超过 16MB boot 分区，只能 `fastboot boot` |
| `Image.gz` / `mt6735-gionee-gn3002.dtb` | 单独的内核与设备树 |

boot image 格式：page 2048，kernel blob = Image.gz 后紧跟 DTB，header 里
`dt_size` 为 0（与原厂一致）。`scripts/mkbootimg_mtk.py` 用原厂件重打包可得到
**逐字节一致**的镜像。

## 刷机

```bash
# 先不写 flash，只进内存
adb reboot bootloader
fastboot boot boot-gz.img

# 确认能起来再写
fastboot flash boot boot-gz.img
```

回滚：刷回备份的原厂 boot.img。只动 `boot` 分区，preloader / lk / tee 一概不碰。

详细说明见 `docs/FLASH.md`。

## 当前状态

- [x] 原厂固件解析（MT6735 / 3GB / 32GB / 720×1280 / MT6328）
- [x] boot.img 打包器验证（用原厂件重打包，逐字节一致）
- [x] 设备树编译通过
- [x] 内核 7.3.0-rc3 + 内建 initramfs 编译通过（本地与 CI 均通过）
- [ ] 首次启动（判据：USB CDC-ACM 出现 `/dev/ttyACM0`）
- [ ] 显示（等实测 FB 基址 / stride）
- [ ] 触摸（等实测 i2c 总线 / 地址 / reset GPIO）
- [ ] 音量键 / 充电 / 音频 / WiFi（长期）

## 首启为什么黑屏

simple-framebuffer 的物理地址和内存大小没有实测值。地址猜错 = 内核往错误
物理内存写像素，会把内存写花，所以首版刻意关掉显示，用 USB 串口当判据，
内存也只声明低 2GB（3GB 在 LPAE 下可能被拆到 4GB 以上）。

拿到 `/proc/iomem`、`/sys/class/graphics/fb0/*` 之后就能开显示。

## 许可

- 本仓库代码与脚本：**BSD-3-Clause**，见 `LICENSE`
- `dts/` 下的设备树同样为 **BSD-3-Clause**（与 GPL-2.0 项目兼容，可直接进内核树）
- 引用的内核源码（mt6735-mainline/linux）为 **GPL-2.0-only**
