import time
import tkinter as tk
from tkinter import ttk
import threading


class Stopwatch:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.running = False

    def start(self):
        """开始计时"""
        if not self.running:
            self.start_time = time.perf_counter()
            self.running = True
            print("秒表已开始")

    def stop(self):
        """结束计时并返回结果"""
        if self.running:
            self.end_time = time.perf_counter()
            self.running = False
            elapsed_time = self.end_time - self.start_time
            return self.format_time(elapsed_time)
        return None

    def format_time(self, seconds):
        """将秒数转换为总毫秒数"""
        milliseconds = seconds * 1000  # 转换为毫秒
        return f"{milliseconds:.0f}毫秒"  # 格式化为整数毫秒


def show_time_popup(time_str):
    """创建并显示非阻塞弹窗"""

    def create_popup():
        # 创建主窗口
        root = tk.Tk()
        root.title("计时结果")
        root.geometry("350x150")
        root.resizable(False, False)

        # 使窗口居中
        root.eval('tk::PlaceWindow . center')

        # 添加内容
        label = ttk.Label(root, text=f"总响应时间: {time_str}", font=("Arial", 12))
        label.pack(pady=20)

        # 确定按钮
        ok_button = ttk.Button(root, text="确定", command=root.destroy)
        ok_button.pack(pady=10)

        # 运行主循环
        root.mainloop()

    # 在新线程中运行弹窗
    popup_thread = threading.Thread(target=create_popup)
    popup_thread.daemon = True
    popup_thread.start()


# 使用示例
if __name__ == "__main__":
    # 创建秒表实例
    stopwatch = Stopwatch()

    # 模拟开始节点
    print("到达开始节点...")
    stopwatch.start()

    # 模拟一些耗时操作
    time.sleep(2.345)  # 这里可以替换为您的实际代码

    # 模拟结束节点
    print("到达结束节点...")
    result = stopwatch.stop()

    if result:
        # 显示弹窗
        show_time_popup(result)
        print("计时完成，弹窗已显示")

        # 这里可以继续执行其他代码，不会被弹窗阻塞
        print("程序继续执行...")
        time.sleep(1)
        print("其他任务完成")

        # 等待一段时间让弹窗显示
        time.sleep(5)
    else:
        print("计时器未启动")