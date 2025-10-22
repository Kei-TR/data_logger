import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import json
import os
import csv
from PIL import Image, ImageTk  # 追加

# v1.0 2025/09/08 作成

# JSON file name
JSON_FILE = "setting.json"

# id to email file path
path_id_to_email = "//cae-sv02/CAE部/共通/log/IoT/rasPi/common/visualize/id_to_email_list.csv"

# Load data from JSON
def load_data():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    else:
        return {"email": [], "thresholds": []}

# Save data to JSON
def save_data(data):
    with open(JSON_FILE, "w", encoding="utf-8-sig") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Convert member id to email address
def convert_id_to_email(member_id):

    if os.path.exists(path_id_to_email): # csvから情報取得
        email = None
        with open(path_id_to_email, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                if row[0] == member_id:
                    email = row[1]
        return email if email else None

# Main Application Class
class ThresholdEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("設定編集アプリ")
        self.geometry("800x600")
        self.data = load_data()

        self.create_widgets()

    def create_widgets(self):
        # Email Section
        email_frame = tk.LabelFrame(self, text="メールアドレス一覧", padx=10, pady=10)
        email_frame.pack(fill="x", padx=10, pady=5)
        self.email_listbox = tk.Listbox(email_frame, height=5)
        self.email_listbox.pack(side="left", fill="x", expand=True)
        self.update_email_listbox()

        email_btn_frame = tk.Frame(email_frame)
        email_btn_frame.pack(side="right", fill="y")
        tk.Button(email_btn_frame, text="追加", command=self.add_email).pack(fill="x")
        tk.Button(email_btn_frame, text="編集", command=self.edit_email).pack(fill="x")
        tk.Button(email_btn_frame, text="削除", command=self.delete_email).pack(fill="x")

        # Threshold Section
        threshold_frame = tk.LabelFrame(self, text="閾値一覧", padx=10, pady=10)
        threshold_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("channel", "value_alltime", "border", "time_high", "time_low", "time_mid")
        self.tree = ttk.Treeview(threshold_frame, columns=columns, show="headings")

        # 項目名を設定
        self.tree.heading("channel", text="チャンネル番号")
        self.tree.heading("value_alltime", text="測定値")
        self.tree.heading("border", text="矩形波HIGH/LOW")
        self.tree.heading("time_high", text="HIGH継続時間(秒)")
        self.tree.heading("time_low", text="LOW継続時間(秒)")
        self.tree.heading("time_mid", text="MID継続時間(秒)")

        # 列幅を設定
        self.tree.column("channel", width=80, anchor="center")
        self.tree.column("value_alltime", width=100, anchor="center")
        self.tree.column("border", width=100, anchor="center")
        self.tree.column("time_high", width=90, anchor="center")
        self.tree.column("time_low", width=90, anchor="center")
        self.tree.column("time_mid", width=100, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.update_threshold_list()

        threshold_btn_frame = tk.Frame(self)
        threshold_btn_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(threshold_btn_frame, text="追加", command=self.add_threshold).pack(side="left")
        tk.Button(threshold_btn_frame, text="編集", command=self.edit_threshold).pack(side="left")
        tk.Button(threshold_btn_frame, text="削除", command=self.delete_threshold).pack(side="left")

    def update_email_listbox(self):
        self.email_listbox.delete(0, tk.END)
        for email in self.data["email"]:
            self.email_listbox.insert(tk.END, email)

    def update_threshold_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in self.data["thresholds"]:
            self.tree.insert("", tk.END, values=(
                item.get("channel", ""),
                f'{item.get("value_alltime", {}).get("min", "なし")} ~ {item.get("value_alltime", {}).get("max", "なし")}',
                f'{item.get("border", {}).get("LOW", "なし")} ~ {item.get("border", {}).get("HIGH", "なし")}',
                f'{item.get("time_high", {}).get("min", "なし")} ~ {item.get("time_high", {}).get("max", "なし")}',
                f'{item.get("time_low", {}).get("min", "なし")} ~ {item.get("time_low", {}).get("max", "なし")}',
                f'{item.get("time_mid", {}).get("min", "なし")} ~ {item.get("time_mid", {}).get("max", "なし")}'
            ))

    def add_email(self):

        new_email = simpledialog.askstring("メール追加", "メールアドレスか社員番号を入力してください：")

        if new_email:

            # 社員番号→メールアドレスへ変換
            if len(new_email) == 5:
                new_email = convert_id_to_email(new_email)
                if not new_email:
                    messagebox.showwarning("警告", "無効な社員番号です。")
                    return

            # メールアドレスを追加
            self.data["email"].append(new_email)
            self.update_email_listbox()
            save_data(self.data)

    def edit_email(self):

        selection = self.email_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "編集するメールアドレスを選択してください。")
            return

        index = selection[0]
        current_email = self.data["email"][index]
        new_email = simpledialog.askstring("メール編集", "メールアドレスか社員番号を入力してください：", initialvalue=current_email)

        if new_email:

            # 社員番号→メールアドレスへ変換
            if len(new_email) == 5:
                new_email = convert_id_to_email(new_email)
                if not new_email:
                    messagebox.showwarning("警告", "無効な社員番号です。")
                    return
    
            # メールアドレスを更新
            self.data["email"][index] = new_email
            self.update_email_listbox()
            save_data(self.data)

    def delete_email(self):
        selection = self.email_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "削除するメールアドレスを選択してください。")
            return
        index = selection[0]
        if messagebox.askyesno("確認", "選択したメールアドレスを削除しますか？"):
            del self.data["email"][index]
            self.update_email_listbox()
            save_data(self.data)

    def add_threshold(self):
        ThresholdEditor(self, None)

    def edit_threshold(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "編集する閾値を選択してください。")
            return
        index = self.tree.index(selected[0])
        ThresholdEditor(self, index)

    def delete_threshold(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "削除する閾値を選択してください。")
            return
        index = self.tree.index(selected[0])
        if messagebox.askyesno("確認", "選択したチャンネルの閾値を削除しますか？"):
            del self.data["thresholds"][index]
            self.update_threshold_list()
            save_data(self.data)

# Threshold Editor Window
class ThresholdEditor(tk.Toplevel):
    def __init__(self, master, index):
        super().__init__(master)
        self.master = master
        self.index = index
        self.title("閾値編集")
        self.geometry("600x700")
        self.data = master.data["thresholds"][index] if index is not None else {}
        self.create_widgets()

    def create_widgets(self):
    
        # 画像の場所
        img_path = "//cae-sv02/CAE部/共通/log/IoT/rasPi/common/data_logger/image.jpg"

        # 各閾値
        number_alltime_min = str(self.data.get("value_alltime", {}).get("min", ""))
        number_alltime_max = str(self.data.get("value_alltime", {}).get("max", ""))
        number_border_high = str(self.data.get("border", {}).get("HIGH", ""))
        number_border_low = str(self.data.get("border", {}).get("LOW", ""))
        number_time_high_min = str(self.data.get("time_high", {}).get("min", ""))
        number_time_high_max = str(self.data.get("time_high", {}).get("max", ""))
        number_time_low_min = str(self.data.get("time_low", {}).get("min", ""))
        number_time_low_max = str(self.data.get("time_low", {}).get("max", ""))
        number_time_mid_min = str(self.data.get("time_mid", {}).get("min", ""))
        number_time_mid_max = str(self.data.get("time_mid", {}).get("max", ""))

        # 画像の配置
        if os.path.exists(img_path):

            # 画像のサイズ取得
            img = Image.open(img_path)
            win_width = 600 # self.winfo_width() if self.winfo_width() > 0 else 300 # ウィンドウの横幅
            fixed_height = 1000  # 画像の高さの最大値（必要に応じて調整）
            orig_width, orig_height = img.size # 元画像のサイズ取得

            # ウィンドウ幅に合わせてスケールを計算
            scale_w = win_width / orig_width
            scale_h = fixed_height / orig_height
            scale = min(scale_w, scale_h)

            # アスペクト比を保ってリサイズ
            new_size = (int(orig_width * scale), int(orig_height * scale))
            img = img.resize(new_size, Image.LANCZOS)

            # 画像を配置
            self.img_tk = ImageTk.PhotoImage(img)
            #img_label = tk.Label(self, image=self.img_tk) # canvasを使わない場合
            #img_label.pack(side="top", fill="x") # canvasを使わない場合

            # Canvas作成
            canvas = tk.Canvas(self, width=new_size[0], height=new_size[1]) # 画像サイズに合わせる
            canvas.pack(side="top", fill="x")
            canvas.create_image(0, 0, anchor="nw", image=self.img_tk) # 画像をCanvasに表示

            # オーバーレイで数字を表示
            canvas.create_text(105, 55, text=f"~{number_alltime_max}", fill="red", anchor="w", font=("Arial", 16, "bold"))
            canvas.create_text(105, 55+35, text=number_border_high, fill="green", anchor="w", font=("Arial", 16, "bold"))
            canvas.create_text(105, 140, text=number_border_low, fill="blue", anchor="w", font=("Arial", 16, "bold"))
            canvas.create_text(105, 140+35, text=f"{number_alltime_min}~", fill="red", anchor="w", font=("Arial", 16, "bold"))
            canvas.create_text(270, 230, text=f"{number_time_high_min}~{number_time_high_max}", fill="green", font=("Arial", 16, "bold"))
            canvas.create_text(270+180, 230, text=f"{number_time_low_min}~{number_time_low_max}", fill="blue", font=("Arial", 16, "bold"))
            canvas.create_text(410, 302, text=f"{number_time_mid_min}~{number_time_mid_max}", fill="black", anchor="w", font=("Arial", 16, "bold"))

        self.entries = {}
        self.waveform_var = tk.BooleanVar(value=True if self.data.get("border") else False)

        tk.Label(self, text="チャンネル番号").pack()
        self.entries["channel"] = tk.Entry(self)
        self.entries["channel"].pack()
        self.entries["channel"].insert(0, self.data.get("channel", ""))

        tk.Checkbutton(self, text="矩形波", variable=self.waveform_var, command=self.toggle_fields).pack()

        # 各エントリ作成＋初期値セット
        def get_nested(d, *keys):
            for k in keys:
                d = d.get(k, {}) if isinstance(d, dict) else {}
            return d if d != {} else ""

        self.entries["value_alltime_min"] = self.create_labeled_entry("測定値 min")
        self.entries["value_alltime_min"].insert(0, str(self.data.get("value_alltime", {}).get("min", "")))
        self.entries["value_alltime_max"] = self.create_labeled_entry("測定値 max")
        self.entries["value_alltime_max"].insert(0, str(self.data.get("value_alltime", {}).get("max", "")))

        self.entries["border_LOW"] = self.create_labeled_entry("矩形波LOW")
        self.entries["border_LOW"].insert(0, str(self.data.get("border", {}).get("LOW", "")))
        self.entries["border_HIGH"] = self.create_labeled_entry("矩形波HIGH")
        self.entries["border_HIGH"].insert(0, str(self.data.get("border", {}).get("HIGH", "")))

        self.entries["time_high_min"] = self.create_labeled_entry("HIGH継続時間(秒) min")
        self.entries["time_high_min"].insert(0, str(self.data.get("time_high", {}).get("min", "")))
        self.entries["time_high_max"] = self.create_labeled_entry("HIGH継続時間(秒) max")
        self.entries["time_high_max"].insert(0, str(self.data.get("time_high", {}).get("max", "")))

        self.entries["time_low_min"] = self.create_labeled_entry("LOW継続時間(秒) min")
        self.entries["time_low_min"].insert(0, str(self.data.get("time_low", {}).get("min", "")))
        self.entries["time_low_max"] = self.create_labeled_entry("LOW継続時間(秒) max")
        self.entries["time_low_max"].insert(0, str(self.data.get("time_low", {}).get("max", "")))

        self.entries["time_mid_min"] = self.create_labeled_entry("MID継続時間(秒) min")
        self.entries["time_mid_min"].insert(0, str(self.data.get("time_mid", {}).get("min", "")))
        self.entries["time_mid_max"] = self.create_labeled_entry("MID継続時間(秒) max")
        self.entries["time_mid_max"].insert(0, str(self.data.get("time_mid", {}).get("max", "")))

        self.toggle_fields()

        tk.Button(self, text="保存", command=self.save_threshold).pack(pady=10)

    def create_labeled_entry(self, label):
        frame = tk.Frame(self)
        frame.pack(fill="x", padx=5, pady=2)
        tk.Label(frame, text=label, width=20, anchor="w").pack(side="left")
        entry = tk.Entry(frame)
        entry.pack(side="right", fill="x", expand=True)
        return entry

    def toggle_fields(self):
        state = "normal" if self.waveform_var.get() else "disabled"
        for key in ["border_LOW", "border_HIGH", "time_high_min", "time_high_max",
                    "time_low_min", "time_low_max", "time_mid_min", "time_mid_max"]:
            self.entries[key].config(state=state)

    def save_threshold(self):
        channel = self.entries["channel"].get()
        value_min = self.entries["value_alltime_min"].get()
        value_max = self.entries["value_alltime_max"].get()
        waveform = self.waveform_var.get()

        if not channel:
            messagebox.showerror("エラー", "チャンネル番号を入力してください。")
            return

        if not waveform:
            if not value_min and not value_max:
                messagebox.showerror("エラー", "閾値がどちらも入力されていません。")
                return
        else:
            low = self.entries["border_LOW"].get()
            high = self.entries["border_HIGH"].get()
            if not low and not high:
                messagebox.showerror("エラー", "LOW/HIGHがどちらも入力されていません。")
                return
            if not low:
                messagebox.showerror("エラー", "LOWに値が入っていません。")
                return
            if not high:
                messagebox.showerror("エラー", "HIGHに値が入っていません。")
                return
            other_fields = ["value_alltime_min", "value_alltime_max", "time_high_min", "time_high_max",
                            "time_low_min", "time_low_max", "time_mid_min", "time_mid_max"]
            if not any(self.entries[k].get() for k in other_fields):
                messagebox.showerror("エラー", "閾値が入力されていません。")
                return

        threshold = {
            "channel": channel
        }

        # value_alltime
        value_alltime = {}
        if value_min:
            value_alltime["min"] = float(value_min)
        if value_max:
            value_alltime["max"] = float(value_max)
        if value_alltime:
            threshold["value_alltime"] = value_alltime

        if waveform:
            # border
            border = {}
            if self.entries["border_LOW"].get():
                border["LOW"] = float(self.entries["border_LOW"].get())
            if self.entries["border_HIGH"].get():
                border["HIGH"] = float(self.entries["border_HIGH"].get())
            if border:
                threshold["border"] = border

            # time_high
            time_high = {}
            if self.entries["time_high_min"].get():
                time_high["min"] = float(self.entries["time_high_min"].get())
            if self.entries["time_high_max"].get():
                time_high["max"] = float(self.entries["time_high_max"].get())
            if time_high:
                threshold["time_high"] = time_high

            # time_low
            time_low = {}
            if self.entries["time_low_min"].get():
                time_low["min"] = float(self.entries["time_low_min"].get())
            if self.entries["time_low_max"].get():
                time_low["max"] = float(self.entries["time_low_max"].get())
            if time_low:
                threshold["time_low"] = time_low

            # time_mid
            time_mid = {}
            if self.entries["time_mid_min"].get():
                time_mid["min"] = float(self.entries["time_mid_min"].get())
            if self.entries["time_mid_max"].get():
                time_mid["max"] = float(self.entries["time_mid_max"].get())
            if time_mid:
                threshold["time_mid"] = time_mid

        if self.index is not None:
            self.master.data["thresholds"][self.index] = threshold
        else:
            self.master.data["thresholds"].append(threshold)

        save_data(self.master.data)
        self.master.update_threshold_list()
        self.destroy()

# Run the application
if __name__ == "__main__":
    app = ThresholdEditorApp()
    app.mainloop()

