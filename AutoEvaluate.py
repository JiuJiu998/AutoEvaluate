import re
import time
import tkinter as tk
from tkinter import ttk, scrolledtext

import winsound
from PIL import Image, ImageTk
import os
import queue
import threading

from datetime import datetime

from AutoSubmitter import AutoSubmitter
from Student import Student


class TeachingEvaluationUI:
    def __init__(self, root):
        self.course_table = None
        self.root = root
        self.root.title("东莞城市学院自动评教系统")

        # 用户状态变量
        self.is_logged_in = False
        self.student_name = ""
        self.student_class = ""

        # 设置窗口大小和位置
        self.setup_window()

        # 初始化日志系统
        self.log_queue = queue.Queue()
        self.setup_logging()

        # 主界面布局
        self.create_main_frame()

        # 初始化组件
        self.create_left_panel()
        self.create_right_panel()

        #  用户数据
        self.stu = None

        # 控制器数据
        self.autoSubmitter = None

        self.log("系统初始化完成")
        self.update_ui_state()  # 初始状态更新

    def setup_window(self):
        """设置窗口属性和位置"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 窗口尺寸 (适当小于屏幕尺寸)
        window_width = min(1200, screen_width - 100)
        window_height = min(800, screen_height - 100)

        # 居中位置
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(800, 600)  # 最小尺寸限制

    def setup_logging(self):
        """初始化日志系统"""
        self.log_dir = "logs"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # 启动日志写入线程
        self.log_thread = threading.Thread(target=self.write_logs_to_file, daemon=True)
        self.log_thread.start()

        # 设置日志处理定时器
        self.root.after(100, self.process_log_queue)

    def create_main_frame(self):
        """创建主框架"""
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左右分割 (PanedWindow允许拖动调整)
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # 左侧面板 (主要内容)
        self.left_panel = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_panel, weight=3)  # 75%比例

        # 右侧面板 (登录和帮助)
        self.right_panel = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_panel, weight=1)  # 25%比例

    def create_left_panel(self):
        """创建左侧面板"""
        # 上部 - 课程列表
        course_frame = ttk.LabelFrame(self.left_panel, text="待评教课程列表", padding=10)
        course_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # 控制按钮区域
        control_frame = ttk.Frame(course_frame)
        control_frame.pack(fill=tk.X, pady=(0, 5))

        self.select_all_btn = ttk.Button(control_frame, text="全选", command=self.select_all_courses)
        self.select_all_btn.pack(side=tk.LEFT, padx=2)

        self.deselect_all_btn = ttk.Button(control_frame, text="全不选", command=self.deselect_all_courses)
        self.deselect_all_btn.pack(side=tk.LEFT, padx=2)

        # 课程表格
        self.create_course_table(course_frame)

        # 下部 - 日志框
        log_frame = ttk.LabelFrame(self.left_panel, text="系统日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def create_course_table(self, parent):
        """创建课程表格"""
        # 创建Treeview
        columns = ("序号", "课程编号", "学年学期", "课程名称", "授课教师", "是否已评教", "操作链接")
        display_columns = ("序号", "课程编号", "学年学期", "课程名称", "授课教师", "是否已评教")  # 不显示隐藏列
        # 创建 Treeview
        self.course_table = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            displaycolumns=display_columns,  # 只显示指定的列
            selectmode="extended",
            height=8
        )

        # 配置列
        col_widths = [50, 100, 80, 250, 100, 80, 0]  # 最后一个宽度为0，表示隐藏列
        for col, width in zip(columns, col_widths):
            self.course_table.heading(col, text=col)
            self.course_table.column(col, width=width, anchor="center")

        # 添加滚动条
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.course_table.yview)
        self.course_table.configure(yscrollcommand=scrollbar.set)

        # 布局
        self.course_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_right_panel(self):
        """创建右侧面板"""
        # 登录区域
        login_frame = ttk.LabelFrame(self.right_panel, text="用户登录", padding=15)
        login_frame.pack(fill=tk.X, pady=(0, 10))

        # 表单元素
        ttk.Label(login_frame, text="学号:").grid(row=0, column=0, sticky=tk.E, pady=5)
        self.username_entry = ttk.Entry(login_frame)
        self.username_entry.grid(row=0, column=1, sticky=tk.W, pady=5)

        ttk.Label(login_frame, text="密码:").grid(row=1, column=0, sticky=tk.E, pady=5)
        self.password_entry = ttk.Entry(login_frame, show="*")
        self.password_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

        self.login_btn = ttk.Button(login_frame, text="登录", command=self.do_login)
        self.login_btn.grid(row=2, column=0, columnspan=2, pady=10)

        # 用户信息显示区域
        self.user_info_frame = ttk.Frame(login_frame)
        self.user_info_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=5)

        ttk.Label(self.user_info_frame, text="姓名:").pack(side=tk.LEFT)
        self.name_label = ttk.Label(self.user_info_frame, text="未登录", foreground="gray")
        self.name_label.pack(side=tk.LEFT, padx=5)

        ttk.Label(self.user_info_frame, text="班级:").pack(side=tk.LEFT)
        self.class_label = ttk.Label(self.user_info_frame, text="未登录", foreground="gray")
        self.class_label.pack(side=tk.LEFT, padx=5)

        # 登录状态显示
        self.login_status = ttk.Label(login_frame, text="状态: 未登录", foreground="red")
        self.login_status.grid(row=4, column=0, columnspan=2, pady=5)

        # 分隔线
        ttk.Separator(self.right_panel).pack(fill=tk.X, pady=5)

        # 评教控制区域
        eval_frame = ttk.LabelFrame(self.right_panel, text="评教控制", padding=10)
        eval_frame.pack(fill=tk.X, pady=(0, 10))

        # 自动评教并提交按钮
        self.submit_eval_btn = ttk.Button(
            eval_frame,
            text="自动评教并提交",
            command=lambda: self.start_evaluation("submit"),
            state=tk.DISABLED  # 初始禁用
        )
        self.submit_eval_btn.pack(fill=tk.X, pady=5)

        # 自动评教并保存按钮
        self.save_eval_btn = ttk.Button(
            eval_frame,
            text="自动评教并保存",
            command=lambda: self.start_evaluation("save"),
            state=tk.DISABLED  # 初始禁用
        )
        self.save_eval_btn.pack(fill=tk.X, pady=5)

        # 使用提示
        help_frame = ttk.LabelFrame(self.right_panel, text="使用提示", padding=10)
        help_frame.pack(fill=tk.BOTH, expand=True)

        help_text = """
    欢迎使用全自动评教系统 Design By JiuJiu
        From 2025/06/19 15:00 ~ 21:00
1. 使用学号和密码登录教务系统
2. 系统自动加载待评教课程
3. 选择课程后点击"自动评教并提交"或"自动评教并保存"
4. 系统将自动完成评价并记录日志，修改客观评价请到"sentences.txt"

注意：
- 请勿频繁操作
- 评教完成后请检查结果
- 遇到问题请联系：
- wx公众号:玖玖捌
- Email:786452808@qq.com
- GitHub:https://github.com/JiuJiu998 
"""

        help_label = ttk.Label(
            help_frame,
            text=help_text,
            wraplength=250,  # 限制换行宽度
            justify=tk.LEFT
        )
        help_label.pack(fill=tk.BOTH, expand=True)

    def update_ui_state(self):
        """根据登录状态更新UI元素状态"""
        if self.is_logged_in:
            # 登录状态
            self.login_status.config(text="状态: 已登录", foreground="green")
            self.submit_eval_btn.config(state=tk.NORMAL)
            self.save_eval_btn.config(state=tk.NORMAL)
            self.select_all_btn.config(state=tk.NORMAL)
            self.deselect_all_btn.config(state=tk.NORMAL)
            self.login_btn.config(text="注销", command=self.do_logout)

            # 更新学生信息显示
            self.name_label.config(text=self.student_name, foreground="black")
            self.class_label.config(text=self.student_class, foreground="black")
        else:
            # 未登录状态
            self.login_status.config(text="状态: 未登录", foreground="red")
            self.submit_eval_btn.config(state=tk.NORMAL)
            self.save_eval_btn.config(state=tk.NORMAL)
            self.select_all_btn.config(state=tk.DISABLED)
            self.deselect_all_btn.config(state=tk.DISABLED)
            self.login_btn.config(text="登录", command=self.do_login)

            # 清空学生信息显示
            self.name_label.config(text="未登录", foreground="gray")
            self.class_label.config(text="未登录", foreground="gray")

    def do_login(self):
        """处理登录"""
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            self.log("错误: 请输入学号和密码", "error")
            return

        # 登录
        try:
            self.stu = Student(account=username, password=password)

            # 模拟登录过程
            # self.log(f"正在验证用户： {username}-{password}")
            self.is_logged_in = True
            loginResult = self.stu.login()
            if loginResult[0]:
                self.log(f"用户 {username} 登录成功")
            else:
                self.log(f"用户 {username} 登录失败：{loginResult[1]}", level="error")
                return

            self.student_name = self.stu.name
            self.student_class = self.stu.className

            self.log(f"学生姓名: {self.student_name}")
            self.log(f"学生班级: {self.student_class}")

            # 更新UI状态
            self.update_ui_state()

            # 加载控制器数据
            self.autoSubmitter = AutoSubmitter(session=self.stu.session, baseUrl=self.stu.baseUrl, logger=self.log)
            self.log("自动评教控制器加载完毕")

            # 加载评教数据
            self.load_course_data()
            self.log("待评教课程数据加载完毕")

        except Exception as e:
            self.log(f"登录失败: {str(e)}", "error")

    def do_logout(self):
        """处理注销"""
        self.is_logged_in = False
        self.student_name = ""
        self.student_class = ""
        self.stu = None
        self.log("用户已注销")
        self.clear_course_table()
        self.update_ui_state()

    def clear_course_table(self):
        """清空 course_table 的内容"""
        for i in self.course_table.get_children():
            self.course_table.delete(i)

    def load_course_data(self):
        """加载数据"""
        evaluateList = self.stu.getEvaluateInfo()
        courses = []
        for evaluate in evaluateList:
            # 逐个取出操作链接进行获取待评教课程
            evaluateCourse = self.autoSubmitter.parse_course_list(evaluate['操作链接'], evaluate['学年学期'])
            courses.append(evaluateCourse)
        sample_courses = [
            (
                course['序号'],
                course['课程编号'],
                course['学年学期'],
                course['课程名称'],
                course['授课教师'],
                course['是否提交'],
                course['操作链接']
            )
            for sublist in courses
            for course in sublist
        ]

        for course in sample_courses:
            self.course_table.insert("", tk.END, values=course)

    def select_all_courses(self):
        """全选所有未评课程"""
        # 先取消当前所有选择
        self.course_table.selection_remove(self.course_table.selection())

        # 获取所有课程项
        all_items = self.course_table.get_children()

        # 只选择未评的课程
        for item in all_items:
            course_values = self.course_table.item(item, 'values')
            if len(course_values) > 5 and course_values[5] == "否":
                self.course_table.selection_add(item)

        selected_count = len(self.course_table.selection())
        self.log(f"已选择 {selected_count} 门未评课程")

    def deselect_all_courses(self):
        """全不选课程"""
        self.course_table.selection_remove(self.course_table.selection())
        self.log("已取消所有选择")

    def start_evaluation(self, submit_mode="save"):
        """开始评教
        :param submit_mode: 'save'表示保存，'submit'表示提交
        """
        selected = self.course_table.selection()

        if not selected:
            self.log("错误: 请选择要评教的课程", "error")
            return

        # 过滤出未评课程
        to_evaluate = [
            item for item in selected
            if "否" in self.course_table.item(item, "values")[-2]
        ]

        if not to_evaluate:
            self.log("错误: 所选课程均已评教", "error")
            return

        action = "提交" if submit_mode == "submit" else "保存"
        self.log(f"开始评教并{action} {len(to_evaluate)} 门课程...")

        # 禁用按钮防止重复点击
        self.submit_eval_btn.config(state=tk.DISABLED)
        self.save_eval_btn.config(state=tk.DISABLED)

        # 这里添加实际的评教逻辑
        for item in to_evaluate:
            course_info = self.course_table.item(item, "values")
            self.log(f"正在评教: {course_info[3]} - {course_info[4]}")

            self.autoSubmitter.load_once_course(course_info[6])
            data = self.autoSubmitter.generate_submission_data(submitMode=submit_mode)

            response = self.stu.session.post(
                url="http://jwn.ccdgut.edu.cn/jsxsd/xspj/xspj_save.do",
                data=data
            )

            alert_pattern = r"alert\('([^']*)'\)"
            match = re.search(alert_pattern, response.text)

            if match:
                alert_message = match.group(1)
                self.log(f"成功评教<{course_info[3]}>，评教结果({action}): {alert_message}", level="error")
            else:
                self.log(f"错误：未找到评教结果,{response.text}", level="error")

            time.sleep(1)

            # 模拟处理时间
            self.root.update()

            # 更新状态为已评（仅当提交时）
            if submit_mode == "submit":
                values = list(course_info)
                values[-2] = "是"
                self.course_table.item(item, values=values)

        self.log(f"评教并{action}完成!")
        winsound.MessageBeep()
        self.submit_eval_btn.config(state=tk.NORMAL)
        self.save_eval_btn.config(state=tk.NORMAL)

    def log(self, message, level="info"):
        """记录日志"""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_entry = f"{timestamp} {message}"

        # 添加到队列供后台线程写入文件
        self.log_queue.put((log_entry, level))

        # 更新UI
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry + "\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

        # 根据日志级别设置颜色
        if level == "error":
            self.log_text.tag_add("error", "end-2c linestart", "end-2c lineend")
            self.log_text.tag_config("error", foreground="red")

    def write_logs_to_file(self):
        """后台线程写入日志到文件"""
        while True:
            try:
                message, level = self.log_queue.get(timeout=1)
                log_date = datetime.now().strftime("%Y-%m-%d")
                log_file = os.path.join(self.log_dir, f"{log_date}.log")

                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"{message}\n")
            except queue.Empty:
                continue

    def process_log_queue(self):
        """处理日志队列 (主线程定时调用)"""
        try:
            while True:
                message, level = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.config(state=tk.DISABLED)
                self.log_text.see(tk.END)

                if level == "error":
                    self.log_text.tag_add("error", "end-2c linestart", "end-2c lineend")
                    self.log_text.tag_config("error", foreground="red")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_log_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = TeachingEvaluationUI(root)
    root.mainloop()