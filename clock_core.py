"""Portable settings, timezone and weather logic (no GUI imports)."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION = '1.1.0'
WEEK = ('星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日')
PRESETS = [
    dict(name='北京', region='中国', zone='Asia/Shanghai', lat=39.9042, lon=116.4074),
    dict(name='迪拜', region='阿联酋', zone='Asia/Dubai', lat=25.2048, lon=55.2708),
    dict(name='卢萨卡', region='赞比亚', zone='Africa/Lusaka', lat=-15.3875, lon=28.3228),
    dict(name='科伦坡', region='斯里兰卡', zone='Asia/Colombo', lat=6.9271, lon=79.8612),
    dict(name='伦敦', region='英国', zone='Europe/London', lat=51.5085, lon=-0.1257),
    dict(name='纽约', region='美国', zone='America/New_York', lat=40.7143, lon=-74.006),
    dict(name='东京', region='日本', zone='Asia/Tokyo', lat=35.6895, lon=139.6917),
    dict(name='新加坡', region='新加坡', zone='Asia/Singapore', lat=1.2897, lon=103.8501),
]
SHOW_DEFAULTS = dict(city=True, region=False, date=True, weekday=True, offset=True,
                     weather=True, seconds=True, sun=True, sun_times=False)

def normalize(raw):
    state = dict(raw)
    ZoneInfo(state['zone'])
    state['name'] = str(state.get('name') or state['zone'])[:100]
    for preset in PRESETS:
        if state['zone'] == preset['zone'] and 'lat' not in state:
            for key in ('lat', 'lon', 'region'):
                state.setdefault(key, preset[key])
    for key in ('x', 'y'):
        state[key] = int(state.get(key, 40))
    # v1.0's default non-topmost becomes the new default on migration.
    state.setdefault('top', True)
    state.setdefault('theme', 'dark' if state.get('dark') else 'system')
    if state['theme'] not in ('system', 'light', 'dark'):
        state['theme'] = 'system'
    transparency = state.get('transparency', round((255 - int(state.get('alpha', 210))) * 100 / 255))
    state['transparency'] = max(0, min(100, int(transparency)))
    state.setdefault('color_mode', 'system')
    state.setdefault('color', '#d7d8d8')
    state['show'] = {**SHOW_DEFAULTS, **(state.get('show') if isinstance(state.get('show'), dict) else {})}
    if 'lat' in state and 'lon' in state:
        state['lat'], state['lon'] = float(state['lat']), float(state['lon'])
        if not (-90 <= state['lat'] <= 90 and -180 <= state['lon'] <= 180):
            raise ValueError('Invalid coordinates')
    return state

def time_data(zone, instant=None):
    instant = instant or datetime.now(timezone.utc)
    there = instant.astimezone(ZoneInfo(zone))
    minutes = round((there.utcoffset() - instant.astimezone().utcoffset()).total_seconds() / 60)
    h, m = divmod(abs(minutes), 60)
    delta = '本地同时间' if not minutes else ('+' if minutes > 0 else '−') + f'{h}h' + (f'{m:02d}m' if m else '')
    return there, delta

def sun_period(weather, zone, now=None):
    """Only use the matching local date; no fabricated 06:00/18:00 fallback."""
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo(zone)).date()
    for row in weather.get('days', []):
        if row.get('date') == today.isoformat():
            rise, setting = row.get('rise'), row.get('set')
            if rise and setting:
                return rise <= now.timestamp() < setting, rise, setting
    if abs(now.timestamp() - weather.get('current_time', 0)) <= 1800 and weather.get('is_day') in (0, 1):
        return bool(weather['is_day']), None, None
    return None, None, None

def parse_weather(data, zone, fetched_at):
    current, daily = data['current'], data['daily']
    days = []
    for day, rise, setting in zip(daily['time'], daily['sunrise'], daily['sunset']):
        days.append(dict(date=datetime.fromtimestamp(day, ZoneInfo(zone)).date().isoformat(), rise=rise, set=setting))
    return dict(temp=current['temperature_2m'], code=current['weather_code'], is_day=current['is_day'],
                current_time=current['time'], fetched=fetched_at, days=days)

def weather_label(code):
    if code == 0: return '晴'
    if code in (1, 2): return '少云 / 多云'
    if code == 3: return '阴'
    if code in (45, 48): return '雾'
    if code in (51, 53, 55, 56, 57): return '毛毛雨'
    if code in (61, 63, 65, 66, 67, 80, 81, 82): return '雨'
    if code in (71, 73, 75, 77, 85, 86): return '雪'
    if code in (95, 96, 99): return '雷雨'
    return '天气未知'

def load_settings(path):
    if not path.exists(): return []
    data = json.loads(path.read_text(encoding='utf-8'))
    legacy = isinstance(data, list)
    rows = data if legacy else data.get('cards', [])
    states = []
    for row in rows:
        try:
            if legacy: row = {**row, 'top': True}
            states.append(normalize(row))
        except (KeyError, ValueError, TypeError):
            continue
    return states

def save_settings(path, states):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(dict(version=VERSION, cards=states), ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)

def startup_command():
    if getattr(sys, 'frozen', False):
        return subprocess.list2cmdline([sys.executable, '--startup'])
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    return subprocess.list2cmdline([str(pythonw if pythonw.exists() else sys.executable),
                                  str(Path(__file__).with_name('world_clock.py')), '--startup'])

def startup_enabled():
    if os.name != 'nt': return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
            return bool(winreg.QueryValueEx(key, 'WorldClockPython')[0])
    except OSError:
        return False

def set_startup(enabled):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        if enabled:
            winreg.SetValueEx(key, 'WorldClockPython', 0, winreg.REG_SZ, startup_command())
        else:
            try: winreg.DeleteValue(key, 'WorldClockPython')
            except FileNotFoundError: pass
