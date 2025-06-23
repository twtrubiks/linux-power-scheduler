"""
Power Scheduler for Linux
一個用於 Linux 系統的電源排程工具，支援定時關機、重啟、休眠等功能
"""

import os
import shlex
import subprocess
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk, messagebox, filedialog


# --- 核心邏輯類別 ---

class AutostartManager:
    """處理 Linux 桌面環境的自動啟動項目管理"""

    def __init__(self):
        self.autostart_dir = os.path.join(os.path.expanduser("~"), ".config", "autostart")
        self.desktop_file_path = os.path.join(self.autostart_dir, "power-scheduler.desktop")
        self.script_path = os.path.abspath(__file__)

    def is_enabled(self):
        """檢查自動啟動是否已啟用"""
        return os.path.exists(self.desktop_file_path)

    def create(self):
        """建立自動啟動設定檔"""
        if not os.path.exists(self.autostart_dir):
            os.makedirs(self.autostart_dir)

        desktop_content = f"""[Desktop Entry]
Type=Application
Name=Power Scheduler
Exec=/usr/bin/python3 {self.script_path}
Comment=Power scheduling application
Icon=system-shutdown
"""
        try:
            with open(self.desktop_file_path, "w", encoding="utf-8") as f:
                f.write(desktop_content)
            messagebox.showinfo("設定成功", "已設定隨系統啟動。")
        except Exception as e:
            messagebox.showerror("錯誤", f"無法建立自動啟動檔案：\n{e}")

    def delete(self):
        """刪除自動啟動設定檔"""
        if self.is_enabled():
            try:
                os.remove(self.desktop_file_path)
                messagebox.showinfo("設定成功", "已取消隨系統啟動。")
            except Exception as e:
                messagebox.showerror("錯誤", f"無法刪除自動啟動檔案：\n{e}")


class ActionExecutor:
    """處理系統指令執行和音效播放"""

    def __init__(self):
        self.sound_process = None

    # 通用系統指令
    GENERAL_COMMANDS = {
        "關機": ["systemctl", "poweroff"],
        "重新開機": ["systemctl", "reboot"],
        "休眠": ["systemctl", "suspend"],
        "關閉螢幕": ["xset", "dpms", "force", "off"],
    }

    # 桌面環境特定指令
    DESKTOP_COMMANDS = {
        "KDE": {
            "登出": ["qdbus", "org.kde.ksmserver", "/KSMServer", "logout", "0", "0", "0"],
        },
        "GNOME": {
            "登出": ["gnome-session-quit", "--no-prompt"],
        },
        "XFCE": {
            "登出": ["xfce4-session-logout", "--logout"],
        }
    }

    def execute(self, action, desktop_env="GNOME", custom_command=None):
        """執行指定的動作"""
        command = self._get_command(action, desktop_env, custom_command)
        if not command:
            return

        self._run_command(command, action)

    def _get_command(self, action, desktop_env, custom_command):
        """取得要執行的指令"""
        if action in self.DESKTOP_COMMANDS.get(desktop_env, {}):
            return self.DESKTOP_COMMANDS[desktop_env][action]
        elif action in self.GENERAL_COMMANDS:
            return self.GENERAL_COMMANDS[action]
        elif action == "執行程式" and custom_command:
            return [custom_command]
        elif action == "執行指令" and custom_command:
            try:
                return shlex.split(custom_command)
            except ValueError:
                messagebox.showerror("指令錯誤", "無法解析指令，請檢查引號是否匹配。")
                return None
        else:
            messagebox.showerror("錯誤", f"未知的任務: {action}")
            return None

    def _run_command(self, command, action):
        """執行指令"""
        try:
            # 系統級操作需要管理員權限
            if action in ["關機", "重新開機", "休眠"]:
                subprocess.Popen(["pkexec"] + command)
            else:
                subprocess.Popen(command)
        except FileNotFoundError:
            messagebox.showerror("錯誤",
                f"指令 '{command[0]}' 不存在。\n"
                f"請確保相關工具已安裝。\n"
                f"(例如 'pkexec' 或 '{command[0]}')")
        except Exception as e:
            messagebox.showerror("執行失敗", f"執行 '{action}' 時發生錯誤:\n{e}")

    def play_sound(self, sound_file):
        """播放音效檔案"""
        if self.sound_process and self.sound_process.poll() is None:
            return  # 已在播放中，避免重複播放

        if not sound_file or not os.path.exists(sound_file):
            messagebox.showwarning("鬧鐘錯誤", "未指定有效的音效檔。")
            return

        try:
            # 使用 ffplay 播放音效
            self.sound_process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", sound_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            messagebox.showerror("錯誤",
                "找不到 'ffplay' 指令，無法播放聲音。\n"
                "請安裝 'ffmpeg' 套件。")
        except Exception as e:
            messagebox.showerror("播放失敗", f"播放音效時發生錯誤:\n{e}")

    def stop_sound(self):
        """停止音效播放"""
        if self.sound_process and self.sound_process.poll() is None:
            self.sound_process.terminate()
            self.sound_process = None


class Scheduler:
    """處理任務排程邏輯"""

    def __init__(self, app_instance):
        self.app = app_instance
        self.job = None
        self.running = False
        self.paused = False
        self.target_time = None
        self.time_left = None
        self.reminder_sent = False
        self.settings = None

    def start(self, settings):
        """開始排程任務"""
        self.settings = settings
        self.running = True
        self.paused = False
        self.reminder_sent = False
        self.app.update_ui_for_running_state(True)

        self._calculate_target_time()
        self.tick()

    def _calculate_target_time(self):
        """計算目標執行時間"""
        mode = self.settings['mode']
        time_config = self.settings['time']

        if mode == "倒數":
            self.time_left = timedelta(
                hours=time_config['h'],
                minutes=time_config['m'],
                seconds=time_config['s']
            )
            self.target_time = datetime.now() + self.time_left

        elif mode == "指定時間":
            self.target_time = datetime(
                year=time_config['year'],
                month=time_config['month'],
                day=time_config['day'],
                hour=time_config['h'],
                minute=time_config['m'],
                second=time_config['s']
            )

        elif mode == "每隔":
            interval = timedelta(
                hours=time_config['h'],
                minutes=time_config['m'],
                seconds=time_config['s']
            )
            self.target_time = datetime.now() + interval

    def stop(self):
        """停止排程任務"""
        if self.job:
            self.app.root.after_cancel(self.job)
            self.job = None
        self.running = False
        self.paused = False
        self.app.update_ui_for_running_state(False)
        self.app.update_status_display()

    def pause(self):
        """暫停/繼續排程任務"""
        if not self.running:
            return

        self.paused = not self.paused
        self.app.pause_button.config(text="繼續" if self.paused else "暫停")

        if not self.paused:
            # 倒數模式繼續時需重新計算目標時間
            if self.settings['mode'] == "倒數":
                self.target_time = datetime.now() + self.time_left
            self.tick()

    def tick(self):
        """排程主循環"""
        if not self.running or self.paused:
            return

        now = datetime.now()
        self._update_time_left(now)
        self.app.update_status_display(self.time_left)

        self._check_reminder()

        if self._should_execute():
            self.execute_action()
            if self.settings['mode'] != "每隔":
                self.stop()
                return

        self.job = self.app.root.after(1000, self.tick)

    def _update_time_left(self, now):
        """更新剩餘時間"""
        mode = self.settings['mode']

        if mode in ["倒數", "指定時間"]:
            self.time_left = self.target_time - now
            if self.time_left.total_seconds() < 0:
                self.time_left = timedelta(0)

        elif mode == "每天":
            time_config = self.settings['time']
            target_today = now.replace(
                hour=time_config['h'],
                minute=time_config['m'],
                second=time_config['s'],
                microsecond=0
            )
            if target_today < now:
                target_today += timedelta(days=1)
            self.time_left = target_today - now

        elif mode == "每隔":
            if now >= self.target_time:
                self.execute_action()
                # 計算下一個執行時間
                interval = timedelta(
                    hours=self.settings['time']['h'],
                    minutes=self.settings['time']['m'],
                    seconds=self.settings['time']['s']
                )
                self.target_time = datetime.now() + interval

            self.time_left = self.target_time - now
            if self.time_left.total_seconds() < 0:
                self.time_left = timedelta(0)

    def _check_reminder(self):
        """檢查是否需要發送提醒"""
        if (self.settings['remind'] and
            not self.reminder_sent and
            self.time_left.total_seconds() <= 60):
            self.reminder_sent = True
            task = self.settings['task']
            messagebox.showinfo("任務提醒", f"任務 '{task}' 將在 1 分鐘後執行。")

    def _should_execute(self):
        """檢查是否應該執行任務"""
        return (self.settings['mode'] != "每隔" and
                self.time_left.total_seconds() <= 0)

    def execute_action(self):
        """執行排程任務"""
        action = self.settings['task']
        desktop_env = self.settings['desktop_env']
        executor = self.app.action_executor

        if action == "鬧鐘":
            self.app.show_alarm_window()
            executor.play_sound(self.settings.get('sound_file'))
        elif action == "顯示訊息":
            message = self.settings.get('message_text', '時間到！')
            messagebox.showinfo("排程訊息", message)
        elif action == "執行程式":
            executor.execute(action, custom_command=self.settings.get('exe_path'))
        elif action == "執行指令":
            executor.execute(action, custom_command=self.settings.get('custom_command'))
        else:
            executor.execute(action, desktop_env=desktop_env)


# --- 使用者介面類別 ---

class AutoSchedulerApp:
    """主應用程式類別"""

    def __init__(self, root):
        self.root = root
        self.root.title("Power Scheduler for Linux")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 初始化核心元件
        self.scheduler = Scheduler(self)
        self.action_executor = ActionExecutor()
        self.autostart_manager = AutostartManager()

        # 初始化 UI 變數
        self._init_variables()

        # 建立介面
        self.create_widgets()
        self.update_time_inputs_visibility()
        self.update_status_display()

    def _init_variables(self):
        """初始化 UI 變數"""
        # 基本設定變數
        self.selected_task = tk.StringVar(value="關機")
        self.schedule_mode = tk.StringVar(value="指定時間")
        self.remind_before_1_min = tk.BooleanVar()
        self.start_with_os = tk.BooleanVar(value=self.autostart_manager.is_enabled())
        self.desktop_env = tk.StringVar()

        # 進階設定變數
        self.alarm_sound_file = tk.StringVar()
        self.message_text = tk.StringVar(value="時間到了！")
        self.exe_path = tk.StringVar()
        self.custom_command = tk.StringVar()

        self.detect_desktop_env()

    def create_widgets(self):
        """建立使用者介面元件"""
        self._create_status_frame()
        self._create_task_selection_frame()
        self._create_time_setting_frame()
        self._create_environment_frame()
        self._create_control_buttons()

    def _create_status_frame(self):
        """建立狀態顯示區域"""
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(top_frame, text="狀態:").pack(side=tk.LEFT)
        self.status_label = ttk.Label(
            top_frame,
            text="尚未執行",
            font=("Arial", 12, "bold"),
            foreground="grey"
        )
        self.status_label.pack(side=tk.LEFT, padx=5)

    def _create_task_selection_frame(self):
        """建立任務選擇區域"""
        left_frame = ttk.LabelFrame(self.root, text="1. 選擇任務", padding="10")
        left_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ns")

        # 基本任務選項
        basic_tasks = ["關機", "重新開機", "休眠", "登出", "關閉螢幕"]
        for i, task in enumerate(basic_tasks):
            ttk.Radiobutton(
                left_frame,
                text=task,
                variable=self.selected_task,
                value=task
            ).grid(row=i, column=0, columnspan=2, sticky="w", pady=2)

        # 需要設定的任務
        advanced_tasks = [
            ("鬧鐘", self.settings_for_alarm),
            ("顯示訊息", self.settings_for_message),
            ("執行程式", self.settings_for_exe),
            ("執行指令", self.settings_for_command)
        ]

        for i, (task_name, settings_func) in enumerate(advanced_tasks):
            row = len(basic_tasks) + i
            ttk.Radiobutton(
                left_frame,
                text=task_name,
                variable=self.selected_task,
                value=task_name
            ).grid(row=row, column=0, sticky="w", pady=2)
            ttk.Button(
                left_frame,
                text="⚙️",
                width=3,
                command=settings_func
            ).grid(row=row, column=1, sticky="w")

        # 分隔線和選項
        separator_row = len(basic_tasks) + len(advanced_tasks)
        ttk.Separator(left_frame, orient='horizontal').grid(
            row=separator_row, column=0, columnspan=2, sticky='ew', pady=10
        )

        ttk.Checkbutton(
            left_frame,
            text="任務前1分鐘提醒",
            variable=self.remind_before_1_min
        ).grid(row=separator_row+1, column=0, columnspan=2, sticky="w", pady=5)

        ttk.Checkbutton(
            left_frame,
            text="隨系統啟動",
            variable=self.start_with_os,
            command=self.toggle_autostart
        ).grid(row=separator_row+2, column=0, columnspan=2, sticky="w", pady=2)

    def _create_time_setting_frame(self):
        """建立時間設定區域"""
        right_frame = ttk.LabelFrame(self.root, text="2. 設定時間", padding="10")
        right_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        # 時間模式選擇
        schedule_modes = ["指定時間", "倒數", "每天", "每隔"]
        for mode_text in schedule_modes:
            ttk.Radiobutton(
                right_frame,
                text=mode_text,
                variable=self.schedule_mode,
                value=mode_text,
                command=self.update_time_inputs_visibility
            ).pack(anchor="w")

        # 建立各模式的輸入框
        self.time_frames = {}
        self._create_time_input_frames(right_frame)

    def _create_time_input_frames(self, parent):
        """建立各種時間輸入框架"""
        self.time_frames["指定時間"] = self.create_time_input_frame(parent, show_ymd=True)
        self.time_frames["倒數"] = self.create_time_input_frame(parent)
        self.time_frames["每天"] = self.create_time_input_frame(parent)
        self.time_frames["每隔"] = self.create_time_input_frame(parent)

    def _create_environment_frame(self):
        """建立環境設定區域"""
        settings_frame = ttk.LabelFrame(self.root, text="3. 環境設定", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        ttk.Label(settings_frame, text="桌面環境:").pack(side=tk.LEFT, padx=5)
        desktop_options = ["KDE", "GNOME", "XFCE"]
        self.desktop_combobox = ttk.Combobox(
            settings_frame,
            textvariable=self.desktop_env,
            values=desktop_options,
            width=15
        )
        self.desktop_combobox.pack(side=tk.LEFT, padx=5)
        ttk.Label(settings_frame, text="(用於'登出'功能)").pack(side=tk.LEFT, padx=5)

    def _create_control_buttons(self):
        """建立控制按鈕區域"""
        bottom_frame = ttk.Frame(self.root, padding="10")
        bottom_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)

        self.execute_button = ttk.Button(
            bottom_frame,
            text="執行",
            command=self.execute_task
        )
        self.execute_button.pack(side=tk.LEFT, padx=5)

        self.pause_button = ttk.Button(
            bottom_frame,
            text="暫停",
            command=self.scheduler.pause,
            state="disabled"
        )
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.reset_button = ttk.Button(
            bottom_frame,
            text="重設",
            command=self.reset_settings
        )
        self.reset_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            bottom_frame,
            text="離開",
            command=self.root.quit
        ).pack(side=tk.RIGHT, padx=5)

    def create_time_input_frame(self, parent, show_ymd=False):
        """建立時間輸入框架"""
        frame = ttk.Frame(parent, padding="5 0 0 20")
        now = datetime.now()

        # 日期輸入 (僅指定時間模式)
        if show_ymd:
            frame.dt_vars = {
                'year': tk.IntVar(value=now.year),
                'month': tk.IntVar(value=now.month),
                'day': tk.IntVar(value=now.day)
            }

            year_values = list(range(now.year, now.year + 5))
            ttk.Combobox(
                frame,
                textvariable=frame.dt_vars['year'],
                values=year_values,
                width=5
            ).pack(side=tk.LEFT)
            ttk.Label(frame, text="年").pack(side=tk.LEFT)

            month_values = list(range(1, 13))
            ttk.Combobox(
                frame,
                textvariable=frame.dt_vars['month'],
                values=month_values,
                width=3
            ).pack(side=tk.LEFT)
            ttk.Label(frame, text="月").pack(side=tk.LEFT)

            day_values = list(range(1, 32))
            ttk.Combobox(
                frame,
                textvariable=frame.dt_vars['day'],
                values=day_values,
                width=3
            ).pack(side=tk.LEFT)
            ttk.Label(frame, text="日").pack(side=tk.LEFT)

        # 時間輸入
        frame.time_vars = {
            'h': tk.IntVar(value=now.hour if show_ymd else 0),
            'm': tk.IntVar(value=now.minute if show_ymd else 5),
            's': tk.IntVar(value=now.second if show_ymd else 0)
        }

        hour_values = list(range(24))
        ttk.Combobox(
            frame,
            textvariable=frame.time_vars['h'],
            values=hour_values,
            width=3
        ).pack(side=tk.LEFT)
        ttk.Label(frame, text="時").pack(side=tk.LEFT)

        minute_values = list(range(60))
        ttk.Combobox(
            frame,
            textvariable=frame.time_vars['m'],
            values=minute_values,
            width=3
        ).pack(side=tk.LEFT)
        ttk.Label(frame, text="分").pack(side=tk.LEFT)

        second_values = list(range(60))
        ttk.Combobox(
            frame,
            textvariable=frame.time_vars['s'],
            values=second_values,
            width=3
        ).pack(side=tk.LEFT)
        ttk.Label(frame, text="秒").pack(side=tk.LEFT)

        return frame

    def update_time_inputs_visibility(self):
        """更新時間輸入框的顯示狀態"""
        selected_mode = self.schedule_mode.get()
        for mode, frame in self.time_frames.items():
            if mode == selected_mode:
                frame.pack(anchor="w", pady=5)
            else:
                frame.pack_forget()

    def update_status_display(self, time_left=None):
        """更新狀態顯示"""
        if not self.scheduler.running:
            self.status_label.config(text="尚未執行", foreground="grey")
            return

        if self.scheduler.paused:
            self.status_label.config(text="已暫停", foreground="orange")
            return

        task = self.scheduler.settings['task']
        if time_left:
            time_str = self._format_time_left(time_left)
            self.status_label.config(
                text=f"將在 {time_str} 後 {task}",
                foreground="blue"
            )
        else:
            self.status_label.config(text=f"執行中: {task}", foreground="green")

    def _format_time_left(self, time_left):
        """格式化剩餘時間顯示"""
        secs = int(time_left.total_seconds())
        h, remainder = divmod(secs, 3600)
        m, s = divmod(remainder, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def update_ui_for_running_state(self, is_running):
        """更新 UI 元件的啟用/停用狀態"""
        state = "disabled" if is_running else "normal"

        # 更新按鈕狀態
        self.execute_button.config(state=state)
        self.reset_button.config(state="normal")  # 重設按鈕永遠啟用
        self.pause_button.config(state="normal" if is_running else "disabled")

        # 鎖定/解鎖設定選項
        self._toggle_settings_widgets(state)

    def _toggle_settings_widgets(self, state):
        """切換設定元件的啟用狀態"""
        for child in self.root.winfo_children():
            if isinstance(child, ttk.LabelFrame):
                for widget in child.winfo_children():
                    if widget not in self.time_frames.values():
                        try:
                            widget.config(state=state)
                        except tk.TclError:
                            pass  # 某些元件如 Separator 沒有 state 屬性

    def detect_desktop_env(self):
        """自動偵測桌面環境"""
        desktop_env = os.environ.get('XDG_CURRENT_DESKTOP', '').upper()

        if "KDE" in desktop_env or "PLASMA" in desktop_env:
            self.desktop_env.set("KDE")
        elif "GNOME" in desktop_env:
            self.desktop_env.set("GNOME")
        elif "XFCE" in desktop_env:
            self.desktop_env.set("XFCE")
        else:
            self.desktop_env.set("GNOME")  # 預設值

    def get_current_settings(self):
        """取得目前的設定值"""
        mode = self.schedule_mode.get()
        frame = self.time_frames[mode]

        settings = {
            'task': self.selected_task.get(),
            'mode': mode,
            'time': dict(frame.time_vars),
            'desktop_env': self.desktop_env.get(),
            'remind': self.remind_before_1_min.get(),
            'startup': self.start_with_os.get(),
            'sound_file': self.alarm_sound_file.get(),
            'message_text': self.message_text.get(),
            'exe_path': self.exe_path.get(),
            'custom_command': self.custom_command.get()
        }

        # 加入日期設定 (指定時間模式)
        if hasattr(frame, 'dt_vars'):
            settings['time'].update(frame.dt_vars)

        # 轉換 Tkinter 變數為 Python 原生類型
        for key, var in settings['time'].items():
            settings['time'][key] = var.get()

        return settings

    def execute_task(self):
        """執行排程任務"""
        settings = self.get_current_settings()

        # 驗證設定
        if not self._validate_settings(settings):
            return

        self.scheduler.start(settings)

    def _validate_settings(self, settings):
        """驗證設定是否有效"""
        if settings['mode'] == "倒數":
            time_config = settings['time']
            if time_config['h'] == 0 and time_config['m'] == 0 and time_config['s'] == 0:
                messagebox.showwarning("無效設定", "倒數時間不能為 0。")
                return False
        return True

    def reset_settings(self):
        """重設所有設定"""
        self.scheduler.stop()

        # 重設變數
        self.selected_task.set("關機")
        self.schedule_mode.set("指定時間")
        self.remind_before_1_min.set(False)
        self.start_with_os.set(False)

        # 更新 UI
        self.update_time_inputs_visibility()
        self.update_status_display()

    def settings_for_alarm(self):
        """設定鬧鐘音效檔"""
        file_path = filedialog.askopenfilename(
            title="選擇鬧鐘音效檔",
            filetypes=[("Sound Files", "*.wav *.mp3"), ("All files", "*.*")]
        )
        if file_path:
            self.alarm_sound_file.set(file_path)
            messagebox.showinfo("設定成功", f"已選擇音效檔:\n{file_path}")

    def settings_for_message(self):
        """設定顯示訊息內容"""
        self._create_text_input_dialog(
            title="設定訊息",
            label_text="請輸入要顯示的訊息:",
            text_var=self.message_text,
            width=40
        )

    def settings_for_exe(self):
        """設定要執行的程式"""
        file_path = filedialog.askopenfilename(title="選擇要執行的程式")
        if file_path:
            self.exe_path.set(file_path)
            messagebox.showinfo("設定成功", f"已選擇程式:\n{file_path}")

    def settings_for_command(self):
        """設定要執行的指令"""
        self._create_text_input_dialog(
            title="設定要執行的指令",
            label_text="請輸入要執行的 Shell 指令:",
            text_var=self.custom_command,
            width=50,
            warning_text="警告：執行任意指令可能存在安全風險。"
        )

    def _create_text_input_dialog(self, title, label_text, text_var, width, warning_text=None):
        """建立文字輸入對話框"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.grab_set()  # 設為模態對話框

        ttk.Label(dialog, text=label_text).pack(padx=10, pady=5)
        entry = ttk.Entry(dialog, textvariable=text_var, width=width)
        entry.pack(padx=10, pady=5)
        entry.focus()  # 設定焦點

        if warning_text:
            ttk.Label(dialog, text=warning_text, foreground="red").pack(padx=10, pady=5)

        ttk.Button(dialog, text="確定", command=dialog.destroy).pack(pady=10)

        # 按 Enter 鍵確定
        entry.bind('<Return>', lambda e: dialog.destroy())

    def toggle_autostart(self):
        """切換自動啟動設定"""
        if self.start_with_os.get():
            self.autostart_manager.create()
        else:
            self.autostart_manager.delete()

    def show_alarm_window(self):
        """顯示鬧鐘視窗"""
        alarm_win = tk.Toplevel(self.root)
        alarm_win.title("鬧鐘！")
        alarm_win.geometry("300x100")
        alarm_win.grab_set()  # 設為模態視窗
        alarm_win.attributes('-topmost', True)  # 置頂顯示

        ttk.Label(
            alarm_win,
            text="時間到！",
            font=("Arial", 16)
        ).pack(expand=True, pady=10)

        def stop_and_close():
            self.action_executor.stop_sound()
            alarm_win.destroy()

        ttk.Button(
            alarm_win,
            text="停止鬧鐘",
            command=stop_and_close
        ).pack(pady=10)

        alarm_win.protocol("WM_DELETE_WINDOW", stop_and_close)

    def on_closing(self):
        """程式關閉時的清理工作"""
        self.action_executor.stop_sound()
        self.scheduler.stop()
        self.root.destroy()


def main():
    """主程式入口"""
    root = tk.Tk()
    app = AutoSchedulerApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
