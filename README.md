# 世界时钟 · Windows 11

使用 Python + PySide6 制作的半透明圆角桌面悬浮卡片，默认显示北京、迪拜、卢萨卡（赞比亚）。

## 下载 EXE（无需 Python）

前往 [Releases](https://github.com/ChunjiaYi/world-clock/releases/latest)，下载 `WorldClock.exe`，双击即可运行。
Windows 11 x64；也可下载完整 ZIP，包含 EXE、使用说明及第三方许可证。

## 从源码启动

1. 安装 64 位 Python 3.10 或更新的兼容版本（推荐 3.12 或 3.13），安装时勾选 Add Python to PATH。
2. 将整个文件夹解压到可写的位置，双击 `start.bat`。
3. 首次启动会在当前文件夹创建 `.venv` 并联网安装依赖。以后可离线启动。

也可以在此文件夹打开终端，执行：

```powershell
python -m pip install -r requirements.txt
python world_clock.py
```

## 操作

- 左键拖动：移动单个卡片，松开后自动保存位置。
- 右键：添加/更换城市、始终置顶、外观模式、背景透明度、移除或退出。
- 背景透明度支持 0–100% 滑块和数字输入，实时预览；0% 不透明，100% 背景完全透明，文字保持可见。确定保存，取消恢复原值。
- 外观模式支持跟随系统、白天（浅色）、夜晚（深色）。新卡片默认跟随系统，Windows 的应用浅色/深色设置改变时自动切换，无需重启。原有深色卡片保留深色选择。
- 添加城市支持输入标准 IANA 时区，例如 `Africa/Lusaka`。
- 系统托盘右键可以重新显示所有卡片或退出。
- 日期右侧的时差，相对于 Windows 当前本地时区计算；支持半小时时差。
- 太阳/月亮仅表示当地 06:00–18:00 / 其余时间，不是天气或真实日出日落。
- 显示时间来自电脑系统时钟，采用 IANA 时区数据库自动换算夏令时。
- 城市、外观、位置保存在用户应用数据目录 `WorldClockPython/clocks.json`。

## 实现范围

这是独立的无边框桌面悬浮程序，不是 Win+W 小组件面板插件。默认不置顶，其他窗口可覆盖它；可通过右键启用置顶。没有使用 Explorer 桌面嵌入，Win+D 的行为由 Windows 管理，可从托盘重新显示。

背景是半透明填色，不是真实毛玻璃模糊。应用不修改壁纸，不默认设置开机启动。

## 技术参考

- Qt 透明窗口：https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QWidget.html
- Python 时区：https://docs.python.org/3/library/zoneinfo.html

Windows 通常不内置 IANA 时区数据库，因此依赖中包含 tzdata。

## 打包 EXE

在 Windows 的 Python 环境中执行：

```powershell
python -m pip install -r requirements-build.txt
python build.py
```

输出为 `dist/WorldClock.exe`。程序包含 Python、Qt 和时区数据库，运行时无需联网安装依赖。

打包后可运行独立启动检查（不会读取或修改个人时钟设置）：

```powershell
Start-Process -FilePath .\dist\WorldClock.exe -ArgumentList '--smoke-test', 'smoke-result.txt' -Wait
Get-Content smoke-result.txt
```

第三方组件说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
