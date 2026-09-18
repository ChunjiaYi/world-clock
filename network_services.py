"""Asynchronous HTTPS services: UI never waits for network responses."""
import json
from urllib.parse import urlencode
from PySide6.QtCore import QObject, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

class Network(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = QNetworkAccessManager(self)

    def get(self, base, params, done):
        request = QNetworkRequest(QUrl(base + '?' + urlencode(params)))
        request.setTransferTimeout(15000)
        request.setRawHeader(b'User-Agent', b'WorldClock/1.1.0')
        reply = self.manager.get(request)
        def finished():
            try:
                if reply.error() != QNetworkReply.NetworkError.NoError:
                    done(None, '网络暂不可用，请稍后重试')
                else:
                    data = json.loads(bytes(reply.readAll()).decode('utf-8'))
                    done(data, None)
            except (ValueError, KeyError, TypeError):
                done(None, '服务返回的数据无法解析')
            finally:
                reply.deleteLater()
        reply.finished.connect(finished)
        return reply

    def search(self, query, done):
        return self.get('https://geocoding-api.open-meteo.com/v1/search',
                        dict(name=query, count=20, language='zh', format='json'), done)

    def weather(self, state, done):
        return self.get('https://api.open-meteo.com/v1/forecast',
                        dict(latitude=state['lat'], longitude=state['lon'], timezone=state['zone'],
                             current='temperature_2m,weather_code,is_day', daily='sunrise,sunset',
                             forecast_days=3, timeformat='unixtime'), done)
