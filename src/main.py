import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor
import boto3
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tomllib
from boto3.s3.transfer import TransferConfig

# --- 补丁开始：修复 botocore 报错 ---
import botocore
if not hasattr(botocore, 'vendored'):
    botocore.vendored = type('fake', (), {'requests': None})
# --- 补丁结束 ---

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class ProgressPercentage:
    """用于计算批量上传进度的类"""
    def __init__(self, file_index, total_files, filename, progress_callback):
        self._file_index = file_index
        self._total_files = total_files
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._callback = progress_callback
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            file_progress = self._seen_so_far / self._size
            total_progress = (self._file_index + file_progress) / self._total_files
            self._callback(total_progress)

class S3UploaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.version = self.get_version()
        self.title(f"AWS S3 上传助手 v{self.version}")
        self.geometry("500x550")
        self.resizable(False, False)
        
        self.selected_files = []

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

        # 3. 进度条 (初始不显示)
        self.progress_bar = ctk.CTkProgressBar(self, width=350)
        self.progress_bar.set(0)

        # 4. 按钮
        self.btn_select = ctk.CTkButton(self, text="选择文件", command=self.select_files, 
                                        fg_color="#FF9800", hover_color="#F57C00", width=200)
        self.btn_select.pack(pady=20)

        self.btn_upload = ctk.CTkButton(self, text="开始上传", command=self.upload_to_s3, 
                                        fg_color="#E65100", hover_color="#BF360C", 
                                        state="disabled", width=200)
        self.btn_upload.pack(pady=10)

        # 5. 底部信息
        footer_text = f"Designed by Maxwell @2026 | v{self.version}"
        self.footer = ctk.CTkLabel(self, text=footer_text, font=("Arial", 12), text_color="gray")
        self.footer.pack(side="bottom", pady=20)

    def get_version(self):
        try:
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            toml_path = os.path.join(base_path, 'pyproject.toml')
            with open(toml_path, "rb") as f:
                data = tomllib.load(f)
                return data["project"].get("version", "1.0.0")
        except Exception:
            return "1.0.0"

    def select_files(self):
        filenames = filedialog.askopenfilenames()
        if filenames:
            self.selected_files = filenames
            self.btn_select.configure(text=f"已选 {len(filenames)} 个文件")
            self.btn_upload.configure(state="normal")
            self.progress_bar.set(0)

    def reset_ui(self):
        self.selected_files = []
        self.btn_select.configure(text="选择文件")
        self.btn_upload.configure(state="disabled", text="开始上传")
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()

    def upload_to_s3(self):
        aws_key = self.key_entry.get().strip()
        aws_secret = self.secret_entry.get().strip()
        bucket_name = self.bucket_entry.get().strip()

        if not all([aws_key, aws_secret, bucket_name]):
            messagebox.showwarning("警告", "请填写完整的凭证和 Bucket 名称")
            return

        self.progress_bar.pack(pady=20)
        self.btn_upload.configure(state="disabled", text="正在上传...")
        
        # 使用线程启动上传任务
        thread = threading.Thread(target=self._run_upload_tasks, args=(aws_key, aws_secret, bucket_name))
        thread.start()

    def update_progress(self, percentage):
        self.after(0, lambda: self.progress_bar.set(percentage))

    def _run_upload_tasks(self, aws_key, aws_secret, bucket_name):
        """管理上传任务池"""
        try:
            # 开启并行处理：同时上传最多 3 个文件
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for idx, file_path in enumerate(self.selected_files):
                    futures.append(executor.submit(self._upload_single_file, aws_key, aws_secret, bucket_name, idx, file_path))
                
                # 等待所有任务完成
                for future in futures:
                    future.result() # 如果有异常会在这里抛出
            
            self.after(0, lambda: messagebox.showinfo("成功", "所有文件上传成功！"))
            self.after(0, self.reset_ui)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("错误", f"上传过程出错: {str(e)}"))
            self.after(0, lambda: self.btn_upload.configure(state="normal", text="开始上传"))
            self.after(0, lambda: self.progress_bar.pack_forget())

    def _upload_single_file(self, aws_key, aws_secret, bucket_name, idx, file_path):
        """上传单个文件，供线程池调用"""
        s3 = boto3.client('s3', aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)
        file_name = os.path.basename(file_path)
        # 配置单文件上传，禁用内部多线程以避免 rewind 报错
        config = TransferConfig(use_threads=False)
        s3.upload_file(
            Filename=file_path, 
            Bucket=bucket_name, 
            Key=file_name,
            Callback=ProgressPercentage(idx, len(self.selected_files), file_path, self.update_progress),
            Config=config
        )

if __name__ == "__main__":
    app = S3UploaderApp()
    app.mainloop()