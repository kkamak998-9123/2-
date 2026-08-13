"""
간단한 데스크톱 계산기 (tkinter)

기능
- 사칙연산 (+, -, *, /), 퍼센트(%), 부호변환(±), 백스페이스(⌫)
- 메모리 기능: MC(메모리 지우기), MR(메모리 불러오기), M+(더하기), M-(빼기)
- K 기능(상수/정수 계산): 예) "3 x" 입력 후 K를 켜면 3이 곱셈 상수로 고정됨.
  이후 숫자만 입력하고 '='를 누르면 매번 그 숫자에 3을 곱한 값이 나옴.
  (예: K 켠 상태에서 3 x K → 5 = (15), 7 = (21), 10 = (30) ...)
"""

import tkinter as tk

MAX_DIGITS = 15


class Calculator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("계산기")
        self.resizable(False, False)
        self.configure(bg="#1e1e1e")

        # 상태값
        self.display_str = "0"
        self.expr_operand1 = None
        self.pending_op = None
        self.last_op = None
        self.last_operand = None
        self.new_entry = True
        self.result_shown = False
        self.memory = 0.0
        self.k_mode = False
        self.error = False

        self._build_ui()
        self._refresh_display()

    # ---------- UI ----------
    def _build_ui(self):
        # 상태 표시줄 (M, K 인디케이터)
        self.status_var = tk.StringVar(value="")
        status_label = tk.Label(
            self, textvariable=self.status_var, anchor="e",
            bg="#1e1e1e", fg="#4fc3f7", font=("Segoe UI", 10, "bold"),
        )
        status_label.grid(row=0, column=0, columnspan=5, sticky="ew", padx=10, pady=(8, 0))

        # 디스플레이
        self.display_var = tk.StringVar(value="0")
        display = tk.Label(
            self, textvariable=self.display_var, anchor="e",
            bg="#1e1e1e", fg="white", font=("Consolas", 28), padx=10,
        )
        display.grid(row=1, column=0, columnspan=5, sticky="ew", padx=10, pady=(0, 10))

        btn_specs = [
            # (row, col, text, colspan, style, command)
            (2, 0, "MC", 1, "mem", self.mem_clear),
            (2, 1, "MR", 1, "mem", self.mem_recall),
            (2, 2, "M+", 1, "mem", self.mem_add),
            (2, 3, "M-", 1, "mem", self.mem_sub),
            (2, 4, "K", 1, "k", self.toggle_k),

            (3, 0, "%", 1, "fn", self.percent),
            (3, 1, "CE", 1, "fn", self.clear_entry),
            (3, 2, "C", 1, "fn", self.clear_all),
            (3, 3, "⌫", 1, "fn", self.backspace),
            (3, 4, "÷", 1, "op", lambda: self.on_operator("/")),

            (4, 0, "7", 1, "num", lambda: self.on_digit("7")),
            (4, 1, "8", 1, "num", lambda: self.on_digit("8")),
            (4, 2, "9", 1, "num", lambda: self.on_digit("9")),
            (4, 3, "±", 1, "fn", self.negate),
            (4, 4, "×", 1, "op", lambda: self.on_operator("*")),

            (5, 0, "4", 1, "num", lambda: self.on_digit("4")),
            (5, 1, "5", 1, "num", lambda: self.on_digit("5")),
            (5, 2, "6", 1, "num", lambda: self.on_digit("6")),
            (5, 3, "0", 1, "num", lambda: self.on_digit("0")),
            (5, 4, "−", 1, "op", lambda: self.on_operator("-")),

            (6, 0, "1", 1, "num", lambda: self.on_digit("1")),
            (6, 1, "2", 1, "num", lambda: self.on_digit("2")),
            (6, 2, "3", 1, "num", lambda: self.on_digit("3")),
            (6, 3, ".", 1, "num", self.on_dot),
            (6, 4, "+", 1, "op", lambda: self.on_operator("+")),
        ]

        colors = {
            "num": ("#3a3a3a", "white"),
            "fn": ("#5a5a5a", "white"),
            "op": ("#4fc3f7", "black"),
            "mem": ("#6a4fc3", "white"),
            "k": ("#c37a4f", "white"),
        }

        self.k_button = None
        for row, col, text, colspan, style, cmd in btn_specs:
            bg, fg = colors[style]
            b = tk.Button(
                self, text=text, command=cmd, bg=bg, fg=fg,
                font=("Segoe UI", 13), relief="flat", padx=10, pady=14,
                activebackground="#777777",
            )
            b.grid(row=row, column=col, columnspan=colspan, sticky="nsew", padx=3, pady=3)
            if text == "K":
                self.k_button = b

        equals = tk.Button(
            self, text="=", command=self.on_equals, bg="#0288d1", fg="white",
            font=("Segoe UI", 15, "bold"), relief="flat", padx=10, pady=14,
        )
        equals.grid(row=7, column=0, columnspan=5, sticky="nsew", padx=3, pady=(3, 8))

        for c in range(5):
            self.grid_columnconfigure(c, weight=1)

        # 키보드 입력 지원
        self.bind("<Key>", self._on_key)

    def _on_key(self, event):
        c = event.char
        if c and c.isdigit():
            self.on_digit(c)
        elif c == ".":
            self.on_dot()
        elif c == "+":
            self.on_operator("+")
        elif c == "-":
            self.on_operator("-")
        elif c == "*":
            self.on_operator("*")
        elif c == "/":
            self.on_operator("/")
        elif event.keysym in ("Return", "KP_Enter") or c == "=":
            self.on_equals()
        elif event.keysym == "BackSpace":
            self.backspace()
        elif event.keysym == "Escape":
            self.clear_all()

    # ---------- 표시 갱신 ----------
    def _refresh_display(self):
        self.display_var.set(self.display_str)
        status_parts = []
        if self.memory != 0:
            status_parts.append("M")
        if self.k_mode:
            status_parts.append("K")
        self.status_var.set("  ".join(status_parts))
        if self.k_button:
            self.k_button.configure(bg="#e0863f" if self.k_mode else "#c37a4f")

    def _format(self, value):
        if value == int(value) and abs(value) < 1e15:
            s = str(int(value))
        else:
            s = f"{value:.10f}".rstrip("0").rstrip(".")
        if len(s.replace("-", "").replace(".", "")) > MAX_DIGITS:
            s = f"{value:.6e}"
        return s

    def set_display_error(self, msg):
        self.display_str = msg
        self.error = True
        self.expr_operand1 = None
        self.pending_op = None
        self.last_op = None
        self.last_operand = None
        self.new_entry = True
        self.result_shown = False
        self._refresh_display()

    # ---------- 입력 처리 ----------
    def on_digit(self, d):
        if self.error:
            self.clear_all()
        if self.new_entry:
            self.display_str = d
            self.new_entry = False
        else:
            if len(self.display_str.replace("-", "").replace(".", "")) >= MAX_DIGITS:
                return
            self.display_str = ("" if self.display_str == "0" else self.display_str) + d
        self.result_shown = False
        self._refresh_display()

    def on_dot(self):
        if self.error:
            self.clear_all()
        if self.new_entry:
            self.display_str = "0."
            self.new_entry = False
        elif "." not in self.display_str:
            self.display_str += "."
        self.result_shown = False
        self._refresh_display()

    def apply(self, a, op, b):
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            if b == 0:
                raise ZeroDivisionError
            return a / b
        raise ValueError(op)

    def on_operator(self, op):
        if self.error:
            return
        try:
            if self.pending_op is not None and not self.new_entry:
                op2 = float(self.display_str)
                result = self.apply(self.expr_operand1, self.pending_op, op2)
                self.last_op = self.pending_op
                self.last_operand = op2
                self.expr_operand1 = result
                self.display_str = self._format(result)
            else:
                self.expr_operand1 = float(self.display_str)
        except ZeroDivisionError:
            self.set_display_error("0으로 나눌 수 없음")
            return
        self.pending_op = op
        self.new_entry = True
        self.result_shown = False
        self._refresh_display()

    def on_equals(self):
        if self.error:
            return
        try:
            if self.pending_op is not None:
                op1 = self.expr_operand1
                op2 = float(self.display_str)
                result = self.apply(op1, self.pending_op, op2)
                self.last_op = self.pending_op
                self.last_operand = op2
                self.pending_op = None
            elif self.last_op is not None:
                if self.result_shown or self.k_mode:
                    op1 = float(self.display_str)
                    result = self.apply(op1, self.last_op, self.last_operand)
                else:
                    return
            else:
                return
        except ZeroDivisionError:
            self.set_display_error("0으로 나눌 수 없음")
            return
        self.display_str = self._format(result)
        self.expr_operand1 = result
        self.new_entry = True
        self.result_shown = True
        self._refresh_display()

    def percent(self):
        if self.error:
            return
        try:
            value = float(self.display_str)
            if self.pending_op is not None and self.expr_operand1 is not None:
                result = self.expr_operand1 * (value / 100)
            else:
                result = value / 100
            self.display_str = self._format(result)
            self.new_entry = True
            self._refresh_display()
        except ValueError:
            pass

    def negate(self):
        if self.error:
            return
        try:
            value = float(self.display_str)
            self.display_str = self._format(-value)
            self._refresh_display()
        except ValueError:
            pass

    def backspace(self):
        if self.error:
            self.clear_all()
            return
        if self.new_entry:
            return
        self.display_str = self.display_str[:-1]
        if self.display_str in ("", "-"):
            self.display_str = "0"
            self.new_entry = True
        self._refresh_display()

    def clear_entry(self):
        if self.error:
            self.clear_all()
            return
        self.display_str = "0"
        self.new_entry = True
        self.result_shown = False
        self._refresh_display()

    def clear_all(self):
        self.display_str = "0"
        self.expr_operand1 = None
        self.pending_op = None
        self.last_op = None
        self.last_operand = None
        self.new_entry = True
        self.result_shown = False
        self.error = False
        self._refresh_display()

    # ---------- 메모리 ----------
    def mem_clear(self):
        self.memory = 0.0
        self._refresh_display()

    def mem_recall(self):
        self.display_str = self._format(self.memory)
        self.new_entry = True
        self._refresh_display()

    def mem_add(self):
        try:
            self.memory += float(self.display_str)
            self.new_entry = True
            self._refresh_display()
        except ValueError:
            pass

    def mem_sub(self):
        try:
            self.memory -= float(self.display_str)
            self.new_entry = True
            self._refresh_display()
        except ValueError:
            pass

    # ---------- K (상수 계산) ----------
    def toggle_k(self):
        self.k_mode = not self.k_mode
        self._refresh_display()


if __name__ == "__main__":
    app = Calculator()
    app.mainloop()
