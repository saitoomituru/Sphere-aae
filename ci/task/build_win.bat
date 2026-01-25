cd sphere-aae
rd /s /q build
mkdir build

echo set(USE_VULKAN ON) >> config.cmake

pip install . -v

if %errorlevel% neq 0 exit %errorlevel%
