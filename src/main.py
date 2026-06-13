import sys
import os
import threading
import boto3
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tomllib  # 用于读取 pyproject.toml

# --- 补丁开始：修复 botocore 报错 ---
import botocore
if not hasattr(botocore, 'vendored'):
    botocore.vendored = type('fake', (), {'requests': None})
# --- 补丁结束 ---

# 设置外观模式和主题
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class S3UploaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        # 获取版本号
        self.version = self.get_version()
        
        self.title(f"AWS S3 上传助手 v{self.version}")
        self.geometry("500x550")
        self.resizable(False, False)
        
        self.selected_file = None

        # 1. 标题
        self.label = ctk.CTkLabel(self, text="AWS S3 配置", font=("Arial", 16, "bold"))
        self.label.pack(pady=(20, 10))

        # 2. 凭证输入框
        self.key_entry = ctk.CTkEntry(self, width=350, placeholder_text="Access Key ID", show="*")
        self.key_entry.pack(pady=5)

        self.secret_entry = ctk.CTkEntry(self, width=350, placeholder_text="Secret Access Key", show="*")
        self.secret_entry.pack(pady=5)

        self.bucket_entry = ctk.CTkEntry(self, width=350, placeholder_text="Bucket 名称")
        self.bucket_entry.pack(pady=5)

        # 3. 选择文件按钮
        self.btn_select = ctk.CTkButton(self, text="选择文件", command=self.select_file, 
                                        fg_color="#FF9800", hover_color="#F57C00", width=200)
        self.btn_select.pack(pady=20)

        # 4. 上传按钮
        self.btn_upload = ctk.CTkButton(self, text="上传到 S3", command=self.upload_to_s3, 
                                        fg_color="#E65100", hover_color="#BF360C", 
                                        state="disabled", width=200)
        self.btn_upload.pack(pady=10)

        # 5. 底部信息 (版本号已集成)
        footer_text = f"Designed by Maxwell @2026 | v{self.version}"
        self.footer = ctk.CTkLabel(self, text=footer_text, 
                                   font=("Arial", 12), text_color="gray")
        self.footer.pack(side="bottom", pady=20)

    def get_version(self):
        """从打包后的根目录读取 pyproject.toml 中的版本号"""
        try:
            # 兼容开发环境和 PyInstaller 打包环境
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            # 向上寻找配置文件 (如果文件在打包根目录)
            toml_path = os.path.join(base_path, 'pyproject.toml')
            
            with open(toml_path, "rb") as f:
                data = tomllib.load(f)
                return data["project"].get("version", "1.0.0")
        except Exception:
            return "1.0.0"

    def select_file(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.selected_file = filename
            self.btn_select.configure(text=os.path.basename(filename))
            self.btn_upload.configure(state="normal")

    def upload_to_s3(self):
        aws_key = self.key_entry.get().strip()
        aws_secret = self.secret_entry.get().strip()
        bucket_name = self.bucket_entry.get().strip()

        if not all([aws_key, aws_secret, bucket_name]):
            messagebox.showwarning("警告", "请填写完整的凭证和 Bucket 名称")
            return

        self.btn_upload.configure(state="disabled", text="正在上传...")
        thread = threading.Thread(target=self._perform_upload, args=(aws_key, aws_secret, bucket_name))
        thread.start()

    def _perform_upload(self, aws_key, aws_secret, bucket_name):
        try:
            s3 = boto3.client('s3', aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)
            file_name = os.path.basename(self.selected_file)
            s3.upload_file(self.selected_file, bucket_name, file_name)
            self.after(0, lambda: messagebox.showinfo("成功", f"文件 {file_name} 上传成功！"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("错误", f"上传失败: {str(e)}"))
        finally:
            self.after(0, lambda: self.btn_upload.configure(state="normal", text="上传到 S3"))

if __name__ == "__main__":
    app = S3UploaderApp()
    app.mainloop()