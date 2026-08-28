import base64
import os
from pathlib import Path
import shutil
import stat
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from Crypto.Cipher import AES
except ImportError:
    from Cryptodome.Cipher import AES

AES_KEY = b"UVbP6pjjw5KZhvddie3tfhg1pVkkveY8"
SPLIT_TOKEN = "|SPLIT|"
PRESET_CONFIGS = {
    "cpu": (
        "[ConsoleVariables]\n"
        "FX.BatchAsync=1\n"
        "FX.EarlyScheduleAsync=1\n"
        "tick.AllowAsyncTickCleanup=1\n"
        "tick.AllowAsyncTickDispatch=1\n\n"
    ),
    "hdr": (
        "[/Script/Engine.RendererSettings]\n"
        "r.HDR.EnableHDROutput=1\n"
        "r.HDR.Display.OutputDevice=5\n"
        "r.HDR.Display.ColorGamut=2\n"
        "r.HDR.UI.Level=2\n"
        "r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange=True\n"
        "r.EyeAdaptationQuality=2\n"
        "r.HDR.Display.MaxLuminance=1000\n"
        "r.HDR.Display.MidLuminance=100\n\n"
    ),
    "lumen_rt": (
        "[SystemSettings]\n"
        "UI.ShowLumenSettings=1\n"
        "UI.ShowRayTracingSettings=1\n"
        "UI.ShowFullRayTracingSettings=1\n\n"
    ),
}

def get_resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def center_window(window: tk.Tk | tk.Toplevel, width: int, height: int):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


def decrypt_ini_content(data: bytes) -> tuple[str, bool]:
    text_check = data[:100].decode("utf-8-sig", errors="ignore")
    if text_check.startswith(";METADATA=(Diff=true, UseCommands=true)"):
        return data.decode("utf-8-sig", errors="replace"), True

    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    text = data.decode("utf-8-sig").strip()
    if not text:
        return "", False

    result_lines = []
    for line in text.split("\n"):
        line = line.strip("\r\n\t ")
        if not line:
            continue
        try:
            enc = base64.b64decode(line)
        except Exception:
            result_lines.append(line)
            continue
        if len(enc) == 0 or len(enc) % 16 != 0:
            result_lines.append(line)
            continue
        dec = cipher.decrypt(enc)
        pad_len = dec[-1]
        if 1 <= pad_len <= 16 and all(b == pad_len for b in dec[-pad_len:]):
            dec = dec[:-pad_len]
        plain = dec.decode("utf-8", errors="replace")
        for part in plain.split(SPLIT_TOKEN):
            if part:
                result_lines.append(part)

    return "\n".join(result_lines) + "\n", False


def update_ini_key_values(content: str, updates: dict, default_section="[/Script/Engine.GameUserSettings]") -> str:
    lines = content.splitlines()
    found_keys = set()
    new_lines = []

    for line in lines:
        line_stripped = line.strip()
        replaced = False
        for key, val in updates.items():
            if line_stripped.startswith(f"{key}=") or line_stripped.startswith(f"{key} ="):
                new_lines.append(f"{key}={val}")
                found_keys.add(key)
                replaced = True
                break
        if not replaced:
            new_lines.append(line)

    missing_keys = set(updates.keys()) - found_keys
    if missing_keys:
        sec_idx = -1
        for idx, line in enumerate(new_lines):
            if line.strip() == default_section:
                sec_idx = idx
                break

        if sec_idx != -1:
            insert_lines = [f"{k}={updates[k]}" for k in sorted(missing_keys)]
            new_lines[sec_idx + 1:sec_idx + 1] = insert_lines
        else:
            new_lines.append(f"\n{default_section}")
            for k in sorted(missing_keys):
                new_lines.append(f"{k}={updates[k]}")

    return "\n".join(new_lines) + "\n"


def find_target_directory() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return None

    base_local = Path(local_app_data)
    sub_paths = [
        Path("HT") / "Saved" / "Config" / "Windows",
        Path("HT") / "Saved_GlobalSteam" / "Config" / "Windows",
        Path("HT") / "Saved_GlobalEpic" / "Config" / "Windows",
        Path("HT") / "Saved_Global" / "Config" / "Windows",
    ]

    for sub in sub_paths:
        target_dir = base_local / sub
        if target_dir.exists() and (target_dir / "Engine.ini").is_file():
            return target_dir

    return None


def make_file_writable(path: Path):
    if path.exists():
        os.chmod(path, stat.S_IWRITE)


def make_file_readonly(path: Path):
    if path.exists():
        os.chmod(path, stat.S_IREAD)


class INIModifierApp:

    def __init__(self, root, config_dir: Path):
        self.root = root
        self.root.title("NTE 畫面隱藏設定小工具")

        try:
            self.root.iconbitmap(get_resource_path("icon.ico"))
        except Exception:
            pass
        center_window(self.root, 450, 260)
        self.root.resizable(False, False)

        self.config_dir = config_dir
        self.game_ini_path = config_dir / "GameUserSettings.ini"
        self.engine_ini_path = config_dir / "Engine.ini"

        self.decrypted_game_ini = ""
        self.decrypted_engine_ini = ""

        self.init_files()
        self.setup_ui()

    def init_files(self):
        already_decrypted_flag = False

        if self.game_ini_path.exists():
            data = self.game_ini_path.read_bytes()
            content, is_dec = decrypt_ini_content(data)
            self.decrypted_game_ini = content
            if is_dec:
                already_decrypted_flag = True

        if self.engine_ini_path.exists():
            data = self.engine_ini_path.read_bytes()
            content, is_dec = decrypt_ini_content(data)
            self.decrypted_engine_ini = content
            if is_dec:
                already_decrypted_flag = True

        if already_decrypted_flag:
            messagebox.showinfo(
                "解密提醒", "似乎你的 ini 檔案已經解密，已跳過解密過程。"
            )

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main_frame,
            text="請選擇要執行的操作：",
            font=("Microsoft JhengHei", 10, "bold"),
        ).pack(anchor=tk.W, pady=(0, 15))

        btn_hidden = ttk.Button(
            main_frame,
            text="加入隱藏的畫面設定",
            command=self.open_hidden_settings_menu,
        )
        btn_hidden.pack(fill=tk.X, pady=5)

        btn_export = ttk.Button(
            main_frame,
            text="匯出解密後的設定檔",
            command=self.export_decrypted_files,
        )
        btn_export.pack(fill=tk.X, pady=5)

        btn_restore = ttk.Button(
            main_frame, text="還原設定", command=self.restore_settings
        )
        btn_restore.pack(fill=tk.X, pady=5)

        path_str = str(self.config_dir)
        display_path = (
            path_str if len(path_str) < 50 else "..." + path_str[-47:]
        )
        ttk.Label(
            main_frame,
            text=f"當前目錄: {display_path}",
            foreground="gray",
            font=("Microsoft JhengHei", 8),
        ).pack(anchor=tk.W, pady=(15, 0))

    def export_decrypted_files(self):
        target_dir = filedialog.askdirectory(title="選擇匯出解密設定檔的位置")
        if not target_dir:
            return

        target_path = Path(target_dir)
        try:
            (target_path / "GameUserSettings.ini").write_text(
                self.decrypted_game_ini, encoding="utf-8"
            )
            (target_path / "Engine.ini").write_text(
                self.decrypted_engine_ini, encoding="utf-8"
            )
            messagebox.showinfo(
                "匯出成功",
                f"解密後的設定檔已成功儲存至：\n{target_dir}",
            )
        except Exception as e:
            messagebox.showerror("匯出失敗", f"儲存設定檔時發生錯誤：\n{e}")

    def restore_settings(self):
        restored_files = []
        possible_backups = [
            ("GameUserSettings.ini", ["GameUserSettings.ini.bak", "GameUserSettings.bak"]),
            ("Engine.ini", ["Engine.ini.bak", "Engine.bak"]),
        ]

        for target_name, bak_names in possible_backups:
            target_file = self.config_dir / target_name
            for bak_name in bak_names:
                bak_file = self.config_dir / bak_name
                if bak_file.exists():
                    try:
                        make_file_writable(target_file)
                        shutil.copy2(bak_file, target_file)
                        restored_files.append(f"{target_name} <- {bak_name}")
                        break
                    except Exception as e:
                        messagebox.showerror(
                            "還原失敗", f"還原 {target_name} 時發生錯誤：\n{e}"
                        )

        if restored_files:
            messagebox.showinfo(
                "還原完成",
                "已成功還原以下設定檔：\n" + "\n".join(restored_files),
            )
            self.init_files()
        else:
            messagebox.showwarning(
                "未找到備份",
                "未在目標目錄下找到相應的 .bak 備份檔案！",
            )

    def open_hidden_settings_menu(self):
        sub_window = tk.Toplevel(self.root)
        sub_window.withdraw()
        sub_window.title("加入隱藏的畫面設定")
        try:
            sub_window.iconbitmap(get_resource_path("icon.ico"))
        except Exception:
            pass
        center_window(sub_window, 400, 280)
        sub_window.resizable(False, False)
        sub_window.grab_set()

        frame = ttk.Frame(sub_window, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        var_hdr = tk.BooleanVar(value=False)
        var_lumen = tk.BooleanVar(value=False)
        var_cpu = tk.BooleanVar(value=False)
        var_fps = tk.BooleanVar(value=False)

        ttk.Checkbutton(
            frame,
            text="HDR設定 *無遊戲內選單預設開啟",
            variable=var_hdr,
        ).pack(anchor=tk.W, pady=6)

        ttk.Checkbutton(
            frame, text="開啟Lumen和RayTracing", variable=var_lumen
        ).pack(anchor=tk.W, pady=6)

        ttk.Checkbutton(
            frame, text="CPU非同步計算最佳化", variable=var_cpu
        ).pack(anchor=tk.W, pady=6)

        ttk.Checkbutton(
            frame,
            text="解鎖fps上限 *設定內顯示30是正常的",
            variable=var_fps,
        ).pack(anchor=tk.W, pady=6)

        def apply_changes():
            if not (var_hdr.get() or var_lumen.get() or var_cpu.get() or var_fps.get()):
                messagebox.showwarning(
                    "提示", "請至少勾選一個修改項！", parent=sub_window
                )
                return

            base_engine_text = self.decrypted_engine_ini

            sections_to_check = [
                "[ConsoleVariables]",
                "[/Script/Engine.RendererSettings]",
                "[SystemSettings]",
            ]
            if (var_hdr.get() or var_lumen.get() or var_cpu.get()) and any(
                sec in base_engine_text for sec in sections_to_check
            ):
                confirm = messagebox.askokcancel(
                    "設定衝突警告",
                    "似乎你解密並修改過 engine.ini，新的設定可能會衝突；\n"
                    "如果使用本工具修改過，請到主選單還原設定後再繼續。\n\n"
                    "是否繼續變更？",
                    parent=sub_window,
                )
                if not confirm:
                    return

            try:
                modified_summary = []
                game_updates = {}
                if var_hdr.get():
                    game_updates["bUseHDRDisplayOutput"] = "True"
                    game_updates["HDRDisplayOutputNits"] = "1000"
                if var_fps.get():
                    game_updates["FrameRateLimit"] = "999.000000"

                if game_updates:
                    game_bak = self.config_dir / "GameUserSettings.ini.bak"
                    if self.game_ini_path.exists() and not game_bak.exists():
                        shutil.copy2(self.game_ini_path, game_bak)

                    new_game_content = update_ini_key_values(
                        self.decrypted_game_ini, game_updates
                    )

                    make_file_writable(self.game_ini_path)
                    self.game_ini_path.write_text(new_game_content, encoding="utf-8")

                    self.decrypted_game_ini = new_game_content
                    modified_summary.append("GameUserSettings.ini")
                if var_hdr.get() or var_lumen.get() or var_cpu.get():
                    engine_bak = self.config_dir / "Engine.ini.bak"
                    if self.engine_ini_path.exists() and not engine_bak.exists():
                        shutil.copy2(self.engine_ini_path, engine_bak)

                    append_text = "\n"
                    if var_hdr.get():
                        append_text += PRESET_CONFIGS["hdr"]
                    if var_lumen.get():
                        append_text += PRESET_CONFIGS["lumen_rt"]
                    if var_cpu.get():
                        append_text += PRESET_CONFIGS["cpu"]

                    new_engine_content = base_engine_text.rstrip() + "\n" + append_text

                    make_file_writable(self.engine_ini_path)
                    self.engine_ini_path.write_text(new_engine_content, encoding="utf-8")
                    make_file_readonly(self.engine_ini_path)

                    self.decrypted_engine_ini = new_engine_content
                    modified_summary.append("Engine.ini(已鎖定唯讀)")

                summary_str = " & ".join(modified_summary)
                messagebox.showinfo(
                    "成功",
                    f"設定已成功儲存至解密後的設定檔！\n\n已修改: {summary_str}",
                    parent=sub_window,
                )
                sub_window.destroy()

            except Exception as e:
                messagebox.showerror(
                    "儲存失敗", f"寫入設定檔時發生錯誤：\n{e}", parent=sub_window
                )

        btn_confirm = ttk.Button(
            frame, text="套用修改", command=apply_changes
        )
        btn_confirm.pack(fill=tk.X, pady=(15, 0))
        sub_window.deiconify()
def main():
    root = tk.Tk()
    root.withdraw()

    target_dir = find_target_directory()

    if not target_dir:
        messagebox.showerror(
            "找不到目錄",
            "未能在 AppData\\Local\\HT 下找到存放 Windows 設定檔的路徑！\n"
            "請確認遊戲是否已執行並生成了相關設定檔。",
        )
        sys.exit(0)

    app = INIModifierApp(root, target_dir)
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()