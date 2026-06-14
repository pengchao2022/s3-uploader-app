import sys
import os
import threading
import subprocess
import tempfile
import boto3
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tomllib
from boto3.s3.transfer import TransferConfig
from concurrent.futures import ThreadPoolExecutor, as_completed
import botocore
if not hasattr(botocore, 'vendored'):
    botocore.vendored = type('fake', (), {'requests': None})

# 设置外观模式和主题
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class ProgressPercentage:
    """进度回调类"""
    def __init__(self, filename, total_size, progress_callback, task_index):
        self._filename = filename
        self._total_size = float(total_size)
        self._seen_so_far = 0
        self._callback = progress_callback
        self._task_index = task_index
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = self._seen_so_far / self._total_size
            self._callback(self._task_index, percentage)

class S3UploaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.version = self.get_version()
        self.title(f"AWS S3 上传助手 v{self.version}")
        self.geometry("500x850")  # 增加窗口高度以容纳新输入框
        self.resizable(False, False)
        
        self.selected_items = []
        self.upload_tasks = []
        self.is_uploading = False
        self.is_completing = False  # 标记是否正在收尾阶段
        
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="s3_uploader_")
        
        # 确保程序退出时清理临时文件
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

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

        # 3. 目标路径输入框（新增）
        self.path_entry = ctk.CTkEntry(self, width=350, placeholder_text="Prefix (可选:e.g., folder/subfolder/)")
        self.path_entry.pack(pady=5)
        
        # 提示标签
        self.path_hint = ctk.CTkLabel(self, text="留空则上传到桶根目录", font=("Arial", 10), text_color="gray")
        self.path_hint.pack(pady=(0, 5))

        # 4. 状态标签
        self.status_label = ctk.CTkLabel(self, text="就绪", font=("Arial", 12), text_color="gray")
        self.status_label.pack(pady=10)

        # 5. 整体进度条
        self.progress_bar = ctk.CTkProgressBar(self, width=350)
        self.progress_bar.set(0)

        # 6. 正在上传的文件列表框架
        self.uploading_frame = ctk.CTkFrame(self)
        
        self.uploading_label = ctk.CTkLabel(self.uploading_frame, text="正在上传:", 
                                            font=("Arial", 12, "bold"), anchor="w")
        self.uploading_label.pack(pady=(10,5), padx=10, anchor="w")
        
        # 动态显示正在上传的文件名 - 高度增加到300，可以显示5-6个任务
        self.active_uploads_text = ctk.CTkTextbox(self.uploading_frame, height=300, width=350, 
                                                   font=("Arial", 13), state="disabled")
        self.active_uploads_text.pack(pady=5, padx=10, fill="both", expand=True)

        # 7. 按钮
        self.btn_select = ctk.CTkButton(self, text="选择文件", command=self.select_files, 
                                        fg_color="#FF9800", hover_color="#F57C00", width=200)
        self.btn_select.pack(pady=10)

        self.btn_upload = ctk.CTkButton(self, text="开始上传", command=self.upload_to_s3, 
                                        fg_color="#E65100", hover_color="#BF360C", 
                                        state="disabled", width=200)
        self.btn_upload.pack(pady=10)

        # 8. 底部信息
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

    def on_closing(self):
        """清理临时文件后退出"""
        if self.is_uploading:
            if messagebox.askokcancel("确认", "上传正在进行中，确定要退出吗？"):
                self.is_uploading = False
                try:
                    import shutil
                    if os.path.exists(self.temp_dir):
                        shutil.rmtree(self.temp_dir)
                except:
                    pass
                self.destroy()
        else:
            try:
                import shutil
                if os.path.exists(self.temp_dir):
                    shutil.rmtree(self.temp_dir)
            except:
                pass
            self.destroy()

    def select_files(self):
        filenames = filedialog.askopenfilenames(title="选择文件或文件夹")
        if filenames:
            self.selected_items = list(filenames)
            self.btn_select.configure(text=f"已选 {len(filenames)} 个文件")
            self.btn_upload.configure(state="normal")
            self.progress_bar.set(0)
            self.update_status(f"已选择 {len(filenames)} 个文件")
            # 清空显示
            self.clear_upload_display()

    def clear_upload_display(self):
        """清空上传列表显示"""
        self.active_uploads_text.configure(state="normal")
        self.active_uploads_text.delete("1.0", "end")
        self.active_uploads_text.configure(state="disabled")

    def update_status(self, message):
        """更新状态栏"""
        self.after(0, lambda: self.status_label.configure(text=message))

    def update_active_uploads(self, active_files):
        """更新正在上传的文件列表"""
        self.after(0, lambda: self._update_active_uploads_ui(active_files))
    
    def _update_active_uploads_ui(self, active_files):
        """在UI线程中更新正在上传的文件列表"""
        self.active_uploads_text.configure(state="normal")
        self.active_uploads_text.delete("1.0", "end")
        
        if active_files and len(active_files) > 0:
            for i, (filename, progress) in enumerate(active_files, 1):
                # 创建进度条显示
                progress_percent = int(progress * 100)
                
                # 统一使用黑色字符的进度条
                bar_length = 41
                filled_length = int(bar_length * progress)
                bar = "█" * filled_length + "░" * (bar_length - filled_length)
                
                # 格式化显示：文件名 + 进度条 + 百分比
                display_text = f"{i}. {filename}\n"
                display_text += f"   {bar} {progress_percent}%\n\n"
                self.active_uploads_text.insert("end", display_text)
        else:
            # 根据不同的状态显示不同的文字
            if self.is_completing:
                self.active_uploads_text.insert("end", "上传收尾中...")
            elif self.is_uploading:
                self.active_uploads_text.insert("end", "准备上传...")
            else:
                self.active_uploads_text.insert("end", "")
        
        self.active_uploads_text.configure(state="disabled")

    def update_progress(self, task_index, percentage):
        """更新单个任务的进度和整体进度"""
        if task_index < len(self.upload_tasks):
            self.upload_tasks[task_index]['progress'] = percentage
            
            # 计算整体进度
            total_progress = sum(t['progress'] for t in self.upload_tasks) / len(self.upload_tasks)
            self.after(0, lambda: self.progress_bar.set(total_progress))
            
            # 更新正在上传的文件列表显示
            active_files = []
            completed_count = 0
            for task in self.upload_tasks:
                if task['progress'] >= 1.0:
                    completed_count += 1
                elif task['progress'] > 0:
                    active_files.append((task['name'], task['progress']))
            
            self.update_active_uploads(active_files)
            
            # 更新状态显示
            self.update_status(f"进度: {completed_count}/{len(self.upload_tasks)} 完成")

    def compress_file(self, source_path, output_dir):
        """压缩文件或文件夹"""
        base_name = os.path.basename(source_path.rstrip('/'))
        zip_path = os.path.join(output_dir, f"{base_name}.zip")
        
        # 避免重名
        counter = 1
        original_path = zip_path
        while os.path.exists(zip_path):
            name, ext = os.path.splitext(original_path)
            zip_path = f"{name}_{counter}{ext}"
            counter += 1
        
        # 使用系统 zip 命令压缩
        subprocess.run(['zip', '-rq', zip_path, source_path], check=True)
        return zip_path, f"{base_name}.zip"

    def upload_single_file(self, s3_client, file_path, bucket, key, task_index):
        """上传单个文件（带进度）"""
        file_size = os.path.getsize(file_path)
        progress = ProgressPercentage(key, file_size, self.update_progress, task_index)
        
        config = TransferConfig(
            multipart_threshold=10 * 1024 * 1024,
            max_concurrency=5,
            multipart_chunksize=5 * 1024 * 1024,
            use_threads=True
        )
        
        s3_client.upload_file(
            Filename=file_path,
            Bucket=bucket,
            Key=key,
            Callback=progress,
            Config=config
        )

    def _perform_upload(self, aws_key, aws_secret, bucket_name):
        """执行并发上传 - 始终保持5个并发（但不超过文件总数）"""
        self.is_uploading = True
        self.is_completing = False
        
        try:
            # 准备上传任务
            self.upload_tasks = []
            task_files = []
            
            # 获取目标路径前缀
            target_prefix = self.path_entry.get().strip()
            if target_prefix:
                # 确保以 / 结尾
                if not target_prefix.endswith('/'):
                    target_prefix += '/'
            
            self.update_status("正在准备文件...")
            self.update_active_uploads([])
            
            for path in self.selected_items:
                # 判断是否需要压缩
                if os.path.isdir(path) or (os.path.isfile(path) and path.endswith('.app')):
                    # 需要压缩
                    try:
                        self.update_status(f"正在压缩: {os.path.basename(path)}...")
                        zip_path, zip_name = self.compress_file(path, self.temp_dir)
                        # 添加路径前缀
                        if target_prefix:
                            s3_key = target_prefix + zip_name
                        else:
                            s3_key = zip_name
                        task_files.append((zip_path, s3_key, True, os.path.basename(path)))
                    except Exception as e:
                        self.update_status(f"压缩失败: {os.path.basename(path)}")
                        self.after(0, lambda: messagebox.showerror("错误", f"压缩 {path} 失败: {str(e)}"))
                        continue
                else:
                    # 普通文件，直接上传
                    original_name = os.path.basename(path)
                    # 添加路径前缀
                    if target_prefix:
                        s3_key = target_prefix + original_name
                    else:
                        s3_key = original_name
                    task_files.append((path, s3_key, False, original_name))
            
            if not task_files:
                self.update_status("没有有效的文件")
                self.after(0, self.reset_ui)
                return
            
            # 初始化任务进度
            for i, (_, s3_key, _, original_name) in enumerate(task_files):
                self.upload_tasks.append({
                    'index': i,
                    'progress': 0,
                    'name': original_name,
                    's3_key': s3_key
                })
            
            # 显示进度条和上传列表区域
            self.progress_bar.pack(pady=10)
            self.uploading_frame.pack(pady=10, padx=20, fill="x")
            
            # 并发数：如果文件数小于5，就全部并发；如果大于等于5，就5个并发
            concurrent_count = min(5, len(task_files))
            self.update_status(f"开始上传 {len(task_files)} 个文件（并发数: {concurrent_count}）...")
            
            # 创建 S3 客户端函数
            def get_s3_client():
                return boto3.client(
                    's3',
                    aws_access_key_id=aws_key,
                    aws_secret_access_key=aws_secret
                )
            
            # 使用线程池并发上传
            import concurrent.futures
            
            with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
                # 提交所有任务
                futures = {}
                for idx, (file_path, s3_key, is_temp, original_name) in enumerate(task_files):
                    future = executor.submit(
                        self.upload_single_file,
                        get_s3_client(),
                        file_path,
                        bucket_name,
                        s3_key,
                        idx
                    )
                    futures[future] = (file_path, is_temp)
                
                # 等待所有任务完成
                for future in concurrent.futures.as_completed(futures):
                    file_path, is_temp = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        self.update_status(f"上传失败: {os.path.basename(file_path)}")
                        self.after(0, lambda: messagebox.showerror("错误", f"上传 {os.path.basename(file_path)} 失败: {str(e)}"))
                    
                    # 清理临时文件
                    if is_temp and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except:
                            pass
                    
                    # 更新完成数量显示
                    completed_count = sum(1 for t in self.upload_tasks if t['progress'] >= 1.0)
                    self.update_status(f"进度: {completed_count}/{len(task_files)} 完成")
            
            # 检查是否全部完成
            all_completed = all(t['progress'] >= 1.0 for t in self.upload_tasks)
            
            if all_completed:
                # 进入收尾阶段
                self.is_completing = True
                
                # 进度条消失
                self.progress_bar.pack_forget()
                
                # 显示"上传收尾中..."
                self.update_active_uploads([])
                self.update_status("上传收尾中...")
                    
                # 延迟1秒后显示成功对话框并重置界面
                self.after(1000, lambda: self.show_success_and_reset(len(task_files)))
            else:
                self.update_status("部分文件上传失败")
                self.after(0, lambda: messagebox.showwarning("警告", "部分文件上传失败，请检查网络或重试"))
                self.after(0, self.reset_ui)
                
        except Exception as e:
            error_msg = str(e)
            self.update_status(f"错误: {error_msg[:50]}...")
            self.after(0, lambda: messagebox.showerror("错误", f"上传失败: {error_msg}"))
            self.after(0, self.reset_ui)
        finally:
            self.is_uploading = False
            self.is_completing = False

    def show_success_and_reset(self, file_count):
        """显示成功消息并重置界面"""
        messagebox.showinfo("成功", f"全部 {file_count} 个文件上传成功！")
        self.reset_ui()

    def reset_ui(self):
        """重置界面"""
        self.selected_items = []
        self.upload_tasks = []
        self.btn_select.configure(text="选择文件")
        self.btn_upload.configure(state="normal", text="开始上传")
        self.progress_bar.set(0)
        self.uploading_frame.pack_forget()
        self.update_status("就绪")
        # 清空上传列表显示
        self.clear_upload_display()

    def upload_to_s3(self):
        if self.is_uploading:
            return
            
        aws_key = self.key_entry.get().strip()
        aws_secret = self.secret_entry.get().strip()
        bucket_name = self.bucket_entry.get().strip()

        if not all([aws_key, aws_secret, bucket_name]):
            messagebox.showwarning("警告", "请填写完整的凭证和 Bucket 名称")
            return
        
        if not self.selected_items:
            messagebox.showwarning("警告", "请先选择要上传的文件")
            return

        self.btn_upload.configure(state="disabled", text="上传中...")
        self.update_status("准备上传...")
        
        upload_thread = threading.Thread(target=self._perform_upload, args=(aws_key, aws_secret, bucket_name))
        upload_thread.daemon = True
        upload_thread.start()

if __name__ == "__main__":
    app = S3UploaderApp()
    app.mainloop()