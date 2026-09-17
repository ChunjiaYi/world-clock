"""Windows 11 translucent world clocks. Python 3.10+."""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PySide6.QtCore import Qt, QTimer, QRectF, QStandardPaths
from PySide6.QtGui import QColor, QFont, QPainter, QIcon, QPixmap, QActionGroup
from PySide6.QtWidgets import (QApplication, QWidget, QMenu, QInputDialog, QMessageBox,
                               QSystemTrayIcon, QDialog, QVBoxLayout, QHBoxLayout,
                               QLabel, QSlider, QSpinBox, QDialogButtonBox)

CITIES = {
    '北京': 'Asia/Shanghai', '迪拜': 'Asia/Dubai',
    '卢萨卡（赞比亚）': 'Africa/Lusaka', '科伦坡': 'Asia/Colombo',
    '新加坡': 'Asia/Singapore', '东京': 'Asia/Tokyo',
    '伦敦': 'Europe/London', '巴黎': 'Europe/Paris',
    '纽约': 'America/New_York', '洛杉矶': 'America/Los_Angeles',
    '悉尼': 'Australia/Sydney', '约翰内斯堡': 'Africa/Johannesburg',
    'UTC': 'UTC',
}
WEEK = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']


def time_data(zone, instant=None):
    instant = instant or datetime.now(timezone.utc)
    there = instant.astimezone(ZoneInfo(zone))
    local = instant.astimezone()
    minutes = round((there.utcoffset() - local.utcoffset()).total_seconds() / 60)
    if minutes == 0:
        difference = '本地同时间'
    else:
        h, m = divmod(abs(minutes), 60)
        difference = ('+' if minutes > 0 else '−') + f'{h}h' + (f'{m:02d}m' if m else '')
    return there, difference


class Clock(QWidget):
    def __init__(self, manager, state):
        super().__init__()
        self.manager, self.state = manager, state
        self.state.setdefault('theme', 'dark' if self.state.get('dark') else 'system')
        self.state.setdefault('transparency', round((255 - self.state.get('alpha', 210)) * 100 / 255))
        self.state['transparency'] = max(0, min(100, int(self.state['transparency'])))
        QApplication.styleHints().colorSchemeChanged.connect(self.system_theme_changed)
        self.drag_offset = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(220, 112)
        self.apply_flags()
        self.setWindowTitle(state['name'] + ' · 世界时钟')
        self.setToolTip('拖动调整位置 · 右键设置\n日/月图标仅表示当地 06:00–18:00，不是天气或日出日落')
        self.move(state.get('x', 300), state.get('y', 40))
        self.keep_on_screen()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(250)

    def apply_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.state.get('top', False):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def keep_on_screen(self):
        if not any(s.availableGeometry().contains(self.geometry()) for s in QApplication.screens()):
            r = QApplication.primaryScreen().availableGeometry()
            self.move(r.x() + 40, r.y() + 40)

    def paintEvent(self, event):
        now, diff = time_data(self.state['zone'])
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        dark = self.is_dark()
        c = QColor('#252930' if dark else '#d7d8d8')
        c.setAlpha(round(255 * (100 - self.state['transparency']) / 100))
        p.setBrush(c)
        p.drawRoundedRect(QRectF(1, 1, 218, 110), 17, 17)
        p.setPen(QColor('#f2f4f7' if dark else '#242727'))
        p.setFont(QFont('Microsoft YaHei UI', 10, QFont.Weight.DemiBold))
        title = self.state['name']
        title = p.fontMetrics().elidedText(title, Qt.TextElideMode.ElideRight, 174)
        p.drawText(QRectF(10, 10, 200, 22), Qt.AlignmentFlag.AlignCenter, title)
        # Draw the day/night indicator without depending on symbol fonts.
        p.setBrush(QColor('#bdc3cc' if dark else '#606666'))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(198, 17, 8, 8))
        if not 6 <= now.hour < 18:
            p.setBrush(c)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            p.drawEllipse(QRectF(201, 15, 7, 7))
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setPen(QColor('#f2f4f7' if dark else '#242727'))
        font = QFont('Segoe UI', 27, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(QRectF(4, 31, 212, 44), Qt.AlignmentFlag.AlignCenter, now.strftime('%H:%M:%S'))
        p.setFont(QFont('Microsoft YaHei UI', 8))
        p.setPen(QColor('#bdc3cc' if dark else '#606666'))
        p.drawText(QRectF(7, 79, 206, 20), Qt.AlignmentFlag.AlignCenter,
                   now.strftime('%Y/%m/%d') + '  ' + WEEK[now.weekday()] + '  ' + diff)

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

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction('添加城市…', self.manager.choose_city)
        menu.addAction('更换城市…', lambda: self.manager.choose_city(self))
        top = menu.addAction('始终置顶')
        top.setCheckable(True)
        top.setChecked(self.state.get('top', False))
        top.triggered.connect(self.toggle_top)
        themes = menu.addMenu('外观模式')
        group = QActionGroup(themes)
        group.setExclusive(True)
        for label, mode in [('跟随系统', 'system'), ('白天（浅色）', 'light'), ('夜晚（深色）', 'dark')]:
            action = themes.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.state['theme'] == mode)
            group.addAction(action)
            action.triggered.connect(lambda checked=False, m=mode: self.change('theme', m))
        menu.addAction(f"背景透明度：{self.state['transparency']}%…", self.edit_transparency)
        menu.addSeparator()
        menu.addAction('移除此时钟', lambda: self.manager.remove(self))
        menu.addAction('退出全部时钟', QApplication.instance().quit)
        menu.exec(event.globalPos())

    def is_dark(self):
        mode = self.state['theme']
        return mode == 'dark' or (mode == 'system' and
            QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark)

    def system_theme_changed(self, scheme):
        self.update()

    def edit_transparency(self):
        original = self.state['transparency']
        dialog = QDialog(self)
        dialog.setWindowTitle('背景透明度')
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('0% 不透明 · 100% 背景完全透明\n时间文字始终可见，拖动滑块即可预览。'))
        row = QHBoxLayout()
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(original)
        number = QSpinBox()
        number.setRange(0, 100)
        number.setSuffix('%')
        number.setValue(original)
        slider.valueChanged.connect(number.setValue)
        number.valueChanged.connect(slider.setValue)
        def preview(value):
            self.state['transparency'] = value
            self.update()
        slider.valueChanged.connect(preview)
        row.addWidget(slider)
        row.addWidget(number)
        layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.manager.save()
        else:
            preview(original)
        dialog.deleteLater()

    def change(self, key, value):
        self.state[key] = value
        self.update()
        self.manager.save()

    def toggle_top(self, checked):
        self.state['top'] = checked
        pos = self.pos()
        self.apply_flags()
        self.move(pos)
        self.show()
        self.manager.save()


class Manager:
    def __init__(self, app):
        self.app, self.clocks = app, []
        self.path = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)) / 'clocks.json'
        self.save_error_shown = False
        states = []
        if self.path.exists():
            try:
                states = json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(states, list):
                    states = []
            except (OSError, ValueError):
                pass
        for state in states:
            try:
                if not isinstance(state, dict) or not isinstance(state['name'], str):
                    continue
                ZoneInfo(state['zone'])
                for k in ('x', 'y', 'alpha'):
                    if k in state:
                        state[k] = int(state[k])
                state['alpha'] = max(60, min(255, state.get('alpha', 210)))
                self.add(state)
            except (KeyError, TypeError, ValueError, ZoneInfoNotFoundError):
                continue
        if not self.clocks:
            for i, name in enumerate(['北京', '迪拜', '卢萨卡（赞比亚）']):
                self.add({'name': name, 'zone': CITIES[name], 'x': 300 + i * 236, 'y': 40})
        pix = QPixmap(32, 32)
        pix.fill(QColor('#287eac'))
        p = QPainter(pix)
        p.setPen(QColor('white'))
        p.drawEllipse(5, 5, 22, 22)
        p.drawLine(16, 8, 16, 16)
        p.drawLine(16, 16, 23, 19)
        p.end()
        self.tray = QSystemTrayIcon(QIcon(pix), app)
        self.tray.setToolTip('世界时钟 · 右键管理')
        self.menu = QMenu()
        self.menu.addAction('添加城市…', self.choose_city)
        self.menu.addAction('显示全部时钟', self.show_all)
        self.menu.addAction('退出', app.quit)
        self.tray.setContextMenu(self.menu)
        self.tray.show()
        app.aboutToQuit.connect(self.save)
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
        name, ok = QInputDialog.getItem(None, '世界时钟', '选择城市，或输入 IANA 时区（如 Africa/Lusaka）：', list(CITIES), 0, True)
        if not ok or not name.strip():
            return
        name = name.strip()
        zone = CITIES.get(name, name)
        try:
            ZoneInfo(zone)
        except (ZoneInfoNotFoundError, ValueError):
            QMessageBox.warning(None, '时区无效', '请选择列表内城市，或输入有效的 IANA 时区名称。')
            return
        if isinstance(target, Clock):
            target.state.update(name=name, zone=zone)
            target.setWindowTitle(name + ' · 世界时钟')
            target.update()
        else:
            self.add({'name': name, 'zone': zone, 'x': 100 + 24 * len(self.clocks), 'y': 160})
        self.save()

    def remove(self, clock):
        if len(self.clocks) == 1:
            self.app.quit()
            return
        self.clocks.remove(clock)
        clock.close()
        clock.deleteLater()
        self.save()

    def save(self):
        for clock in self.clocks:
            clock.state.update(x=clock.x(), y=clock.y())
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix('.tmp')
            temp.write_text(json.dumps([c.state for c in self.clocks], ensure_ascii=False, indent=2), encoding='utf-8')
            temp.replace(self.path)
        except OSError as exc:
            if not self.save_error_shown:
                self.save_error_shown = True
                QMessageBox.warning(None, '无法保存设置', str(exc))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('WorldClockPython')
    app.setQuitOnLastWindowClosed(False)
    if len(sys.argv) == 3 and sys.argv[1] == '--smoke-test':
        # Exercise the frozen executable without reading or changing user settings.
        class TestManager:
            def save(self):
                pass
        clock = Clock(TestManager(), {'name': '卢萨卡（赞比亚）', 'zone': 'Africa/Lusaka'})
        clock.show()
        app.processEvents()
        for month in (1, 7):
            instant = datetime(2026, month, 15, 12, tzinfo=timezone.utc)
            assert time_data('Africa/Lusaka', instant)[0].hour == 14
        assert not clock.grab().isNull()
        report = Path(sys.argv[2])
        clock.grab().save(str(report.with_suffix('.png')))
        report.write_text('PASS: frozen app, Qt window, rendering, tzdata and Zambia UTC+2', encoding='utf-8')
        clock.close()
        return
    manager = Manager(app)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
