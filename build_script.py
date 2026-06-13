import PyInstaller.__main__
import os

# 1. 自动处理图标路径
icon_path = os.path.join('src', 'icons', 's3-uploader.icns')
icon_arg = [f'--icon={icon_path}'] if os.path.exists(icon_path) else []

# 2. 执行打包
PyInstaller.__main__.run([
    'src/main.py',
    '--name=S3Uploader',
    '--windowed',
    '--onedir',    
    '--noconfirm',
    '--clean',
    '--debug=imports',
    '--collect-all=customtkinter',
    '--add-data=pyproject.toml:.', 
    '--add-data=assets:assets', 
] + icon_arg)

print("✅ 打包完成！")