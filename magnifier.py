# 版本号：v5.0 可视化参数版
# 最后更新：2024-02-07
import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab, ImageTk, Image
import keyboard
import time
import ctypes
import json
import sys

class SettingsWindow(tk.Toplevel):
    """参数设置窗口"""
    def __init__(self, parent, magnifier):
        super().__init__(parent)
        self.magnifier = magnifier
        self.title("参数设置")
        self.geometry("380x600")
        
        # 初始化控件
        self.create_widgets()
        self.load_current_settings()
        
        # 窗口关闭时保存设置
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        """创建参数控件"""
        notebook = ttk.Notebook(self)
        
        # 基本参数标签页
        basic_frame = ttk.Frame(notebook)
        self.create_basic_controls(basic_frame)
        notebook.add(basic_frame, text="基本设置")
        
        # 高级参数标签页
        adv_frame = ttk.Frame(notebook)
        self.create_adv_controls(adv_frame)
        notebook.add(adv_frame, text="高级设置")
        
        notebook.pack(expand=True, fill=tk.BOTH)

    def create_basic_controls(self, frame):
        """基本参数控件"""
        ttk.Label(frame, text="放大倍数 (2-8)").pack(pady=5)
        self.zoom_scale = ttk.Scale(frame, from_=2, to=8, command=lambda v: self.update_param('ZOOM', v))
        self.zoom_scale.pack(fill=tk.X, padx=10)
        
        ttk.Label(frame, text="捕捉区域大小 (100-800)").pack(pady=5)
        self.capture_spin = ttk.Spinbox(frame, from_=100, to=800)
        self.capture_spin.pack(fill=tk.X, padx=10)
        
        ttk.Label(frame, text="刷新率 (FPS)").pack(pady=5)
        self.fps_combobox = ttk.Combobox(frame, values=["30", "60", "90", "120"])
        self.fps_combobox.pack(fill=tk.X, padx=10)

    def create_adv_controls(self, frame):
        """高级参数控件"""
        ttk.Label(frame, text="水平捕捉偏移").pack(pady=5)
        self.cap_x_scale = ttk.Scale(frame, from_=-1000, to=1000, command=lambda v: self.update_offset('capture_offset_x', v))
        self.cap_x_scale.pack(fill=tk.X, padx=10)
        
        ttk.Label(frame, text="垂直捕捉偏移").pack(pady=5)
        self.cap_y_scale = ttk.Scale(frame, from_=-1000, to=1000, command=lambda v: self.update_offset('capture_offset_y', v))
        self.cap_y_scale.pack(fill=tk.X, padx=10)
        
        ttk.Label(frame, text="窗口水平位置").pack(pady=5)
        self.win_x_scale = ttk.Scale(frame, from_=-2000, to=2000, command=lambda v: self.update_offset('window_offset_x', v))
        self.win_x_scale.pack(fill=tk.X, padx=10)
        
        ttk.Label(frame, text="窗口垂直位置").pack(pady=5)
        self.win_y_scale = ttk.Scale(frame, from_=-2000, to=2000, command=lambda v: self.update_offset('window_offset_y', v))
        self.win_y_scale.pack(fill=tk.X, padx=10)

    def load_current_settings(self):
        """加载当前参数"""
        self.zoom_scale.set(self.magnifier.ZOOM)
        self.capture_spin.delete(0, tk.END)
        self.capture_spin.insert(0, str(self.magnifier.CAPTURE_SIZE))
        self.fps_combobox.set(str(self.magnifier.FPS))
        self.cap_x_scale.set(self.magnifier.capture_offset_x)
        self.cap_y_scale.set(self.magnifier.capture_offset_y)
        self.win_x_scale.set(self.magnifier.window_offset_x)
        self.win_y_scale.set(self.magnifier.window_offset_y)

    def update_param(self, name, value):
        """更新需要重启的参数"""
        setattr(self.magnifier, name, round(float(value)))
        if name == 'ZOOM':
            self.magnifier.actual_capture = int(
                self.magnifier.CAPTURE_SIZE / self.magnifier.ZOOM / self.magnifier.screen_scale
            )

    def update_offset(self, name, value):
        """实时更新偏移参数"""
        setattr(self.magnifier, name, int(float(value)))
        self.magnifier.update_calibration()

    def on_close(self):
        """窗口关闭事件处理"""
        try:
            self.magnifier.CAPTURE_SIZE = int(self.capture_spin.get())
            self.magnifier.FPS = int(self.fps_combobox.get())
            self.magnifier.frame_interval = 1 / self.magnifier.FPS
            self.magnifier.save_settings()
            self.destroy()
            print("参数已保存")
        except ValueError:
            print("输入值无效")

class ScreenMagnifier:
    def __init__(self):
        # 初始化系统参数
        self.init_system_params()
        
        # 加载用户设置
        self.load_settings()
        
        # 计算衍生参数
        self.actual_capture = int(
            self.CAPTURE_SIZE / self.ZOOM / self.screen_scale
        )
        
        # 初始化主窗口
        self.init_main_window()
        
        # 初始化热键和状态
        self.is_active = False
        self.last_frame_time = 0
        keyboard.add_hotkey('o', self.toggle_magnifier)
        keyboard.add_hotkey('esc', self.safe_exit)
        
        # 启动主循环
        self.update()

    def init_system_params(self):
        """获取系统参数"""
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        self.screen_scale = ctypes.windll.shcore.GetScaleFactorForDevice(0)/100
        self.screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        self.screen_h = ctypes.windll.user32.GetSystemMetrics(1)

    def init_main_window(self):
        """初始化主窗口"""
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', 1)
        self.update_calibration()
        self.root.withdraw()
        
        # 创建画布
        self.canvas = tk.Canvas(self.root, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 设置按钮
        self.settings_btn = ttk.Button(self.root, text="⚙", command=self.show_settings)
        self.settings_btn.place(x=10, y=10)

    def load_settings(self):
        """加载用户设置"""
        try:
            with open("magnifier_settings.json") as f:
                settings = json.load(f)
                self.ZOOM = settings.get("ZOOM", 4)
                self.CAPTURE_SIZE = settings.get("CAPTURE_SIZE", 400)
                self.FPS = settings.get("FPS", 60)
                self.capture_offset_x = settings.get("capture_offset_x", 0)
                self.capture_offset_y = settings.get("capture_offset_y", 0)
                self.window_offset_x = settings.get("window_offset_x", 0)
                self.window_offset_y = settings.get("window_offset_y", 0)
        except FileNotFoundError:
            self.set_defaults()

    def set_defaults(self):
        """设置默认参数"""
        self.ZOOM = 4
        self.CAPTURE_SIZE = 400
        self.FPS = 60
        self.capture_offset_x = 0
        self.capture_offset_y = 0
        self.window_offset_x = 0
        self.window_offset_y = 0

    def save_settings(self):
        """保存用户设置"""
        settings = {
            "ZOOM": self.ZOOM,
            "CAPTURE_SIZE": self.CAPTURE_SIZE,
            "FPS": self.FPS,
            "capture_offset_x": self.capture_offset_x,
            "capture_offset_y": self.capture_offset_y,
            "window_offset_x": self.window_offset_x,
            "window_offset_y": self.window_offset_y
        }
        with open("magnifier_settings.json", "w") as f:
            json.dump(settings, f)

    def show_settings(self):
        """显示设置窗口"""
        SettingsWindow(self.root, self)

    def update_calibration(self):
        """更新窗口位置"""
        x = (self.screen_w - self.CAPTURE_SIZE) // 2 + self.window_offset_x
        y = (self.screen_h - self.CAPTURE_SIZE) // 2 + self.window_offset_y
        self.root.geometry(f"{self.CAPTURE_SIZE}x{self.CAPTURE_SIZE}+{x}+{y}")

    def toggle_magnifier(self):
        """切换显示状态"""
        self.is_active = not self.is_active
        if self.is_active:
            self.root.deiconify()
        else:
            self.root.withdraw()
        self.last_frame_time = time.time()

    def safe_exit(self):
        """安全退出程序"""
        self.save_settings()
        self.root.quit()
        sys.exit()

    def capture_area(self):
        """捕捉屏幕区域"""
        try:
            x = self.screen_w//2 - self.actual_capture//2 + int(self.capture_offset_x * self.screen_scale)
            y = self.screen_h//2 - self.actual_capture//2 + int(self.capture_offset_y * self.screen_scale)
            return ImageGrab.grab((
                max(0, x),
                max(0, y),
                min(self.screen_w, x + self.actual_capture),
                min(self.screen_h, y + self.actual_capture)
            ))
        except Exception as e:
            print(f"截屏失败: {str(e)}")
            return Image.new('RGB', (self.CAPTURE_SIZE, self.CAPTURE_SIZE), (0,255,0))

    def update(self):
        """主更新循环"""
        if self.is_active:
            try:
                img = self.capture_area().resize(
                    (self.CAPTURE_SIZE, self.CAPTURE_SIZE), 
                    Image.BICUBIC
                )
                self.tk_img = ImageTk.PhotoImage(img)
                self.canvas.create_image(0, 0, image=self.tk_img, anchor=tk.NW)
            except Exception as e:
                print(f"更新失败: {str(e)}")
        
        delay = max(1, int(1000 / self.FPS))
        self.root.after(delay, self.update)

if __name__ == "__main__":
    app = ScreenMagnifier()
    app.root.mainloop()