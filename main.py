import flet as ft
import datetime
import asyncio  # 引入异步库，替代 threading


# 必须改为 async main
async def main(page: ft.Page):
    # --- 1. 窗口与设备适配设置 ---
    page.title = "Calculator"
    page.bgcolor = "#FFFFFF"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT  # 强制亮色模式，避免系统深色模式影响

    # 移除桌面端的 window 设置，手机会自动全屏
    # page.window_width = ... (不需要)

    # --- 2. 核心逻辑状态 ---
    state = {
        "display": "0",
        "last_button": None,
        "hidden_mode": False,
        "hidden_inputs": [],
        "is_locked": False,
        "total_sum": 0,
        "waiting_for_new_input": False,
        "auto_update_running": False
    }

    # --- 3. 核心计算与功能函数 (异步化) ---

    def get_time_code():
        now = datetime.datetime.now()
        if now.second >= 30:
            target_time = now + datetime.timedelta(minutes=1)
        else:
            target_time = now
        time_str = f"{target_time.month}{target_time.day:02d}{target_time.hour:02d}{target_time.minute:02d}"
        return int(time_str)

    # 异步更新任务
    async def auto_update_task():
        while state["auto_update_running"]:
            target_val = get_time_code() - state["total_sum"]
            if state["display"] != str(target_val):
                state["display"] = str(target_val)
                display_text.value = state["display"]
                await page.update_async()  # 异步更新 UI
            await asyncio.sleep(1)  # 非阻塞等待

    # 触发乱跳逻辑
    async def trigger_random_jump():
        if state["is_locked"]:
            if not state["auto_update_running"]:
                state["auto_update_running"] = True
                state["display"] = str(get_time_code() - state["total_sum"])
                await update_display()
                # 启动后台异步任务
                asyncio.create_task(auto_update_task())

    # --- 4. 交互事件处理 (Async) ---

    async def on_button_click(e):
        data = e.control.data

        # [逻辑 A] 锁死模式
        if state["is_locked"]:
            if data == "=":
                state["auto_update_running"] = False
                state["display"] = str(get_time_code())
                await update_display()
            else:
                await trigger_random_jump()
            return

        # [逻辑 B] 激活秘密模式
        if data == "." and state["last_button"] == ".":
            state["hidden_mode"] = True
            state["display"] = "0"
            state["hidden_inputs"] = []
            await update_display()
            return

        # [逻辑 C] 秘密模式输入
        if state["hidden_mode"]:
            if data == "+":
                try:
                    state["hidden_inputs"].append(float(state["display"]))
                except:
                    pass
                current_total = sum(state["hidden_inputs"])

                if len(state["hidden_inputs"]) == 3:
                    state["total_sum"] = int(current_total)
                    state["display"] = str(state["total_sum"])
                    state["is_locked"] = True
                    await page.update_async()
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
        await update_display()

    async def on_background_tap(e):
        await trigger_random_jump()

    async def update_display():
        display_text.value = state["display"]
        await page.update_async()

    # --- 5. UI 构建 (响应式布局) ---

    # 动态计算按钮大小：(屏幕宽度 - 间距) / 4
    # Vivo X200s 逻辑宽度约 390-412dp。我们留出左右各 20dp 的 padding，中间间距 15dp
    # 4 * btn_size + 3 * 15 = (page.width - 40)
    # 但 page.width 在初始化时可能不准，所以我们使用 Flexible 和 Row 的对齐来自动适应

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
        ])
    )

    display_text = ft.Text(value="0", color="black", size=70, weight="w400", text_align=ft.TextAlign.RIGHT)
    display_area = ft.Container(
        content=display_text,
        alignment=ft.alignment.bottom_right,
        expand=True,  # 占据所有剩余空间
        padding=ft.padding.only(right=30, bottom=10)
    )

    tools_row = ft.Container(
        padding=ft.padding.only(left=25, bottom=10),
        content=ft.Row([
            ft.Icon(name="history", color="#9E9E9E", size=24),
            ft.Icon(name="calculate_outlined", color="#9E9E9E", size=24),
        ], spacing=20)
    )

    # 按钮样式定义
    BG_NUM = "#F7F7F7"
    BG_OP_PINK = "#FFEBEE"
    BG_RED = "#F44336"
    TXT_RED = "#D32F2F"
    TXT_GREY = "#9E9E9E"

    # 响应式按钮生成器：使用 expand=1 让按钮自动填满行，保持圆形
    def btn(text, bg="#F7F7F7", color="black", data=None):
        font_size = 28
        if text in ["mc", "m+", "m-", "mr"]: font_size = 20

        # 按钮容器
        return ft.Container(
            content=ft.Text(text, color=color, size=font_size, weight="w400"),
            alignment=ft.alignment.center,
            bgcolor=bg,
            shape=ft.BoxShape.CIRCLE,  # 强制保持圆形
            on_click=on_button_click,
            data=data or text,
            ink=True,
            aspect_ratio=1,  # 宽高比 1:1，保证是正圆
            expand=1  # 在 Row 中自动伸缩
        )

    def icon_btn(icon_name, bg="#F7F7F7", color="#D32F2F", data=None):
        return ft.Container(
            content=ft.Icon(name=icon_name, color=color, size=28),
            alignment=ft.alignment.center,
            bgcolor=bg,
            shape=ft.BoxShape.CIRCLE,
            on_click=on_button_click,
            data=data,
            ink=True,
            aspect_ratio=1,
            expand=1
        )

    # 辅助函数：创建一行按钮，并添加间距
    def btn_row(controls):
        # 在按钮之间插入间隔
        spaced_controls = []
        for i, control in enumerate(controls):
            spaced_controls.append(control)
            if i < len(controls) - 1:
                # 按钮之间的间距
                spaced_controls.append(ft.Container(width=15))
        return ft.Row(spaced_controls, alignment=ft.MainAxisAlignment.CENTER)

    # 键盘布局
    keypad = ft.Container(
        padding=20,
        content=ft.Column([
            btn_row([btn("mc", "transparent", TXT_GREY), btn("m+", "transparent", TXT_GREY),
                     btn("m-", "transparent", TXT_GREY), btn("mr", "transparent", TXT_GREY)]),
            btn_row([btn("AC", BG_NUM, TXT_RED), icon_btn("backspace_outlined", BG_NUM, TXT_RED, "x"),
                     btn("+/-", BG_NUM, TXT_RED), btn("÷", BG_OP_PINK, TXT_RED)]),
            btn_row([btn("7", BG_NUM), btn("8", BG_NUM), btn("9", BG_NUM), btn("×", BG_OP_PINK, TXT_RED)]),
            btn_row([btn("4", BG_NUM), btn("5", BG_NUM), btn("6", BG_NUM), btn("-", BG_OP_PINK, TXT_RED)]),
            btn_row([btn("1", BG_NUM), btn("2", BG_NUM), btn("3", BG_NUM), btn("+", BG_OP_PINK, TXT_RED)]),
            btn_row([btn("%", BG_NUM), btn("0", BG_NUM), btn(".", BG_NUM), btn("=", BG_RED, "white")]),
        ], spacing=15)  # 行间距
    )

    # 组装主布局
    main_layout = ft.Column([
        header,
        display_area,
        tools_row,
        keypad,
        # 底部留白，防止被手势条遮挡
        ft.Container(height=10)
    ], expand=True)

    # --- 6. 最终层级 (使用 SafeArea) ---
    # SafeArea 会自动避开摄像头挖孔和底部黑条
    page.add(
        ft.SafeArea(
            ft.GestureDetector(
                on_tap=on_background_tap,
                content=ft.Container(
                    content=main_layout,
                    bgcolor="white",
                    expand=True
                ),
                expand=True
            ),
            expand=True
        )
    )


ft.app(target=main)
