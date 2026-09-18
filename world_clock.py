"""World Clock 1.1.0 — Windows desktop cards."""
import copy
import json
import math
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt, QTimer, QRectF, QStandardPaths, QLockFile
from PySide6.QtGui import QColor, QFont, QPainter, QIcon, QPixmap, QPainterPath
from PySide6.QtWidgets import (QApplication, QWidget, QMenu, QMessageBox, QSystemTrayIcon,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox, QDialogButtonBox,
    QCheckBox, QComboBox, QColorDialog, QPushButton, QLineEdit, QListWidget, QFileDialog)
from clock_core import (VERSION, PRESETS, SHOW_DEFAULTS, WEEK, normalize, time_data,
    sun_period, parse_weather, weather_label, load_settings, save_settings,
    startup_enabled, set_startup)
from network_services import Network


class CityDialog(QDialog):
    def __init__(self, network, parent=None):
        super().__init__(parent)
        self.network, self.result_city, self.reply = network, None, None
        self.generation = 0
        self.setWindowTitle('添加城市 · 联网搜索')
        self.resize(440, 420)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('输入城市名；中文无结果时，可尝试英文或拼音。'))
        row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText('例如：Lusaka、上海、London')
        row.addWidget(self.query)
        button = QPushButton('搜索')
        button.clicked.connect(self.search)
        self.query.returnPressed.connect(self.search)
        row.addWidget(button)
        layout.addLayout(row)
        self.status = QLabel('常用城市（无需搜索）')
        layout.addWidget(self.status)
        self.list = QListWidget()
        self.rows = list(PRESETS)
        self.fill()
        layout.addWidget(self.list)
        self.list.itemDoubleClicked.connect(self.accept_city)
        layout.addWidget(QLabel('城市：GeoNames via Open-Meteo · 天气：Open-Meteo'))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept_city)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.finished.connect(self.stop_request)

    def fill(self):
        self.list.clear()
        for city in self.rows:
            self.list.addItem(f"{city['name']} · {city.get('region', '')} · {city['zone']}")
        if self.rows: self.list.setCurrentRow(0)

    def stop_request(self, _=None):
        self.generation += 1
        if self.reply:
            self.reply.abort()
            self.reply = None

    def search(self):
        query = self.query.text().strip()
        if len(query) < 2:
            self.status.setText('请输入至少两个字符。')
            return
        self.stop_request()
        generation = self.generation
        self.status.setText('正在搜索…')
        self.rows = []
        self.fill()
        def done(data, error):
            if generation != self.generation: return
            self.reply = None
            if error:
                self.status.setText(error)
                return
            for item in data.get('results', []):
                try:
                    zone = item['timezone']
                    ZoneInfo(zone)
                    region = ' / '.join(dict.fromkeys(x for x in [item.get('admin1'), item.get('country')] if x))
                    self.rows.append(dict(name=item['name'], region=region, zone=zone,
                                          lat=item['latitude'], lon=item['longitude']))
                except (KeyError, ValueError, TypeError):
                    continue
            self.fill()
            self.status.setText(f'找到 {len(self.rows)} 个结果，请按地区选择。' if self.rows else '无结果，可尝试英文或拼音。')
        self.reply = self.network.search(query, done)

    def accept_city(self, *_):
        index = self.list.currentRow()
        if 0 <= index < len(self.rows):
            self.result_city = self.rows[index]
            self.accept()


class CardSettings(QDialog):
    def __init__(self, clock):
        super().__init__(clock)
        self.clock = clock
        self.original = copy.deepcopy(clock.state)
        self.setWindowTitle('卡片设置 · ' + clock.state['name'])
        self.resize(380, 470)
        layout = QVBoxLayout(self)
        self.top = QCheckBox('始终置顶')
        self.top.setChecked(clock.state['top'])
        self.top.toggled.connect(lambda value: clock.set_top(value))
        layout.addWidget(self.top)
        layout.addWidget(QLabel('外观 / 卡片颜色'))
        self.mode = QComboBox()
        for title, value in [('跟随系统', 'system'), ('白天（浅色）', 'light'), ('夜晚（深色）', 'dark')]:
            self.mode.addItem(title, value)
        self.mode.setCurrentIndex(self.mode.findData(clock.state['theme']))
        self.mode.currentIndexChanged.connect(lambda _: self.preview('theme', self.mode.currentData()))
        layout.addWidget(self.mode)
        self.custom = QCheckBox('使用自定义卡片颜色（关闭则跟随上方外观）')
        self.custom.setChecked(clock.state['color_mode'] == 'custom')
        self.custom.toggled.connect(lambda value: self.preview('color_mode', 'custom' if value else 'system'))
        layout.addWidget(self.custom)
        color = QPushButton('选择卡片颜色…')
        color.clicked.connect(self.choose_color)
        layout.addWidget(color)
        layout.addWidget(QLabel('背景透明度：0% 不透明，100% 全透明；文字保持可见。'))
        row = QHBoxLayout()
        slider, number = QSlider(Qt.Orientation.Horizontal), QSpinBox()
        slider.setRange(0, 100)
        number.setRange(0, 100)
        number.setSuffix('%')
        slider.setValue(clock.state['transparency'])
        number.setValue(slider.value())
        slider.valueChanged.connect(number.setValue)
        number.valueChanged.connect(slider.setValue)
        slider.valueChanged.connect(lambda value: self.preview('transparency', value))
        row.addWidget(slider)
        row.addWidget(number)
        layout.addLayout(row)
        layout.addWidget(QLabel('显示内容'))
        labels = dict(city='城市名称', region='地区 / 国家', date='日期', weekday='星期',
                      offset='与电脑本地的时差', weather='天气 / 温度', seconds='秒',
                      sun='太阳 / 月亮', sun_times='日出 / 日落时间')
        for i, (key, label) in enumerate(labels.items()):
            if i % 2 == 0:
                row = QHBoxLayout()
                layout.addLayout(row)
            box = QCheckBox(label)
            box.setChecked(clock.state['show'][key])
            box.toggled.connect(lambda value, k=key: self.toggle_show(k, value))
            row.addWidget(box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def preview(self, key, value):
        self.clock.state[key] = value
        self.clock.update()

    def toggle_show(self, key, value):
        self.clock.state['show'][key] = value
        self.clock.resize_card()

    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.clock.state['color']), self, '选择卡片颜色')
        if color.isValid():
            self.clock.state['color'] = color.name()
            self.custom.setChecked(True)
            self.clock.update()

    def reject(self):
        self.clock.state = self.original
        self.clock.set_top(self.original['top'])
        self.clock.resize_card()
        self.clock.manager.save()
        super().reject()


class Clock(QWidget):
    def __init__(self, manager, state):
        super().__init__()
        self.manager, self.state = manager, normalize(state)
        self.drag_offset = None
        self.pending = False
        self.retry_at = 0
        self.weather_error = ''
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool |
            (Qt.WindowType.WindowStaysOnTopHint if self.state['top'] else Qt.WindowType.Widget))
        self.setWindowTitle(self.state['name'] + ' · 世界时钟')
        self.resize_card()
        self.move(self.state['x'], self.state['y'])
        self.keep_on_screen()
        QApplication.styleHints().colorSchemeChanged.connect(self.theme_changed)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(250)

    def theme_changed(self, _):
        self.update()

    def resize_card(self):
        show = self.state['show']
        rows = int(show['city'] or show['region'] or show['sun'])
        rows += int(show['date'] or show['weekday'] or show['offset'])
        rows += int(show['weather']) + int(show['sun_times'])
        self.setFixedSize(256, 68 + 22 * rows)
        self.update()

    def keep_on_screen(self):
        if not any(s.availableGeometry().contains(self.geometry()) for s in QApplication.screens()):
            rect = QApplication.primaryScreen().availableGeometry()
            self.move(rect.x() + 40, rect.y() + 40)

    def background(self):
        dark = self.state['theme'] == 'dark' or (self.state['theme'] == 'system' and
            QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark)
        color = QColor(self.state['color']) if self.state['color_mode'] == 'custom' else QColor('#262c35' if dark else '#dee2e6')
        if not color.isValid(): color = QColor('#dee2e6')
        luminance = 0.2126 * color.redF() + 0.7152 * color.greenF() + 0.0722 * color.blueF()
        return color, luminance < 0.5

    def paintEvent(self, event):
        now, delta = time_data(self.state['zone'])
        show, weather = self.state['show'], self.state.get('weather', {})
        day, rise, setting = sun_period(weather, self.state['zone'], now)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        background, dark = self.background()
        background.setAlpha(round(255 * (100 - self.state['transparency']) / 100))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(background)
        p.drawRoundedRect(QRectF(1, 1, self.width()-2, self.height()-2), 17, 17)
        foreground, muted = QColor('#f4f6fa' if dark else '#202631'), QColor('#c8d0dc' if dark else '#525e70')
        def text(line, y, height, size, bold=False, color=None, right_margin=12):
            p.setPen(color or foreground)
            p.setFont(QFont('Microsoft YaHei UI' if size < 20 else 'Segoe UI', size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            line = p.fontMetrics().elidedText(line, Qt.TextElideMode.ElideRight, self.width()-12-right_margin)
            p.drawText(QRectF(12, y, self.width()-12-right_margin, height), Qt.AlignmentFlag.AlignCenter, line)
        y = 9
        if show['city'] or show['region'] or show['sun']:
            title = ' · '.join(x for x in [self.state['name'] if show['city'] else '',
                              self.state.get('region', '') if show['region'] else ''] if x)
            text(title, y, 22, 10, True, right_margin=32 if show['sun'] else 12)
            if show['sun']:
                p.setPen(muted)
                p.setBrush(muted)
                x = self.width()-24
                if day is True:
                    p.drawEllipse(QRectF(x-4, y+7, 8, 8))
                    for angle in range(0, 360, 45):
                        a = math.radians(angle)
                        p.drawLine(round(x+6*math.cos(a)), round(y+11+6*math.sin(a)),
                                   round(x+8*math.cos(a)), round(y+11+8*math.sin(a)))
                elif day is False:
                    path = QPainterPath()
                    path.addEllipse(QRectF(x-6, y+5, 12, 12))
                    cut = QPainterPath()
                    cut.addEllipse(QRectF(x-1, y+2, 12, 12))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawPath(path.subtracted(cut))
                else:
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawEllipse(QRectF(x-5, y+6, 10, 10))
            y += 22
        text(now.strftime('%H:%M:%S' if show['seconds'] else '%H:%M'), y, 48, 28, True)
        y += 48
        footer = [now.strftime('%Y/%m/%d') if show['date'] else '', WEEK[now.weekday()] if show['weekday'] else '', delta if show['offset'] else '']
        if any(footer):
            text('  '.join(x for x in footer if x), y, 22, 8, color=muted)
            y += 22
        if show['weather']:
            if weather.get('temp') is not None:
                stale = self.weather_error or time.time()-weather.get('fetched', 0) > 3600
                line = f"{weather['temp']:.0f}°C  {weather_label(weather.get('code'))}" + (' · 缓存' if stale else '')
            else:
                line = self.weather_error or ('天气更新中…' if 'lat' in self.state else '请选择城市以获取天气')
            text(line, y, 22, 9, color=muted)
            y += 22
        if show['sun_times']:
            if rise and setting:
                zone = ZoneInfo(self.state['zone'])
                line = f"日出 {datetime.fromtimestamp(rise, zone):%H:%M}   日落 {datetime.fromtimestamp(setting, zone):%H:%M}"
            else: line = '日出 / 日落时间暂无数据'
            text(line, y, 22, 8, color=muted)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self.drag_offset)

    def mouseReleaseEvent(self, event):
        if self.drag_offset is not None:
            self.drag_offset = None
            self.keep_on_screen()
            self.manager.save()

    def set_top(self, enabled):
        self.state['top'] = enabled
        pos = self.pos()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
        self.move(pos)
        self.show()

    def settings(self):
        dialog = CardSettings(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.manager.save()
        dialog.deleteLater()
        self.manager.refresh_weather()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction('卡片设置（显示内容 / 颜色 / 透明度）…', self.settings)
        menu.addAction('添加城市…', self.manager.choose_city)
        menu.addAction('更换城市…', lambda: self.manager.choose_city(self))
        menu.addAction('立即更新天气', lambda: self.manager.refresh_weather(force=True, target=self))
        menu.addAction('保存卡片位置和设置', self.manager.save_notice)
        menu.addSeparator()
        menu.addAction('移除此时钟', lambda: self.manager.remove(self))
        menu.addAction('退出全部时钟', QApplication.instance().quit)
        menu.exec(event.globalPos())


class Manager:
    def __init__(self, app, path=None, online=True):
        self.app, self.clocks = app, []
        self.online = online
        self.network = Network(app)
        self.path = path or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)) / 'clocks.json'
        try:
            states = load_settings(self.path)
        except (OSError, ValueError, TypeError, AttributeError):
            states = []
            if self.path.exists():
                backup = self.path.with_name('clocks-unreadable-' + str(int(time.time())) + '.json')
                try: backup.write_bytes(self.path.read_bytes())
                except OSError: pass
        for state in states: self.add(state)
        if not self.clocks:
            for i, city in enumerate(PRESETS[:3]):
                self.add({**city, 'x': 160 + i * 272, 'y': 40})
        pix = QPixmap(32, 32)
        pix.fill(QColor('#287eac'))
        p = QPainter(pix)
        p.setPen(QColor('white'))
        p.drawEllipse(5, 5, 22, 22)
        p.drawLine(16, 8, 16, 16)
        p.drawLine(16, 16, 23, 19)
        p.end()
        app.setWindowIcon(QIcon(pix))
        self.tray = QSystemTrayIcon(QIcon(pix), app)
        self.tray.setToolTip('世界时钟 ' + VERSION)
        self.menu = QMenu()
        self.menu.addAction('添加城市（联网搜索）…', self.choose_city)
        self.menu.addAction('显示全部时钟', self.show_all)
        self.menu.addAction('保存当前位置和设置到本地', self.save_notice)
        self.menu.addAction('导出设置文件…', self.export_settings)
        self.menu.addAction('立即更新全部天气', lambda: self.refresh_weather(force=True))
        self.auto = self.menu.addAction('开机自启')
        self.auto.setCheckable(True)
        self.menu.aboutToShow.connect(lambda: self.auto.setChecked(startup_enabled()))
        self.auto.triggered.connect(self.toggle_startup)
        self.menu.addAction('关于 / 天气数据来源', self.about)
        self.menu.addSeparator()
        self.menu.addAction('退出', app.quit)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(lambda reason: self.show_all() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        self.tray.show()
        app.aboutToQuit.connect(self.save)
        self.weather_timer = QTimer(app)
        self.weather_timer.timeout.connect(self.refresh_weather)
        self.weather_timer.start(60000)
        QTimer.singleShot(100, self.refresh_weather)
        self.show_all()

    def add(self, state):
        clock = Clock(self, state)
        self.clocks.append(clock)
        clock.show()

    def show_all(self):
        for clock in self.clocks:
            clock.keep_on_screen()
            clock.show()
            clock.raise_()

    def choose_city(self, target=None):
        dialog = CityDialog(self.network)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            city = dialog.result_city
            if isinstance(target, Clock):
                target.state.update(city)
                target.state.pop('weather', None)
                target.retry_at = 0
                target.weather_error = ''
                target.setWindowTitle(city['name'] + ' · 世界时钟')
                target.update()
            else:
                self.add({**city, 'x': 100 + 24 * len(self.clocks), 'y': 180})
            self.save()
            self.refresh_weather(force=True)
        dialog.deleteLater()

    def refresh_weather(self, force=False, target=None):
        if not self.online: return
        for clock in ([target] if target else list(self.clocks)):
            if clock not in self.clocks or clock.pending or 'lat' not in clock.state: continue
            show = clock.state['show']
            if not force and not any(show[k] for k in ('weather', 'sun', 'sun_times')): continue
            now = time.time()
            cache = clock.state.get('weather', {})
            if not force and (clock.retry_at > now or now-cache.get('fetched', 0) < 900): continue
            clock.pending = True
            identity = tuple(clock.state.get(k) for k in ('lat', 'lon', 'zone'))
            def done(data, error, card=clock, identity=identity):
                if card not in self.clocks: return
                card.pending = False
                if identity != tuple(card.state.get(k) for k in ('lat', 'lon', 'zone')):
                    self.refresh_weather(force=True, target=card)
                    return
                if not error:
                    try:
                        card.state['weather'] = parse_weather(data, card.state['zone'], time.time())
                        card.weather_error = ''
                        self.save()
                    except (KeyError, TypeError, ValueError): error = '天气数据暂不可用'
                if error:
                    card.weather_error = error
                    card.retry_at = time.time() + 300
                card.setToolTip('天气：Open-Meteo · 城市：GeoNames\n' + ('上次更新：' + datetime.fromtimestamp(card.state.get('weather', {}).get('fetched', 0)).strftime('%m/%d %H:%M') if card.state.get('weather') else '暂无天气数据') + '\n' + card.weather_error)
                card.update()
            self.network.weather(clock.state, done)

    def remove(self, clock):
        if len(self.clocks) == 1:
            self.app.quit()
            return
        self.clocks.remove(clock)
        clock.close()
        clock.deleteLater()
        self.save()

    def save(self):
        for clock in self.clocks: clock.state.update(x=clock.x(), y=clock.y())
        try:
            save_settings(self.path, [clock.state for clock in self.clocks])
            return True
        except OSError as exc:
            self.tray.showMessage('设置未保存', str(exc))
            return False

    def save_notice(self):
        if self.save(): self.tray.showMessage('已保存', '卡片位置和设置已保存到：\n' + str(self.path))

    def export_settings(self):
        filename, _ = QFileDialog.getSaveFileName(None, '导出当前位置和设置', 'world-clock-settings.json', 'JSON (*.json)')
        if filename:
            self.save()
            try: save_settings(Path(filename), [c.state for c in self.clocks])
            except OSError as exc: QMessageBox.warning(None, '导出失败', str(exc))

    def toggle_startup(self, enabled):
        try: set_startup(enabled)
        except OSError as exc:
            self.auto.setChecked(startup_enabled())
            QMessageBox.warning(None, '开机自启设置失败', str(exc))

    def about(self):
        QMessageBox.information(None, '世界时钟 ' + VERSION,
            '天气及日出日落：Open-Meteo（CC BY 4.0）\nhttps://open-meteo.com/\n'
            '城市搜索：GeoNames via Open-Meteo（CC BY 4.0）\nhttps://www.geonames.org/\n\n'
            '天气约每 15 分钟更新；网络失败时保留并标记缓存。\n'
            '太阳/月亮按当地当天日出日落时间计算；无有效数据时显示空心圆。\n'
            '仅发送所选城市坐标、时区或搜索词，不读取设备定位。\n'
            '开机自启默认关闭，启用后请保留程序在当前位置。')


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('WorldClockPython')
    app.setQuitOnLastWindowClosed(False)
    if len(sys.argv) == 3 and sys.argv[1] in ('--smoke-test', '--network-test'):
        from self_test import run_smoke, run_network
        (run_smoke if sys.argv[1] == '--smoke-test' else run_network)(app, Path(sys.argv[2]))
        return
    folder = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    folder.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(folder / 'world-clock.lock'))
    if not lock.tryLock(100):
        if '--startup' not in sys.argv:
            QMessageBox.information(None, '世界时钟', '世界时钟已经在运行，请从系统托盘打开。')
        return
    manager = Manager(app)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
