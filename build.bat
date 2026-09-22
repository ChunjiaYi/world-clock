@echo off
setlocal
cd /d "%~dp0"
for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VCINSTALL=%%i"
if not defined VCINSTALL (
 echo Microsoft C++ Build Tools with Windows SDK is required.
 exit /b 1
)
call "%VCINSTALL%\VC\Auxiliary\Build\vcvars64.bat" >nul
if not exist build mkdir build
if not exist dist mkdir dist
rc /nologo /fo build\app.res app.rc
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /O2 /MT /EHsc /utf-8 /DUNICODE /D_UNICODE /DNOMINMAX /DWIN32_LEAN_AND_MEAN /Fo:build\ /Fe:dist\WorldClock.exe main.cpp build\app.res /link /SUBSYSTEM:WINDOWS /INCREMENTAL:NO user32.lib gdi32.lib shell32.lib ole32.lib comctl32.lib comdlg32.lib advapi32.lib winhttp.lib windowscodecs.lib d2d1.lib dwrite.lib dwmapi.lib shlwapi.lib
exit /b %errorlevel%
