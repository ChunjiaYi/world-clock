# Third-party components

World Clock uses unmodified components distributed under their respective licenses:

- Python 3.13.13 — Python Software Foundation License. https://www.python.org/downloads/release/python-31313/
- PySide6 / Shiboken6 / Qt 6.8.3 — LGPLv3 / GPLv3 / applicable Qt third-party licenses. https://code.qt.io/cgit/pyside/pyside-setup.git/ and https://download.qt.io/official_releases/qt/6.8/6.8.3/
- tzdata 2026.4 — Apache-2.0; IANA timezone data is public domain. https://pypi.org/project/tzdata/2026.4/
- PyInstaller 6.22.3 bootloader — GPL with bootloader exception. https://pyinstaller.org/en/stable/license.html

Upstream license texts are included in the release ZIP's `licenses` directory. The corresponding application source and build script are published alongside the release. Qt libraries are used as shared DLLs; you may rebuild the application with a compatible modified library using the supplied build script. Nothing here restricts rights granted by the component licenses, including reverse engineering for debugging modifications to LGPL-covered components.
