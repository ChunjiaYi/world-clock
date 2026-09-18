import unittest
from unittest.mock import patch
from datetime import datetime, timezone
import clock_core as core

class CoreTests(unittest.TestCase):
    def test_sunset_boundaries_and_stale_day(self):
        noon = datetime(2026, 9, 18, 12, tzinfo=timezone.utc).timestamp()
        weather = dict(days=[dict(date='2026-09-18', rise=noon-3600, set=noon+3600)])
        for offset, expected in [(-3601, False), (-3600, True), (3599, True), (3600, False)]:
            self.assertIs(core.sun_period(weather, 'Africa/Lusaka', datetime.fromtimestamp(noon+offset, timezone.utc))[0], expected)
        self.assertIsNone(core.sun_period(weather, 'Africa/Lusaka', datetime.fromtimestamp(noon+86400, timezone.utc))[0])

    def test_timezones_and_defaults(self):
        for month, london in [(1, 12), (7, 13)]:
            utc = datetime(2026, month, 15, 12, tzinfo=timezone.utc)
            self.assertEqual(core.time_data('Africa/Lusaka', utc)[0].hour, 14)
            self.assertEqual(core.time_data('Europe/London', utc)[0].hour, london)
            self.assertEqual(core.time_data('Asia/Colombo', utc)[0].minute, 30)
        self.assertTrue(core.normalize(core.PRESETS[0])['top'])

    def test_autostart_registry_contract_without_system_mutation(self):
        import winreg
        with patch.object(winreg, 'CreateKey') as create, patch.object(winreg, 'SetValueEx') as write:
            core.set_startup(True)
            create.assert_called_once_with(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run')
            self.assertEqual(write.call_args.args[1], 'WorldClockPython')
            self.assertIn('--startup', write.call_args.args[4])
        with patch.object(winreg, 'CreateKey'), patch.object(winreg, 'DeleteValue') as delete:
            core.set_startup(False)
            self.assertEqual(delete.call_args.args[1], 'WorldClockPython')

    def test_weather_timestamp_parsing(self):
        midnight = datetime(2026, 9, 17, 22, tzinfo=timezone.utc).timestamp()
        data = dict(current=dict(temperature_2m=22, weather_code=0, is_day=1, time=midnight+43200),
                    daily=dict(time=[midnight], sunrise=[midnight+21600], sunset=[midnight+64800]))
        parsed = core.parse_weather(data, 'Africa/Lusaka', midnight)
        self.assertEqual(parsed['days'][0]['date'], '2026-09-18')

if __name__ == '__main__': unittest.main()
