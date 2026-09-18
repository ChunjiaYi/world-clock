# 世界时钟 · v1.1.0

适用于 Windows 11 x64 的半透明桌面时钟，支持世界城市、联网天气和日出日落。

## 下载与升级

在 [Releases](https://github.com/ChunjiaYi/world-clock/releases/latest) 下载 `WorldClock-v1.1.0-windows-x64.zip`，完整解压后双击文件夹中的 `WorldClock.exe`。无需安装 Python。这是免安装便携包，请保留同目录下的 `_internal` 文件夹，不要单独移动 EXE。

升级时从系统托盘退出旧版，将新版完整解压到独立文件夹并运行。旧版城市、位置、透明度会自动迁移；v1.1.0 首次迁移默认启用置顶。已启用开机自启的用户如更换 EXE 位置，请在新版中关闭再开启开机自启。

## v1.1.0 功能

1. **开机自启**：托盘右键勾选，默认关闭，仅影响当前 Windows 用户，无需管理员权限。
2. **联网天气和日出日落**：每 15 分钟更新，太阳/月亮按城市当天日出日落切换。极昼极夜可使用服务提供的当前昼夜状态；无有效数据时显示空心圆，不猜测昼夜。
3. **默认置顶**：每张卡片可在设置中关闭。
4. **显示内容开关**：城市、地区/国家、日期、星期、时差、天气、太阳/月亮、日出日落时间。
5. **本地保存**：拖动后自动保存；托盘右键可手动保存全部位置和设置，也可导出 JSON。
6. **联网搜索城市**：输入中文、英文或拼音，结果显示地区、国家和时区，避免同名城市选错。
7. **显示/隐藏秒**：每张卡片独立设置。
8. **自定义卡片颜色**：支持颜色选择器，或跟随系统浅色/深色；背景透明度 0–100%，文字保持可见。

## 操作

- 左键拖动卡片。
- 卡片右键 → **卡片设置**，调整外观和显示内容，实时预览；取消会恢复原设置。
- 卡片右键 → 添加/更换城市、立即更新天气、保存设置。
- 系统托盘右键 → 开机自启、保存位置和设置、导出、显示全部、更新天气、退出。
- 日期旁时差以 Windows 本地时区为基准，自动处理夏令时和半小时时区。
- 设置保存在 `%APPDATA%\WorldClockPython\clocks.json`，包含城市坐标与天气缓存。
- 程序不修改系统时间、不读取设备定位、不自动开启开机自启。离线时仍可看时间；已有天气会显示“缓存”。

天气及城市服务：Open-Meteo / GeoNames；天气数据 CC BY 4.0，按接口可用性更新，主要用于个人非商业使用。城市搜索词、所选城市坐标和时区会发送给 Open-Meteo，不发送个人设置文件。数据来源也可在托盘“关于”中查看。

## QtCore 启动错误修复

v1.0 的本地打包环境曾将其他工具目录中的运行库带入 EXE。v1.1.0 固定 Qt 依赖版本，在清理后的 DLL 搜索路径下打包，并检查依赖清单，避免混入不兼容的运行库。

## 从源码运行或打包

推荐官方 Python 3.13 x64，在独立虚拟环境中执行：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-build.txt
.venv\Scripts\python world_clock.py
.venv\Scripts\python build.py
```

也可双击 `start.bat`（首次联网安装依赖）。打包输出为 `dist/WorldClock/WorldClock.exe`，发布时需包含整个 `dist/WorldClock` 文件夹。

验证最终 EXE（测试不会修改个人设置或开机自启）：

```powershell
Start-Process -FilePath .\dist\WorldClock\WorldClock.exe -ArgumentList '--smoke-test', 'smoke-result.txt' -Wait
Get-Content smoke-result.txt
```

## 实现范围

独立悬浮窗口，不嵌入 Explorer 桌面，也不是 Win+W 面板插件。背景是半透明填色，无毛玻璃模糊。本版本未做商业代码签名。

第三方组件与许可证见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
