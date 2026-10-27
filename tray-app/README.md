# 我的设备电量 2.3.0

Windows 10/11 x64 托盘电量工具。Electron + Python HID 后端，宋体、绿色语义配色、透明圆角弹窗。

- 点击托盘图标查看所有检测到的设备；每 60 秒自动刷新，也可点击底部文字刷新。
- 动态枚举设备，不固定展示三台；未支持的接收器明确标记“暂不支持电量读取”。
- 没有独立面板和设置页面；点击外部或 Esc 收起，右键托盘退出。
- 加入 Attack Shark R5 Ultra（373E:0046 / 0047）电量协议。协议模拟测试通过，尚待 R5 实机验证。

## 从源码运行

安装 Python 3.13 x64、Node.js 22 或更新版本，在本目录执行：

```powershell
py -3 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
cd desktop
npm ci
npm start
```

默认使用 tray-app/.venv/Scripts/python.exe；可用 BATTERY_PYTHON 环境变量指定其他解释器。

## 构建便携 EXE

在本目录运行 `./build.ps1`，产物位于 `dist/我的设备电量.exe`。不需要目标电脑安装 Python 或 Node.js；产物未做代码签名。

## 测试

在本目录运行：

```powershell
./.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_*.py'
./.venv/Scripts/python.exe -m unittest discover -s tests/protocols
node --test desktop/test/geometry.test.js
```

## 兼容与来源

不是所有无线设备都有统一电量协议，也不保证同品牌所有型号可用。支持范围和限制见 [兼容说明](兼容范围与协议来源.md)。本机验证过罗技、ROG OMNI 和雷蛇 Xbox 耳机；其他型号主要依赖上游实现与模拟测试。

- 基于 [yszyszysz233/2.4G-battery-viewer](https://github.com/yszyszysz233/2.4G-battery-viewer)；保留原项目在仓库根目录。
- providers 与协议测试主要来自 [HaloBattery](https://github.com/HeyOkay/HaloBattery)，提交 2251f0534a8e886c9692ead42056059b4f69d8c0，MIT。
- R5 协议参考 [attackshark-battery-bridge](https://github.com/maxboeer/attackshark-battery-bridge)，提交 2d77aeb5cd8a9fa3408416200cc86de61221f145，MIT。
- 第三方许可证和协议致谢位于 [licenses](licenses)。各来源保留原授权；本 fork 不替上游未声明许可的文件授予新许可证。
