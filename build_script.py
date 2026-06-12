import PyInstaller.__main__
import os

# 获取图标的绝对路径
icon_path = os.path.join('src', 'icons', 's3-uploader.icns')

PyInstaller.__main__.run([
    'src/main.py',
    '--name=S3Uploader',
    '--windowed',
    '--onefile',
    '--noconfirm',
    '--clean',
    f'--icon={icon_path}',  
])