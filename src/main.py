import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor
import boto3
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tomllib

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

        # 4. 选择文件按钮
        self.btn_select = ctk.CTkButton(self, text="选择文件或文件夹", command=self.select_files, 
                                        fg_color="#FF9800", hover_color="#F57C00", width=200)
        self.btn_select.pack(pady=20)

        # 5. 上传按钮
        self.btn_upload = ctk.CTkButton(self, text="开始上传", command=self.upload_to_s3, 
                                        fg_color="#E65100", hover_color="#BF360C", 
                                        state="disabled", width=200)
        self.btn_upload.pack(pady=10)

        # 6. 底部信息 (包含你的版权签名)
        footer_text = f"Designed by Maxwell @2026 | v{self.version}"
        self.footer = ctk.CTkLabel(self, text=footer_text, 
                                   font=("Arial", 12), text_color="gray")
        self.footer.pack(side="bottom", pady=20)

    def get_version(self):
        """从打包后的根目录读取 pyproject.toml 中的版本号"""
        try:
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            toml_path = os.path.join(base_path, 'pyproject.toml')
            
            with open(toml_path, "rb") as f:
                data = tomllib.load(f)
                return data["project"].get("version", "1.0.0")
        except Exception:
            return "1.0.0"

    def select_files(self):
        """同时支持文件和文件夹选择"""
        # 注意：这里我们使用 filedialog 组合逻辑
        file_paths = filedialog.askopenfilenames(title="选择文件")
        dir_path = filedialog.askdirectory(title="选择文件夹 (可选)")
        
        all_paths = list(file_paths)
        if dir_path:
            all_paths.append(dir_path)
            
        if all_paths:
            self.selected_files = all_paths
            self.btn_select.configure(text=f"已选 {len(all_paths)} 个项目")
            self.btn_upload.configure(state="normal")
            self.progress_bar.set(0)

    def reset_ui(self):
        """重置界面状态"""
        self.selected_files = []
        self.btn_select.configure(text="选择文件或文件夹")
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
        
        thread = threading.Thread(target=self._run_upload_tasks, args=(aws_key, aws_secret, bucket_name))
        thread.start()

    def update_progress(self, current_finished_count, total_count):
        """根据已完成文件数更新进度条"""
        percentage = current_finished_count / total_count
        self.after(0, lambda: self.progress_bar.set(percentage))

    def _run_upload_tasks(self, aws_key, aws_secret, bucket_name):
        """并发执行上传任务，支持文件夹递归"""
        try:
            # 预处理：将所有文件夹展开为文件列表
            file_queue = []
            for path in self.selected_files:
                if os.path.isdir(path):
                    for root, _, files in os.walk(path):
                        for file in files:
                            file_queue.append(os.path.join(root, file))
                else:
                    file_queue.append(path)
            
            total_files = len(file_queue)
            finished_count = 0
            counter_lock = threading.Lock()
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                for file_path in file_queue:
                    futures.append(executor.submit(
                        self._upload_single_file, aws_key, aws_secret, bucket_name, file_path
                    ))
                
                for future in futures:
                    future.result() 
                    with counter_lock:
                        finished_count += 1
                        self.update_progress(finished_count, total_files)
            
            self.after(0, lambda: messagebox.showinfo("成功", f"全部 {total_files} 个文件上传成功！"))
            self.after(0, self.reset_ui)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("错误", f"上传过程出错: {str(e)}"))
            self.after(0, lambda: self.btn_upload.configure(state="normal", text="开始上传"))
            self.after(0, lambda: self.progress_bar.pack_forget())

    def _upload_single_file(self, aws_key, aws_secret, bucket_name, file_path):
        """上传单个文件，处理目录结构"""
        s3 = boto3.client('s3', aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)
        
        # 保持文件名作为 S3 Key
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        with open(file_path, 'rb') as data:
            s3.put_object(
                Bucket=bucket_name,
                Key=file_name,
                Body=data,
                ContentLength=file_size
            )

if __name__ == "__main__":
    app = S3UploaderApp()
    app.mainloop()