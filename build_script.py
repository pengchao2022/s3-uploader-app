import PyInstaller.__main__
import os

PyInstaller.__main__.run([
    'src/main.py',
    '--name=S3Uploader',
    '--windowed',
    '--onedir',    
    '--noconfirm',
    '--clean',
    f'--icon={os.path.join("src", "icons", "s3-uploader.icns")}',
    '--collect-all=customtkinter',
])