import sys
import os
import threading
import boto3
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tomllib
from boto3.s3.transfer import TransferConfig

# --- 补丁保持不变 ---
import botocore
if not hasattr(botocore, 'vendored'):
    botocore.vendored = type('fake', (), {'requests': None})

class ProgressPercentage:
    """用于计算上传进度的类"""
    def __init__(self, filename, progress_callback):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._callback = progress_callback

    def __call__(self, bytes_amount):
        self._seen_so_far += bytes_amount
        percentage = self._seen_so_far / self._size
        # 通过回调函数更新 GUI 进度条
        self._callback(percentage)

class S3UploaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.version = self.get_version()
        self.title(f"AWS S3 上传助手 v{self.version}")
        self.geometry("500x600") # 稍微拉长窗口以容纳进度条
        self.resizable(False, False)
        self.selected_file = None

        # 1. 标题及输入框 (保持不变)
        self.label = ctk.CTkLabel(self, text="AWS S3 配置", font=("Arial", 16, "bold"))
        self.label.pack(pady=(20, 10))

        self.key_entry = ctk.CTkEntry(self, width=350, placeholder_text="Access Key ID", show="*")
        self.key_entry.pack(pady=5)
        self.secret_entry = ctk.CTkEntry(self, width=350, placeholder_text="Secret Access Key", show="*")
        self.secret_entry.pack(pady=5)
        self.bucket_entry = ctk.CTkEntry(self, width=350, placeholder_text="Bucket 名称")
        self.bucket_entry.pack(pady=5)

        # 2. 进度条 (新增)
        self.progress_bar = ctk.CTkProgressBar(self, width=350)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=20)

        # 3. 按钮
        self.btn_select = ctk.CTkButton(self, text="选择文件", command=self.select_file, fg_color="#FF9800", width=200)
        self.btn_select.pack(pady=10)

        self.btn_upload = ctk.CTkButton(self, text="上传到 S3", command=self.upload_to_s3, state="disabled", width=200)
        self.btn_upload.pack(pady=10)

    # ... get_version 和 select_file 方法保持不变 ...
    def get_version(self): # (此处省略实现，与原代码一致) ...
        return "1.0.0"

    def select_file(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.selected_file = filename
            self.btn_select.configure(text=os.path.basename(filename))
            self.btn_upload.configure(state="normal")
            self.progress_bar.set(0) # 选择新文件重置进度

    def upload_to_s3(self):
        aws_key = self.key_entry.get().strip()
        aws_secret = self.secret_entry.get().strip()
        bucket_name = self.bucket_entry.get().strip()

        if not all([aws_key, aws_secret, bucket_name]):
            messagebox.showwarning("警告", "请填写完整的凭证和 Bucket 名称")
            return

        self.btn_upload.configure(state="disabled", text="上传中...")
        thread = threading.Thread(target=self._perform_upload, args=(aws_key, aws_secret, bucket_name))
        thread.start()

    def update_progress(self, percentage):
        """线程安全地更新进度条"""
        self.after(0, lambda: self.progress_bar.set(percentage))

    def _perform_upload(self, aws_key, aws_secret, bucket_name):
        try:
            s3 = boto3.client('s3', aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)
            file_name = os.path.basename(self.selected_file)
            
            # 使用回调函数上传
            s3.upload_file(
                self.selected_file, 
                bucket_name, 
                file_name,
                Callback=ProgressPercentage(self.selected_file, self.update_progress)
            )
            
            self.after(0, lambda: messagebox.showinfo("成功", "上传成功！"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("错误", f"上传失败: {str(e)}"))
        finally:
            self.after(0, lambda: self.btn_upload.configure(state="normal", text="上传到 S3"))
            self.after(0, lambda: self.progress_bar.set(0))

if __name__ == "__main__":
    app = S3UploaderApp()
    app.mainloop()