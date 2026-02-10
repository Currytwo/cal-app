import flet as ft
import datetime
import threading
import time


def main(page: ft.Page):
    # --- 1. 窗口基础设置 ---
    page.title = "Calculator"
    page.bgcolor = "#FFFFFF"
    page.window_width = 390
    page.window_height = 844
    page.padding = 0

    # --- 2. 核心逻辑状态 ---
    state = {
        "display": "0",
        "last_button": None,
        "hidden_mode": False,  # 是否激活秘密模式
        "hidden_inputs": [],  # 存储秘密输入的数字
        "is_locked": False,  # 是否处于锁屏状态
        "total_sum": 0,  # 秘密数字的总和
        "waiting_for_new_input": False,
        "auto_update_running": False
    }

    # --- 3. 核心计算与功能函数 ---

    # [功能] 获取当前时间代码
    def get_time_code():
        now = datetime.datetime.now()
        if now.second >= 30:
            target_time = now + datetime.timedelta(minutes=1)
        else:
            target_time = now
        time_str = f"{target_time.month}{target_time.day:02d}{target_time.hour:02d}{target_time.minute:02d}"
        return int(time_str)

    # [功能] 自动更新任务 (后台线程)
    def auto_update_task():
        while state["auto_update_running"]:
            target_val = get_time_code() - state["total_sum"]
            if state["display"] != str(target_val):
                state["display"] = str(target_val)
                # 必须在主线程更新 UI
                display_text.value = state["display"]
                page.update()
            time.sleep(1)

    # [功能] 触发乱跳逻辑 (封装成函数，供按钮和背景使用)
    def trigger_random_jump():
        if state["is_locked"]:
            if not state["auto_update_running"]:
                state["auto_update_running"] = True
                # 立即跳动一次
                state["display"] = str(get_time_code() - state["total_sum"])
                update_display()
                # 启动后台线程
                threading.Thread(target=auto_update_task, daemon=True).start()

    # --- 4. 交互事件处理 ---

    def on_button_click(e):
        data = e.control.data

        # [逻辑 A] 锁死模式 (关键修改！)
        # 不再通过遮罩拦截，而是直接在这里判断
        if state["is_locked"]:
            if data == "=":
                # === 点击等号：揭秘 ===
                state["auto_update_running"] = False
                state["display"] = str(get_time_code())  # 显示最终时间
                # 此时依然保持 is_locked = True，等待用户看够了自己退出或重置
                # 如果你想按等号后解锁，可以在这里加 state["is_locked"] = False
                update_display()
            else:
                # === 点击其他任何按钮：触发乱跳 ===
                trigger_random_jump()
            return

        # [逻辑 B] 激活秘密模式 (双击 .)
        if data == "." and state["last_button"] == ".":
            state["hidden_mode"] = True
            state["display"] = "0"
            state["hidden_inputs"] = []
            update_display()
            return

        # [逻辑 C] 秘密模式输入
        if state["hidden_mode"]:
            if data == "+":
                try:
                    state["hidden_inputs"].append(float(state["display"]))
                except:
                    pass
                current_total = sum(state["hidden_inputs"])

                # 第三次按加号 -> 进入锁屏
                if len(state["hidden_inputs"]) == 3:
                    state["total_sum"] = int(current_total)
                    state["display"] = str(state["total_sum"])
                    state["is_locked"] = True
                    # 这里不需要再显示任何 overlay 了，逻辑锁已生效
                    page.update()
                else:
                    state["display"] = str(int(current_total))
                    state["waiting_for_new_input"] = True
            elif data in "0123456789.":
                if state["waiting_for_new_input"] or state["display"] == "0":
                    state["display"] = ""
                    state["waiting_for_new_input"] = False
                state["display"] += data

        # [逻辑 D] 普通计算器
        else:
            if data == "AC":
                state["display"] = "0"
            elif data == "x":
                state["display"] = state["display"][:-1] if len(state["display"]) > 1 else "0"
            elif data == "=":
                try:
                    expr = state["display"].replace("÷", "/").replace("×", "*")
                    state["display"] = str(int(eval(expr)))
                except:
                    state["display"] = "Error"
            elif data in "0123456789.+-÷×%":
                if state["display"] == "0" and data not in ".":
                    state["display"] = data
                else:
                    state["display"] += data

        state["last_button"] = data
        update_display()

    # 背景点击事件 (处理点击按钮之间的空白处)
    def on_background_tap(e):
        # 点击空白处也触发乱跳
        trigger_random_jump()

    def update_display():
        display_text.value = state["display"]
        page.update()

    # --- 5. UI 构建 (由内向外) ---

    # 顶部导航
    header = ft.Container(
        padding=ft.padding.only(left=20, right=20, top=10),
        content=ft.Row([
            ft.Column([
                ft.Text("计算", size=26, weight="bold", color="black"),
                ft.Container(bgcolor="#D32F2F", height=3, width=30, border_radius=2)
            ], spacing=2),
            ft.Container(content=ft.Text("汇率", size=20, color="#9E9E9E"), padding=ft.padding.only(bottom=5)),
            ft.Container(expand=True),
            ft.IconButton(icon="add", icon_color="black", icon_size=28),
            ft.IconButton(icon="settings_outlined", icon_color="black", icon_size=24)
        ], alignment=ft.MainAxisAlignment.START)
    )

    # 显示屏
    display_text = ft.Text(value="0", color="black", size=65, weight="w400", text_align=ft.TextAlign.RIGHT)
    display_area = ft.Container(
        content=display_text,
        alignment=ft.alignment.bottom_right,
        expand=True,
        padding=ft.padding.only(right=30, bottom=10)
    )

    # 工具栏
    tools_row = ft.Container(
        padding=ft.padding.only(left=25, bottom=10),
        content=ft.Row([
            ft.Icon(name="history", color="#9E9E9E", size=24),
            ft.Icon(name="calculate_outlined", color="#9E9E9E", size=24),
        ], spacing=20)
    )

    # 按钮生成器
    BG_NUM = "#F7F7F7"
    BG_OP_PINK = "#FFEBEE"
    BG_RED = "#F44336"
    TXT_RED = "#D32F2F"
    TXT_GREY = "#9E9E9E"

    def btn(text, bg="#F7F7F7", color="black", data=None, size=80):
        font_size = 28
        if text in ["mc", "m+", "m-", "mr"]: font_size = 20
        return ft.Container(
            content=ft.Text(text, color=color, size=font_size, weight="w400"),
            alignment=ft.alignment.center,
            width=size, height=size,
            bgcolor=bg, border_radius=size / 2,
            on_click=on_button_click, data=data or text, ink=True
        )

    def icon_btn(icon_name, bg="#F7F7F7", color="#D32F2F", data=None):
        return ft.Container(
            content=ft.Icon(name=icon_name, color=color, size=28),
            alignment=ft.alignment.center,
            width=80, height=80,
            bgcolor=bg, border_radius=40,
            on_click=on_button_click, data=data, ink=True
        )

    # 键盘区域 (最关键的布局)
    # 不再包含任何 clone 按钮，就是纯粹的布局
    keypad = ft.Container(
        padding=20,
        content=ft.Column([
            ft.Row([btn("mc", "transparent", TXT_GREY), btn("m+", "transparent", TXT_GREY),
                    btn("m-", "transparent", TXT_GREY), btn("mr", "transparent", TXT_GREY)], alignment="spaceBetween"),
            ft.Row([btn("AC", BG_NUM, TXT_RED), icon_btn("backspace_outlined", BG_NUM, TXT_RED, "x"),
                    btn("+/-", BG_NUM, TXT_RED), btn("÷", BG_OP_PINK, TXT_RED)], alignment="spaceBetween"),
            ft.Row([btn("7", BG_NUM), btn("8", BG_NUM), btn("9", BG_NUM), btn("×", BG_OP_PINK, TXT_RED)],
                   alignment="spaceBetween"),
            ft.Row([btn("4", BG_NUM), btn("5", BG_NUM), btn("6", BG_NUM), btn("-", BG_OP_PINK, TXT_RED)],
                   alignment="spaceBetween"),
            ft.Row([btn("1", BG_NUM), btn("2", BG_NUM), btn("3", BG_NUM), btn("+", BG_OP_PINK, TXT_RED)],
                   alignment="spaceBetween"),
            ft.Row([btn("%", BG_NUM), btn("0", BG_NUM), btn(".", BG_NUM), btn("=", BG_RED, "white")],
                   alignment="spaceBetween"),
        ], spacing=12)
    )

    # 组装主布局
    main_layout = ft.Column([
        ft.Container(height=10),
        header,
        display_area,
        tools_row,
        keypad,
        ft.Container(height=20)
    ], expand=True)

    # --- 6. 最终层级 ---
    # 使用 GestureDetector 包裹整个页面，用于捕获点击空白处
    # 按钮的点击事件会优先于 GestureDetector 触发
    page.add(
        ft.GestureDetector(
            on_tap=on_background_tap,  # 点击背景
            content=ft.Container(
                content=main_layout,
                bgcolor="white",  # 确保有背景色以捕获点击
                expand=True
            ),
            expand=True
        )
    )


ft.app(target=main)