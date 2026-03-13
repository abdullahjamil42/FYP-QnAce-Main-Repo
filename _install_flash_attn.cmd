@echo off
echo [1/4] Loading Visual Studio build environment...
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64
if errorlevel 1 exit /b %errorlevel%

echo [2/4] Configuring CUDA 12.4...
set "CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4"
set "DISTUTILS_USE_SDK=1"
set "MSSdk=1"
set "FLASH_ATTENTION_FORCE_BUILD=TRUE"
set "FLASH_ATTN_CUDA_ARCHS=80"
set "MAX_JOBS=1"
set "NVCC_THREADS=1"
set "TMP=C:\22i-2451\QACE_Final\_flash_attn_buildtmp"
set "TEMP=C:\22i-2451\QACE_Final\_flash_attn_buildtmp"
set "PATH=C:\22i-2451\QACE_Final\.venv311\Scripts;%CUDA_HOME%\bin;%PATH%"

echo [3/4] Verifying toolchain...
where cl
if errorlevel 1 exit /b %errorlevel%
where nvcc
if errorlevel 1 exit /b %errorlevel%

echo [4/4] Installing flash-attn...
if not exist "C:\22i-2451\QACE_Final\_flash_attn_buildtmp" mkdir "C:\22i-2451\QACE_Final\_flash_attn_buildtmp"
"C:\22i-2451\QACE_Final\.venv311\Scripts\python.exe" -m pip install --no-build-isolation --no-deps "C:\22i-2451\QACE_Final\_flash_attn_src\flash_attn-2.8.3"
exit /b %errorlevel%