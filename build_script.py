import PyInstaller.__main__
import os

# 获取图标
icon_path = os.path.join('src', 'icons', 's3-uploader.icns')

PyInstaller.__main__.run([
    'src/main.py',
    '--name=S3Uploader',
    '--windowed',
    '--onefile',       # 坚持使用单文件
    '--noconfirm',
    '--clean',
    f'--icon={icon_path}',
    # --- 优化点：剔除不需要的 AWS 模块 ---
    # 如果你只用 S3，可以手动排除其他庞大的 AWS 子服务
    '--exclude-module=botocore.vendored.requests',
    # 强制收集 UI 资源，避免启动时动态查找路径导致的卡顿
    '--collect-all=customtkinter',
])