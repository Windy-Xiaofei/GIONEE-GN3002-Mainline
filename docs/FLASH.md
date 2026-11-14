# 刷机与调试

全部操作都只碰 **boot 分区**。system / userdata / preloader / lk / tee 一概不动。

## 0. 先备份（只做一次）

```bash
adb devices
adb shell su -c 'dd if=/dev/block/by-name/boot of=/sdcard/boot-stock.img'
adb pull /sdcard/boot-stock.img
```

如果 `su` 不可用，用 TWRP 的 backup，或者 `adb shell` 里找 `/dev/block/platform/mtk-msdc.0/by-name/boot`。

## 1. 不刷写，直接从内存引导（推荐先试这个）

MTK 的 LK 支持 `fastboot boot`，镜像只进内存，掉电即恢复：

```bash
adb reboot bootloader
fastboot devices
fastboot boot boot.img
```

- 成功：屏幕（v2 之后）/ USB 串口有反应
- 失败：长按电源 10 秒强制重启，回到 LineageOS，flash 内容没变

## 2. 写入 boot 分区

```bash
fastboot flash boot boot.img
fastboot reboot
```

回滚：

```bash
fastboot flash boot boot-stock.img
```

## 3. 看内核有没有起来

v1 没有显示输出，判据是 **USB 串口**：

```bash
# 手机插在笔记本上
dmesg | tail -20          # 应该出现 cdc_acm 1-1:1.0: ttyACM0
screen /dev/ttyACM0 115200
# 或
picocom -b 115200 /dev/ttyACM0
```

进得去 shell 就说明：内核起来了、initramfs 跑了、USB gadget 正常。

如果连不上：

```bash
lsusb                     # 看有没有 1d6b:0104
dmesg | grep -i -E 'usb|musb|acm'
```

## 4. 抓 pstore（重启后还能看上次的日志）

```bash
adb shell su -c 'ls -l /sys/fs/pstore'
adb shell su -c 'cat /sys/fs/pstore/console-ramoops-0'
```

ramoops 区域在 0x43F10000，只有内核写到一半崩了才有内容。

## 5. 常见失败

| 现象 | 可能原因 |
|---|---|
| 完全黑屏、无 USB、10 秒后自动重启 | 内核没解压/没启动：LK 不认 Image.gz，改用裸 Image |
| 有 USB 设备但无 ttyACM | gadget 没绑定：musb 没进 peripheral 模式 |
| 内核起来但 initramfs panic | init 脚本或 busybox 链接问题 |
| 起来后立刻重启 | 内存节点写错，踩到保留区 |
