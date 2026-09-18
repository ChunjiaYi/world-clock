"""Offline smoke test of the frozen application; no user settings touched."""
import json
from datetime import datetime, timezone
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider, QSpinBox
from clock_core import PRESETS, normalize, sun_period, save_settings, load_settings, time_data

def run_network(app, report):
    import time
    from PySide6.QtCore import QTimer
    from network_services import Network
    from clock_core import parse_weather
    network, results = Network(app), {}
    def done(key, data, error):
        if error:
            results[key] = {'error': error}
        elif key == 'search':
            results[key] = {'count': len(data.get('results', []))}
        else:
            parsed = parse_weather(data, 'Africa/Lusaka', time.time())
            results[key] = {'temperature': parsed['temp'], 'days': len(parsed['days'])}
        if len(results) == 2: app.quit()
    network.search('Lusaka', lambda d, e: done('search', d, e))
    network.weather(PRESETS[2], lambda d, e: done('weather', d, e))
    QTimer.singleShot(20000, app.quit)
    app.exec()
    report.write_text(json.dumps(results, ensure_ascii=False), encoding='utf-8')
    assert len(results) == 2 and all('error' not in row for row in results.values())

def run_smoke(app, report):
    from world_clock import Clock, CardSettings, Manager
    report.parent.mkdir(parents=True, exist_ok=True)
    class Stub:
        def save(self): return True
        def refresh_weather(self): pass
    card = Clock(Stub(), {**PRESETS[2], 'x': 50, 'y': 50})
    card.show()
    app.processEvents()
    assert card.state['top'] and card.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    for percent, alpha in [(0, 255), (50, 128), (100, 0)]:
        card.state['transparency'] = percent
        app.processEvents()
        assert card.grab().toImage().pixelColor(128, card.height()-3).alpha() == alpha
    card.state['transparency'] = 18
    card.state['color_mode'] = 'custom'
    card.state['color'] = '#123456'
    assert card.background()[0].name() == '#123456'
    card.state['color_mode'] = 'system'
    card.state['theme'] = 'dark'
    assert card.background()[1]
    card.state['theme'] = 'light'
    assert not card.background()[1]
    for show in (True, False):
        card.state['show'] = {k: show for k in card.state['show']}
        card.resize_card()
        assert not card.grab().isNull()
    card.state['show'] = normalize(PRESETS[2])['show']
    card.resize_card()
    dialog = CardSettings(card)
    slider, number = dialog.findChild(QSlider), dialog.findChild(QSpinBox)
    slider.setValue(37)
    assert number.value() == 37 and card.state['transparency'] == 37
    number.setValue(82)
    assert slider.value() == 82
    dialog.reject()
    assert card.state['transparency'] == 18
    card.set_top(False)
    card.state['show']['seconds'] = False
    settings = report.with_suffix('.settings.json')
    save_settings(settings, [card.state])
    restored = load_settings(settings)[0]
    assert restored['show']['seconds'] is False and restored['top'] is False
    settings.write_text(json.dumps([dict(name='卢萨卡', zone='Africa/Lusaka', top=False)]), encoding='utf-8')
    assert load_settings(settings)[0]['top'] is True
    fixed = datetime(2026, 9, 18, 12, tzinfo=timezone.utc)
    weather = dict(days=[dict(date='2026-09-18', rise=fixed.timestamp()-3600, set=fixed.timestamp()+3600)])
    assert sun_period(weather, 'Africa/Lusaka', fixed)[0] is True
    assert sun_period(weather, 'Africa/Lusaka', datetime(2026, 9, 18, 18, tzinfo=timezone.utc))[0] is False
    assert sun_period(weather, 'Africa/Lusaka', datetime(2026, 9, 19, 12, tzinfo=timezone.utc))[0] is None
    assert time_data('Africa/Lusaka', fixed)[0].hour == 14
    card.state['theme'] = 'system'
    card.state['show']['seconds'] = True
    card.grab().save(str(report.with_suffix('.png')))
    card.close()
    manager = Manager(app, path=report.with_suffix('.manager.json'), online=False)
    assert len(manager.clocks) == 3
    assert manager.save()
    manager.tray.hide()
    manager.weather_timer.stop()
    for clock in manager.clocks: clock.close()
    report.write_text('PASS: Qt imports; Windows rendering; topmost default; 0/50/100 transparency; '
        'custom/system colors; display options; slider sync/cancel; v1.0 migration; settings roundtrip; '
        'sunrise/sunset/day rollover; Zambia timezone; tray manager. No user config/autostart changed.', encoding='utf-8')
