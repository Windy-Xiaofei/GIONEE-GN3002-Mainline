# Android 移植计划

目标：给 GN3002 做一套**能给日常用**的 Android，而不是能开机就完事的实验品。

## 为什么选 8.1 而不是直接上 9

| 依据 | 事实 |
|---|---|
| MT6735 最远的现成设备树 | Coolpad `mt6735-common` 的 **lineage-15.1**（8.1），306 个文件，持续维护到 2026-10 |
| MT6735 的 9 代设备树 | 搜遍 GitHub 为 **0**，没人做过 |
| 8.1 与 9 的门槛差异 | 很小：两者都要 HWC2、gralloc1、严格 SELinux。8.1 已把这些坑填过 |
| 8.1 与 7.1 的差异 | 很大：HWC2、HIDL 服务、audio policy XML、linker namespace |

所以策略是：**用 8.1 的成熟骨架把机器跑起来，再推 9**。先做 7.1 或先做 8.1 的中间态都是浪费。

## 技术路线

```
原厂 5.1 内核（预编译 Image.gz-dtb）  ← 面板/触摸/传感器/基带/WiFi 驱动都在这
        +
LineageOS 15.1 框架（源码编译）      ← 新系统
        +
原厂 5.1 vendor blobs（从 system.img 提取）  ← MTK 的 HAL 与固件
```

关键决策：**不做内核开发**，用 `TARGET_PREBUILT_KERNEL` 指向原厂内核。这台机器没有 3.10
源码，而且原厂内核把这些硬件都点亮了，重写没有收益。

同 SoC 的 Coolpad 树已经把 MTK 在 8.1 上的坑填平了，可直接参照的部分：

- `TARGET_USES_HWC2 := true` + `MTK_HWC_VERSION := 1.4.1`（HWC1 到 HWC2 的桥）
- `TARGET_HAS_LEGACY_CAMERA_HAL1 := true`（让 MTK 相机 blob 在 8.1 上能跑）
- **60 多条 `TARGET_LD_SHIM_LIBS`**（bionic / icu / ui / omx / socket 的兼容 shim）
- 全套 MTK daemon 的 SELinux policy（ccci / nvram / thermal / wmt / rild / agpsd …）
- HIDL 服务：audio@2.0、composer@2.1、camera.provider@2.4、wifi@1.0、bluetooth@1.0-service.mtk

我们与它的差异只在**机型层**：面板 `tm_ft8606`、触摸 FT8606、双卡配置、分区大小、按键布局。

## 里程碑

### M1 — TWRP（先做这个）

- 产物：`recovery.img`
- 判据：能进 recovery、显示正常、触摸可用、adb 可用
- 意义：验证设备树骨架、fstab、预编译内核打包；recovery 是独立分区，**刷坏不影响系统**，
  而且顺手建立一条救援通道
- 预估：源码约 12GB，构建 40-60 分钟

### M2 — LineageOS 15.1 首启

- 判据：开机进系统，显示 + 触摸 + adb + logcat 正常
- 预估：构建 3-4 小时

### M3 — 功能补齐

按"能当手机用"的优先级：

1. WiFi（`/dev/wmtWifi` + `WIFI_RAM_CODE_6735`）
2. 音频（`audio.primary.mt6735.so` + `audio_device.xml`）
3. RIL（mtkrild + ccci，双卡 dsda）
4. 相机（legacy HAL1）
5. 传感器、亮度、按键、充电显示

每项独立验收，失败不影响其他项。

### M4 — Android 9（LineageOS 16.0）

在 M3 基础上把设备树从 15.1 推到 16.0。已知增量：

- SELinux 更严（`neverallow` 会挡住老 blob 的很多操作）
- HIDL 版本对齐（audio 可能需要 @4.0 / @5.0）
- `android.hardware.radio` 接口变化
- audio policy 全面 XML 化

## 仓库结构（计划）

```
device/gionee/gbl7356/          # 机型层（本仓库主战场）
  BoardConfig.mk                # 预编译内核、分区大小、HWC2、shim 列表
  gbl7356.mk                    # 产品定义、权限、keylayout
  rootdir/fstab.mt6735          # 沿用原厂分区表
  rootdir/init.mt6735.rc        # 从原厂 ramdisk 适配
  configs/                      # audio_device.xml、media_codecs.xml、WPS 配置
  sepolicy/                     # 机型-specific policy
vendor/gionee/gbl7356/          # 从原厂 system.img 提取的 blobs
local_manifests/                # 引入 mt6735-common 与 LineageOS 15.1
```

## CI 方案

公开仓库 + GitHub Actions（公开仓库不计时长）。

- M1 阶段：TWRP 最小 manifest（约 12GB 源码）
- M2 起：LineageOS 15.1 完整 manifest（约 30GB 源码）
- Runner 根分区只有约 14GB 空闲，构建目录需要落到 `/mnt`（约 65GB）
- 单个 job 有 6 小时上限，15.1 构建需在 4 小时内完成，否则要拆缓存

## 风险与对策

| 风险 | 对策 |
|---|---|
| 预编译内核缺少 8.1 需要的特性（如 sdcardfs） | 先用 FUSE 兼容路径；实在不行再找同 SoC 的 3.10 源码编 |
| MTK blob 与 8.1 的 linker/SELinux 冲突 | 直接复用 Coolpad 树的 shim 与 policy，逐条对齐 |
| 相机在 8.1 上崩（clang 对齐问题） | 用 legacy HAL1；接受"相机最后做、可能做不出来" |
| CI 构建超时 | 先 TWRP 打通流程，再上完整 ROM；必要时用 ccache 或拆分 |
| 变砖 | 只动 boot / recovery，preloader / lk / tee 一律不碰；原厂包常备 |

## 不做的事

- 不为了"新版本号"牺牲可用性。目标是能打电话、能上网、能用相机
- 不在真机上盲试。每次改动先在 CI 出包，再用 logcat / dmesg 定位
- 不碰 NV 数据分区（nvdata 里有基带校准，格式化会导致无信号）
