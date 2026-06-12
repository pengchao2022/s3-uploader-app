import PyInstaller.__main__
import os

PyInstaller.__main__.run([
    'src/main.py',
    '--name=S3Uploader',
    '--windowed',
    '--onefile',
    '--noconfirm',
    '--clean',
    # 强制包含这些库
    '--hidden-import=requests',
    '--hidden-import=boto3',
    '--hidden-import=botocore',
    # 这一行非常关键：解决 CustomTkinter 资源加载慢的问题
    '--collect-all=customtkinter',
    f'--icon={os.path.join("src", "icons", "s3-uploader.icns")}',
])