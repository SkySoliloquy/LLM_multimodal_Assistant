import subprocess
import sys
import tempfile
import os
import time


class NewWindowPrinter:
    """使用文件通信的简单窗口打印器 - 单例模式"""

    _instances = {}  # 存储不同窗口名称的单例

    def __new__(cls, window_name="定向输出窗口"):
        # 如果该窗口名称的实例不存在，则创建新实例
        if window_name not in cls._instances:
            instance = super(NewWindowPrinter, cls).__new__(cls)
            cls._instances[window_name] = instance
        return cls._instances[window_name]

    def __init__(self, window_name="定向输出窗口"):
        # 防止重复初始化
        if hasattr(self, 'initialized') and self.initialized:
            return

        self.window_name = window_name
        # 创建临时文件用于通信
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.txt', encoding='utf-8'
        )
        self.temp_path = self.temp_file.name
        self.temp_file.close()

        self.process = None
        self._start_new_window()
        self.initialized = True

    def _start_new_window(self):
        """启动新窗口监听文件变化"""
        subproc_code = f"""
import time
import os
import sys

def main():
    file_path = r"{self.temp_path}"
    window_name = "{self.window_name}"

    print(f"===== {{window_name}} =====")

    try:
        last_position = 0
        while True:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.seek(0, 2)
                    file_size = f.tell()

                    if file_size > last_position:
                        f.seek(last_position)
                        new_content = f.read()
                        print(new_content, end='', flush=True)
                        last_position = file_size

                    if file_size > 0:
                        f.seek(0)
                        content = f.read()
                        if "___EXIT___" in content:
                            break

            except FileNotFoundError:
                break
            except Exception as e:
                break

            time.sleep(0.1)

    except KeyboardInterrupt:
        pass
    finally:
        print(f"\\n===== {{window_name}} 关闭 =====")
        try:
            os.remove(file_path)
        except:
            pass
        input("按回车键退出...")

if __name__ == "__main__":
    main()
""".strip()

        self.process = subprocess.Popen(
            [sys.executable, "-c", subproc_code],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        time.sleep(1)

    def print_to_window(self, message):
        """向窗口发送消息"""
        try:
            with open(self.temp_path, 'a', encoding='utf-8') as f:
                f.write(str(message))
                f.flush()
        except Exception as e:
            print(f"发送到窗口失败: {e}")

    def close(self):
        """关闭窗口"""
        try:
            with open(self.temp_path, 'a', encoding='utf-8') as f:
                f.write("___EXIT___\n")
                f.flush()
        except:
            pass

        if self.process:
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.terminate()

        try:
            if os.path.exists(self.temp_path):
                os.remove(self.temp_path)
        except:
            pass

        # 从实例字典中移除
        if self.window_name in NewWindowPrinter._instances:
            del NewWindowPrinter._instances[self.window_name]