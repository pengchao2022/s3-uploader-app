import sys
import os
import threading
import boto3
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tomllib
import keyring # 安全存储凭证

class S3UploaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.version = "1.0.0"
        self.title(f"AWS S3 上传助手 v{self.version}")
        self.geometry("500x650")
        
        # UI 布局
        self.key_entry = ctk.CTkEntry(self, width=350, placeholder_text="Access Key ID", show="*")
        self.key_entry.pack(pady=5)
        self.secret_entry = ctk.CTkEntry(self, width=350, placeholder_text="Secret Access Key", show="*")
        self.secret_entry.pack(pady=5)
        
        # 记住密码勾选框
        self.remember_var = ctk.BooleanVar()
        self.remember_checkbox = ctk.CTkCheckBox(self, text="记住凭证", variable=self.remember_var)
        self.remember_checkbox.pack(pady=5)
        
        # 读取已保存的凭证
        self.load_credentials()

        self.btn_select = ctk.CTkButton(self, text="选择文件", command=self.select_file)
        self.btn_select.pack(pady=10)
        
        # 进度条
        self.progress = ctk.CTkProgressBar(self, width=350)
        self.progress.set(0)
        self.progress.pack(pady=10)
        
        self.btn_upload = ctk.CTkButton(self, text="上传", command=self.upload_to_s3, state="disabled")
        self.btn_upload.pack(pady=10)

    def load_credentials(self):
        try:
            key = keyring.get_password("S3Uploader", "access_key")
            secret = keyring.get_password("S3Uploader", "secret_key")
            if key and secret:
                self.key_entry.insert(0, key)
                self.secret_entry.insert(0, secret)
                self.remember_var.set(True)
        except Exception as e:
            print(f"Keyring load error: {e}") # 即使读取失败，也不要让程序退出

    def select_file(self):
        self.selected_file = filedialog.askopenfilename()
        if self.selected_file:
            self.btn_upload.configure(state="normal")

    def upload_to_s3(self):
        key, secret = self.key_entry.get(), self.secret_entry.get()
        
        # 处理记住密码
        if self.remember_var.get():
            keyring.set_password("S3Uploader", "access_key", key)
            keyring.set_password("S3Uploader", "secret_key", secret)
        else:
            keyring.delete_password("S3Uploader", "access_key")
            keyring.delete_password("S3Uploader", "secret_key")

        thread = threading.Thread(target=self._perform_upload, args=(key, secret))
        thread.start()

    def _perform_upload(self, key, secret):
        file_size = os.path.getsize(self.selected_file)
        s3 = boto3.client('s3', aws_access_key_id=key, aws_secret_access_key=secret)

        def progress_callback(bytes_transferred):
            percentage = bytes_transferred / file_size
            self.after(0, lambda: self.progress.set(percentage))

        try:
            s3.upload_file(self.selected_file, "YOUR_BUCKET", "file_name", 
                           Callback=progress_callback)
            self.after(0, lambda: messagebox.showinfo("成功", "上传完成"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("错误", str(e)))
        finally:
            self.after(0, lambda: self.progress.set(0))