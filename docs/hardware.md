# 硬件档案

全部来自原厂固件实测（`gionee-gn3002_SV1.0_5.1_2017.10.11.zip`），标注了每一项的来源，
方便判断可信度。

## SoC 与平台

| 项目 | 值 | 来源 |
|---|---|---|
| SoC | MT6735（Denali-1，4×Cortex-A53 @1.3GHz，Mali-T720 MP2） | scatter / preloader 名 |
| 平台工程名 | `gionee6735_66t_l1` | `MT6735_Android_scatter.txt` |
| 存储 | eMMC，boot channel MSDC_0，block size 0x20000 | scatter general |
| 安全固件 | 有 ATF（`mt6735_atf_release_pad.img`）+ `trustzone.bin` + `secro.img` | 原厂包 |
| 基带 | MTK CCCI，`modem_1_lwg_n.img`（LTE），双卡 dsda | `system/etc/firmware`、build.prop |

## 系统身份

| 项目 | 值 |
|---|---|
| 型号 / 品牌 | GN3002 / GIONEE |
| 设备代号 | **`GIONEE_GBL7356`**（`ro.product.device`） |
| 出厂系统 | Android 5.1 / SDK 22 |
| 用户空间 | **64 位**：`ro.zygote=zygote64_32`，`lib/` 与 `lib64/` 并存 |
| 屏幕密度 | 320 dpi，`ro.sf.hwrotation=0` |

## 内核与 boot 镜像布局

| 项目 | 值 |
|---|---|
| 原厂内核 | Linux 3.10.65，gcc 4.9，构建于 2016-05-12 |
| 内核模块 | **无**（`/system/lib/modules` 为空，全部内建） |
| page size | 2048 |
| kernel base / offset | `0x40000000` / `+0x00080000` |
| ramdisk / tags offset | `0x04000000` / `0x0E000000` |
| 内核 blob | `Image.gz` 后紧跟 DTB，header 的 `dt_size` 为 0 |
| cmdline | `bootopt=64S3,32N2,64N2`（最后一段让 LK 切 AArch64，因此不需要 bootshim） |

提取好的预编译内核：`work/rom/Image.gz-dtb`（6,928,802 字节，其中 DTB 27,604 字节）。
这个文件可以直接用作 Android 设备树的 `TARGET_PREBUILT_KERNEL`。

## 分区表（关键项）

| 分区 | 大小 | 说明 |
|---|---|---|
| preloader | 256 KB | **绝对不要碰** |
| lk | 512 KB | **绝对不要碰** |
| boot | 16 MB | `mmcblk0p7` |
| recovery | 16 MB | `mmcblk0p8`，移植期刷 TWRP 用这里 |
| system | **3 GB** | 空间充裕，8.1/9 都放得下 |
| cache | 400 MB | |
| userdata | 1.5 GB | |
| nvdata | 32 MB | 含基带校准数据，不要格式化 |
| frp | 1 MB | 挂载为 `/persistent` |
| protect1 / protect2 | — | 挂载为 `/protect_f` / `/protect_s` |

块设备路径统一为 `/dev/block/platform/mtk-msdc.0/by-name/<名字>`。

## 显示

| 项目 | 值 | 来源 |
|---|---|---|
| 分辨率 | 720×1280 | fb0 `virtual_size=736,3840` |
| 面板 | `tm_ft8606`（天马 + 汇顶 FT8606 触摸一体） | 原厂 cmdline `lcm=1-tm_ft8606` |
| 帧缓冲基址 | **`0x7e000000`，16 MB** | 原厂 DTB `MTKFB` 节点 |
| stride / bpp | 2944 / 32bpp | `/sys/class/graphics/fb0/*` |
| backlight | PMIC（MT6328） | 原厂 DTB |

这三个帧缓冲参数是主线阶段最重要的实测收获，也是当时判断"显示该往哪写"的唯一依据。

## 传感器

| 类型 | 存在 | 型号线索 |
|---|---|---|
| 加速度 | 是 | MC3410（原厂 DTB） |
| 光线 / 距离 | 是 | CM36652（原厂 DTB） |
| 电子罗盘 | 是 | AKM09911 |
| 陀螺仪 | **未在 build.prop 声明** | 原厂 DTB 有 ITG1010，但系统未启用 |

I2C 总线为 i2c2，触摸 EINT 为 GPIO10。

## 相机

| 项目 | 值 |
|---|---|
| 配置 | 前 + 后，`camera.disable_zsl_mode=1` |
| HAL 形态 | MTK legacy HAL1（`camera.mt6735.so`） |
| 相关设备节点 | `/dev/GAF001AF`（主摄）、`/dev/DW9714AF`（VCM 马达） |

Android 8.1 上需要 `TARGET_HAS_LEGACY_CAMERA_HAL1 := true` 才能让这套 blob 跑起来。

## 连接

| 项目 | 值 |
|---|---|
| WiFi/BT | MTK WMT combo，`/dev/wmtWifi`，固件 `WIFI_RAM_CODE_6735` |
| NFC | pn54x（`nfc_nci.pn54x.default.so`） |
| GPS | MTK agpsd（`/system/bin/mtk_agpsd`） |
| USB | MTK musb，默认 `persist.sys.usb.config=mass_storage` |

## Vendor HAL 清单（原厂 5.1）

`system/lib/hw/` 与 `system/lib64/hw/` 下均有：

```
audio.primary.mt6735.so   audio_policy.default.so   bluetooth.default.so
camera.mt6735.so          gps.default.so            gralloc.mt6735.so
hwcomposer.mt6735.so      lights.default.so         memtrack.mt6735.so
sensors.mt6735.so         power.default.so          vibrator.default.so
nfc_nci.pn54x.default.so  keystore.default.so       audio.usb.default.so
```

注意 `hwcomposer.mt6735.so` 是 **HWC1**，Android 8+ 需要 HWC2 —— 同 SoC 的社区设备树
（Coolpad `mt6735-common` 的 lineage-15.1）已通过 `TARGET_USES_HWC2` + MTK HWC 1.4.1 解决，
可直接参照。

## 已知的 LK 怪癖

| 现象 | 说明 |
|---|---|
| `fastboot boot` 报 `low power, need battery charging` | 电量计误报，电池实际 98%。判断在 LK 的 download 路径里，无法绕过 |
| `adb reboot recovery` 不可靠 | 多数情况要按物理键组合进 fastboot / recovery |
| 看门狗 | 内核挂住约 10 秒后被 WDT 复位，`androidboot.bootreason=wdt_by_pass_pwk` |
| 无 UART | SoC 的 UART0 在 0x11002000，但板子上没有测试点，**没有任何串口日志可看** |
