# 刷机与救砖手册

**铁律：只动 `boot` 和 `recovery`，绝不碰 `preloader` / `lk` / `tee`。**
动到前三个的任何一个，SP Flash Tool 也救不回来（那需要 BROM 模式短接）。

原厂包 `gionee-gn3002_SV1.0_5.1_2017.10.11.zip` 必须留着，那是唯一可靠的救援手段。

## 分区与设备路径

```
/dev/block/platform/mtk-msdc.0/by-name/boot       -> mmcblk0p7   16 MB
/dev/block/platform/mtk-msdc.0/by-name/recovery   -> mmcblk0p8   16 MB
/dev/block/platform/mtk-msdc.0/by-name/system                  3 GB
```

## 0. 先备份（做一次，存到电脑上）

```bash
export MSYS_NO_PATHCONV=1     # Git Bash 下必须，否则路径会被改写
adb start-server
adb shell "su -c 'dd if=/dev/block/mmcblk0p7 of=/data/local/tmp/boot.img bs=1048576'"
adb shell "su -c 'dd if=/dev/block/mmcblk0p8 of=/data/local/tmp/recovery.img bs=1048576'"
adb pull /data/local/tmp/boot.img     work/backup/boot-backup.img
adb pull /data/local/tmp/recovery.img work/backup/recovery-backup.img
```

原厂 boot.img 也能直接从 ROM 包里取（`rom/boot.img`，8,110,080 字节）。

## 1. 刷入（推荐：adb + dd）

已验证最可靠的方式。因为 LK 的 `fastboot` 有低电量误报，这条路才是主力。

```bash
export MSYS_NO_PATHCONV=1
adb push my-boot.img /data/local/tmp/
adb shell "su -c 'dd if=/data/local/tmp/my-boot.img of=/dev/block/mmcblk0p7 bs=1048576; sync'"

# 立刻回读校验
adb shell "su -c 'dd if=/dev/block/mmcblk0p7 bs=<镜像字节数> count=1 | md5sum'"
md5sum my-boot.img        # 两个 md5 必须一致
```

**每次写完都要回读校验**，这一步能省掉一次变砖。

## 2. 关于 fastboot（为什么基本用不了）

| 现象 | 说明 |
|---|---|
| `fastboot boot` 报 `low power, need battery charging` | LK 的电量计误报（系统里实测 98%）。判断在 LK 的 download 路径，无法绕过 |
| `adb reboot bootloader` 不生效 | 这台 LK 多数情况只认物理按键组合 |
| `fastboot devices` 时有时无 | MTK LK 不支持 USB 热插拔，必须保持线插着重新进 fastboot |

结论：**不要在这上面花时间**。要试镜像就用 dd 写分区。

## 3. 救援（已验证可行）

上一次变砖（boot 分区里是无法启动的内核，系统反复被看门狗复位）就是用这套流程救回来的。

1. 下载并安装 **SP Flash Tool** 与 **MTK USB VCOM 驱动**
2. 打开原厂包里的 `MT6735_Android_scatter.txt`
3. 选择 **Download Only**（或 Firmware Upgrade，后者会清数据）
4. 手机完全关机（长按电源 10-15 秒确认断电）
5. 点 Download，然后插 USB
6. 等待全部进度条变绿，最后出现绿色圆圈

注意：

- 只救 boot/recovery 时，可以在 SP Flash Tool 里取消勾选其他分区，**更安全**
- 不要勾 `preloader`，除非确实需要（刷错 preloader 会导致无法再进下载模式）
- 刷完第一次开机会比较慢（要重新生成 ART 缓存）

## 4. 看系统有没有起来

Android 系统（移植期最常用）：

```bash
adb devices
adb logcat -d > boot.log          # 完整日志
adb shell dmesg | tail -50        # 内核日志
adb shell getprop sys.boot_completed
```

失败时先看这几项：

```bash
adb shell cat /proc/cmdline | tr ' ' '\n' | grep -E 'bootreason|boot_mode'
# wdt_by_pass_pwk = 被看门狗复位（内核挂住过）
```

## 5. 常见故障

| 现象 | 可能原因 |
|---|---|
| 屏幕无输出、无 USB、约 10 秒后自动重启 | 内核没起来或被看门狗咬死；查 `bootreason` |
| 卡在开机动画 | Android 框架层 HAL 启动失败；`logcat` 里搜 `FATAL` / `avc: denied` |
| 能开机但黑屏 | 显示 HAL 或面板配置错；`dmesg` 里找 `mtkfb` / `lcm` |
| 反复重启 | SELinux `neverallow` 或 init 服务崩溃；看 `last_kmsg` / `pstore` |
| 无信号 | `nvdata` 被格式化或基带固件缺失；**绝对不要格式化 nvdata** |
| 进了 recovery 但 adb 不通 | 原厂 recovery 不开 adbd，属正常；用 TWRP 或音量键菜单 |
