import sys
import os

# --- 补丁开始：修复 botocore 报错 ---
import botocore
if not hasattr(botocore, 'vendored'):
    # 模拟一个对象，让 boto3 以为它找到了那个旧版 requests
    botocore.vendored = type('fake', (), {'requests': None})
# --- 补丁结束 ---

import customtkinter as ctk
from tkinter import filedialog, messagebox
import boto3
import requests


# 设置外观模式和主题
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class S3UploaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AWS S3 上传助手")
        # 调整了窗口比例为 500x450
        self.geometry("500x450")
        
        self.selected_file = None

        # 1. 标题
        self.label = ctk.CTkLabel(self, text="S3 存储桶名称", font=("Arial", 16, "bold"))
        self.label.pack(pady=(50, 10))

        # 2. 输入框
        self.bucket_entry = ctk.CTkEntry(self, width=350, placeholder_text="请输入 Bucket 名称")
        self.bucket_entry.pack(pady=5)

        # 3. 选择文件按钮
        self.btn_select = ctk.CTkButton(self, text="选择文件", command=self.select_file, 
                                        fg_color="#FF9800", hover_color="#F57C00", width=200)
        self.btn_select.pack(pady=30)

        # 4. 压缩并上传按钮
        self.btn_upload = ctk.CTkButton(self, text="压缩并上传", command=self.upload_to_s3, 
                                        fg_color="#E65100", hover_color="#BF360C", 
                                        state="disabled", width=200)
        self.btn_upload.pack(pady=10)

        # 5. 开发者信息 (底部版权栏)
        self.footer = ctk.CTkLabel(self, text="designed and coded by Maxwell @2026 all rights reserved", 
                                   font=("Arial", 10), text_color="gray")
        # 使用 pack(side="bottom") 让它固定在最下方
        self.footer.pack(side="bottom", pady=20)

    def select_file(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.selected_file = filename
            self.btn_select.configure(text=os.path.basename(filename))
            self.btn_upload.configure(state="normal")

    def upload_to_s3(self):
        # 此处省略业务逻辑...
        bucket_name = self.bucket_entry.get().strip()
        if not bucket_name:
            messagebox.showwarning("提示", "请输入 Bucket 名称")
            return
        messagebox.showinfo("成功", f"正在启动上传任务到 {bucket_name}")

if __name__ == "__main__":
    app = S3UploaderApp()
    app.mainloop()