import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import json
import os
import sys
import time
import subprocess
import requests
import hashlib
from PIL import Image
import imagehash
import io
from datetime import datetime

# ── Версия и авто-обновление ──────────────────────────────────────────────────
CURRENT_VERSION = "1.0.0"
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/LimitedQJ/vfx-texture-detector/main/version.json"

# ── Тема ──────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

C = {
    "BG":       "#0a0a0f",
    "SIDEBAR":  "#0f0f18",
    "CARD":     "#13131f",
    "CARD2":    "#1a1a2e",
    "BORDER":   "#1e1e35",
    "ACCENT":   "#4f6ef7",
    "ACCENT2":  "#7c3aed",
    "SUCCESS":  "#10b981",
    "WARNING":  "#f59e0b",
    "DANGER":   "#ef4444",
    "TEXT":     "#e2e8f0",
    "SUBTEXT":  "#64748b",
    "SUBTEXT2": "#94a3b8",
    "HIGHLIGHT":"#1e2a4a",
}

FONT_TITLE  = ("JetBrains Mono", 22, "bold")
FONT_HEADER = ("JetBrains Mono", 13, "bold")
FONT_BODY   = ("JetBrains Mono", 11)
FONT_SMALL  = ("JetBrains Mono", 10)
FONT_MONO   = ("Courier New", 11)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
PENDING_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pending_deletion.json")
INPUT_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input_textures.json")
GITHUB_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vfx_library.json")

# ── Roblox API ─────────────────────────────────────────────────────────────────
ROBLOX_THUMB_URL = "https://thumbnails.roblox.com/v1/assets?assetIds={}&returnPolicy=PlaceHolder&size=420x420&format=Png&isCircular=false"
ROBLOX_ASSET_URL = "https://assetdelivery.roblox.com/v1/asset/?id={}"

# ── GitHub VFX Studio ──────────────────────────────────────────────────────────
GITHUB_RAW = "https://raw.githubusercontent.com/Sytranom/VFXStudio/main/textures.json"


def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_image_phash(asset_id: str) -> str | None:
    """Получить pHash изображения по asset ID через Roblox API."""
    try:
        url = ROBLOX_THUMB_URL.format(asset_id)
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data.get("data"):
            return None
        img_url = data["data"][0].get("imageUrl")
        if not img_url:
            return None
        img_resp = requests.get(img_url, timeout=10)
        if img_resp.status_code != 200:
            return None
        img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
        return str(imagehash.phash(img))
    except Exception:
        return None


def fetch_vfx_library() -> list:
    """Загрузить библиотеку текстур VFX Studio с GitHub."""
    try:
        resp = requests.get(GITHUB_RAW, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            with open(GITHUB_CACHE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return data
    except Exception:
        pass
    # Fallback — кэш
    if os.path.exists(GITHUB_CACHE):
        with open(GITHUB_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_input_textures() -> list:
    """Загрузить текстуры переданные из Roblox Studio плагина."""
    if not os.path.exists(INPUT_FILE):
        return []
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_pending_deletion(ids: list):
    """Сохранить ID дубликатов для удаления плагином."""
    data = {
        "timestamp": datetime.now().isoformat(),
        "ids": ids
    }
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def check_for_update() -> dict | None:
    """Проверяет наличие новой версии на GitHub."""
    try:
        resp = requests.get(GITHUB_VERSION_URL, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            latest = data.get("version", "0.0.0")
            if latest != CURRENT_VERSION:
                return data
    except Exception:
        pass
    return None


def download_and_update(url: str, on_progress=None):
    """Скачивает новый .exe и перезапускает приложение."""
    try:
        resp = requests.get(url, stream=True, timeout=60)
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        exe_path = os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
        tmp_path = exe_path + ".new"

        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if on_progress and total > 0:
                        on_progress(downloaded / total * 100)

        if getattr(sys, "frozen", False):
            bat = exe_path + "_update.bat"
            with open(bat, "w") as f:
                f.write(f'@echo off\ntimeout /t 2 /nobreak\nmove /y "{tmp_path}" "{exe_path}"\nstart "" "{exe_path}"\ndel "%~f0"\n')
            subprocess.Popen(bat, shell=True)
            sys.exit(0)
        else:
            os.replace(tmp_path, exe_path)
            os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        raise e


# ── Анимированная кнопка ───────────────────────────────────────────────────────
class GlowButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, e):
        self.configure(border_width=1, border_color=C["ACCENT"])

    def _on_leave(self, e):
        self.configure(border_width=0)


# ── Карточка статистики ────────────────────────────────────────────────────────
class StatCard(ctk.CTkFrame):
    def __init__(self, master, title, value, icon, color, **kwargs):
        super().__init__(master, fg_color=C["CARD"], corner_radius=14,
                         border_width=1, border_color=C["BORDER"], **kwargs)
        self.configure(width=180, height=90)
        self.pack_propagate(False)
        self.grid_propagate(False)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(14, 4))

        ctk.CTkLabel(top, text=icon, font=("Segoe UI Emoji", 18),
                     text_color=color).pack(side="left")
        ctk.CTkLabel(top, text=title, font=FONT_SMALL,
                     text_color=C["SUBTEXT2"]).pack(side="left", padx=8)

        self.value_label = ctk.CTkLabel(self, text=str(value),
                                         font=("JetBrains Mono", 24, "bold"),
                                         text_color=color)
        self.value_label.pack(anchor="w", padx=14)

    def set_value(self, val):
        self.value_label.configure(text=str(val))


# ── Строка лога ────────────────────────────────────────────────────────────────
class LogLine(ctk.CTkFrame):
    COLORS = {
        "INFO":    C["SUBTEXT2"],
        "SUCCESS": C["SUCCESS"],
        "WARNING": C["WARNING"],
        "ERROR":   C["DANGER"],
        "FOUND":   C["ACCENT"],
    }

    def __init__(self, master, level, message, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        now = datetime.now().strftime("%H:%M:%S")
        color = self.COLORS.get(level, C["TEXT"])

        ctk.CTkLabel(self, text=now, font=FONT_MONO,
                     text_color=C["SUBTEXT"], width=65, anchor="w").pack(side="left")
        ctk.CTkLabel(self, text=f"[{level}]", font=("JetBrains Mono", 10, "bold"),
                     text_color=color, width=75, anchor="w").pack(side="left")
        ctk.CTkLabel(self, text=message, font=FONT_MONO,
                     text_color=C["TEXT"], anchor="w").pack(side="left", fill="x", expand=True)


# ── Строка дубликата ───────────────────────────────────────────────────────────
class DuplicateRow(ctk.CTkFrame):
    def __init__(self, master, idx, group, on_select, **kwargs):
        super().__init__(master, fg_color=C["CARD2"], corner_radius=8,
                         border_width=1, border_color=C["BORDER"], **kwargs)
        self.group = group
        self.selected = False
        self.on_select = on_select

        self.configure(cursor="hand2")
        self.bind("<Button-1>", self._toggle)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)
        inner.bind("<Button-1>", self._toggle)

        # Номер группы
        ctk.CTkLabel(inner, text=f"#{idx:02d}", font=("JetBrains Mono", 12, "bold"),
                     text_color=C["ACCENT"], width=36, anchor="w").pack(side="left")

        # IDs
        ids_text = "  ≡  ".join([f"ID:{g['id']}" for g in group])
        ctk.CTkLabel(inner, text=ids_text, font=FONT_MONO,
                     text_color=C["TEXT"], anchor="w").pack(side="left", padx=8)

        # Авторы
        authors = list(set(g.get("author", "?") for g in group))
        auth_text = ", ".join(authors[:3])
        ctk.CTkLabel(inner, text=f"👤 {auth_text}", font=FONT_SMALL,
                     text_color=C["SUBTEXT2"], anchor="e").pack(side="right", padx=8)

        # Чекбокс
        self.check_var = tk.BooleanVar(value=False)
        self.checkbox = ctk.CTkCheckBox(inner, text="", variable=self.check_var,
                                         width=20, height=20,
                                         fg_color=C["ACCENT"], border_color=C["BORDER"],
                                         command=self._on_check)
        self.checkbox.pack(side="right")

    def _toggle(self, e=None):
        self.check_var.set(not self.check_var.get())
        self._on_check()

    def _on_check(self):
        self.selected = self.check_var.get()
        if self.selected:
            self.configure(fg_color=C["HIGHLIGHT"], border_color=C["ACCENT"])
        else:
            self.configure(fg_color=C["CARD2"], border_color=C["BORDER"])
        self.on_select()


# ── Главное окно ───────────────────────────────────────────────────────────────
class TextureDetectorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("VFX Texture Detector")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(fg_color=C["BG"])
        self.resizable(True, True)

        self._scanning = False
        self._duplicate_groups = []
        self._all_rows = []

        cfg = load_config()
        self._threshold = cfg.get("threshold", 0)

        self._build_ui()
        self._log("INFO", "VFX Texture Detector запущен")
        self._log("INFO", f"Файл ввода: {INPUT_FILE}")
        self._log("INFO", "Ожидание данных от плагина Roblox Studio...")

        # Авто-обновление — проверяем при запуске
        threading.Thread(target=self._check_update_on_start, daemon=True).start()

        # Автоматически проверяем наличие input файла
        self._watch_input()

    # ── Построение UI ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # Основной контейнер
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # ── Сайдбар ───────────────────────────────────────────────────────────
        self._build_sidebar(main)

        # ── Правая часть ──────────────────────────────────────────────────────
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 0))
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # Топбар
        self._build_topbar(right)

        # Контент
        content = ctk.CTkFrame(right, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        content.grid_rowconfigure(1, weight=1)
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)

        # Статистика
        self._build_stats(content)

        # Левая колонка — результаты
        self._build_results(content)

        # Правая колонка — логи
        self._build_logs(content)

    def _build_sidebar(self, parent):
        sidebar = ctk.CTkFrame(parent, fg_color=C["SIDEBAR"], corner_radius=0,
                                border_width=0, width=220)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # Логотип
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=20, pady=(24, 0))

        ctk.CTkLabel(logo_frame, text="⬡", font=("Segoe UI Emoji", 28),
                     text_color=C["ACCENT"]).pack(side="left")
        title_f = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_f.pack(side="left", padx=8)
        ctk.CTkLabel(title_f, text="VFX", font=("JetBrains Mono", 16, "bold"),
                     text_color=C["ACCENT"]).pack(anchor="w")
        ctk.CTkLabel(title_f, text="DETECTOR", font=("JetBrains Mono", 10),
                     text_color=C["SUBTEXT"]).pack(anchor="w")

        ctk.CTkFrame(sidebar, height=1, fg_color=C["BORDER"]).pack(fill="x", padx=16, pady=20)

        # Навигация
        nav_items = [
            ("⊞", "Дашборд",    True),
            ("⊙", "Настройки",  False),
            ("⊏", "История",    False),
        ]
        self._nav_btns = []
        for icon, label, active in nav_items:
            btn = ctk.CTkButton(
                sidebar, text=f"  {icon}   {label}",
                font=FONT_BODY, height=42, corner_radius=10,
                anchor="w", fg_color=C["HIGHLIGHT"] if active else "transparent",
                hover_color=C["BORDER"], text_color=C["TEXT"] if active else C["SUBTEXT2"],
                border_width=1 if active else 0,
                border_color=C["ACCENT"] if active else "transparent"
            )
            btn.pack(fill="x", padx=12, pady=2)
            self._nav_btns.append(btn)

        ctk.CTkFrame(sidebar, fg_color="transparent").pack(fill="both", expand=True)

        # Нижняя часть сайдбара
        ctk.CTkFrame(sidebar, height=1, fg_color=C["BORDER"]).pack(fill="x", padx=16, pady=8)

        # Статус подключения
        status_frame = ctk.CTkFrame(sidebar, fg_color=C["CARD"], corner_radius=10)
        status_frame.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(status_frame, text="ROBLOX STUDIO",
                     font=FONT_SMALL, text_color=C["SUBTEXT"]).pack(pady=(8, 2))
        self._connection_dot = ctk.CTkLabel(status_frame, text="● Ожидание",
                                             font=FONT_SMALL, text_color=C["WARNING"])
        self._connection_dot.pack(pady=(0, 8))

        ctk.CTkLabel(sidebar, text="v" + CURRENT_VERSION, font=FONT_SMALL,
                     text_color=C["SUBTEXT"]).pack(pady=(0, 4))

        self._update_btn = ctk.CTkButton(
            sidebar, text="", font=FONT_SMALL, height=0,
            fg_color="transparent", hover_color="transparent",
            text_color="transparent", command=self._do_update
        )
        self._update_btn.pack(pady=(0, 8))

    def _build_topbar(self, parent):
        topbar = ctk.CTkFrame(parent, fg_color="transparent", height=70)
        topbar.pack(fill="x", padx=20, pady=(16, 0))
        topbar.pack_propagate(False)

        # Заголовок
        title_f = ctk.CTkFrame(topbar, fg_color="transparent")
        title_f.pack(side="left", fill="y")
        ctk.CTkLabel(title_f, text="Детектор дубликатов",
                     font=FONT_TITLE, text_color=C["TEXT"]).pack(anchor="w")
        self._subtitle = ctk.CTkLabel(title_f, text="Готов к сканированию",
                                       font=FONT_SMALL, text_color=C["SUBTEXT2"])
        self._subtitle.pack(anchor="w")

        # Кнопки справа
        btn_frame = ctk.CTkFrame(topbar, fg_color="transparent")
        btn_frame.pack(side="right", fill="y")

        self._scan_btn = GlowButton(
            btn_frame, text="▶  СКАНИРОВАТЬ",
            font=FONT_HEADER, width=160, height=40, corner_radius=10,
            fg_color=C["ACCENT"], hover_color=C["ACCENT2"],
            text_color="white", command=self._start_scan
        )
        self._scan_btn.pack(side="left", padx=(0, 8))

        self._delete_btn = GlowButton(
            btn_frame, text="🗑  УДАЛИТЬ",
            font=FONT_HEADER, width=130, height=40, corner_radius=10,
            fg_color=C["CARD"], hover_color=C["DANGER"],
            text_color=C["SUBTEXT2"], command=self._export_for_deletion,
            state="disabled"
        )
        self._delete_btn.pack(side="left", padx=(0, 8))

        self._clear_btn = GlowButton(
            btn_frame, text="↺  СБРОСИТЬ",
            font=FONT_HEADER, width=130, height=40, corner_radius=10,
            fg_color=C["CARD"], hover_color=C["BORDER"],
            text_color=C["SUBTEXT2"], command=self._clear_results
        )
        self._clear_btn.pack(side="left")

    def _build_stats(self, parent):
        stats_frame = ctk.CTkFrame(parent, fg_color="transparent")
        stats_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        self._stat_total    = StatCard(stats_frame, "ВСЕГО ТЕКСТУР",  "—", "◈", C["ACCENT"])
        self._stat_scanned  = StatCard(stats_frame, "ПРОВЕРЕНО",      "—", "◉", C["SUBTEXT2"])
        self._stat_dupes    = StatCard(stats_frame, "ДУБЛИКАТОВ",     "—", "⊗", C["DANGER"])
        self._stat_selected = StatCard(stats_frame, "ВЫБРАНО",        "0", "◎", C["WARNING"])

        for card in [self._stat_total, self._stat_scanned, self._stat_dupes, self._stat_selected]:
            card.pack(side="left", padx=(0, 10))

    def _build_results(self, parent):
        results_frame = ctk.CTkFrame(parent, fg_color=C["CARD"], corner_radius=14,
                                      border_width=1, border_color=C["BORDER"])
        results_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        results_frame.grid_rowconfigure(1, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)

        # Заголовок
        hdr = ctk.CTkFrame(results_frame, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))

        ctk.CTkLabel(hdr, text="ГРУППЫ ДУБЛИКАТОВ",
                     font=FONT_HEADER, text_color=C["SUBTEXT2"]).pack(side="left")

        self._select_all_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(hdr, text="Все", variable=self._select_all_var,
                         font=FONT_SMALL, fg_color=C["ACCENT"],
                         border_color=C["BORDER"], text_color=C["SUBTEXT2"],
                         command=self._toggle_select_all).pack(side="right")

        ctk.CTkFrame(results_frame, height=1, fg_color=C["BORDER"]).grid(
            row=0, column=0, sticky="ew", padx=0, pady=(46, 0))

        # Список дубликатов
        self._results_scroll = ctk.CTkScrollableFrame(
            results_frame, fg_color="transparent",
            scrollbar_button_color=C["BORDER"],
            scrollbar_button_hover_color=C["ACCENT"]
        )
        self._results_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        self._empty_label = ctk.CTkLabel(
            self._results_scroll,
            text="Нет результатов\nЗапустите сканирование",
            font=FONT_BODY, text_color=C["SUBTEXT"]
        )
        self._empty_label.pack(expand=True, pady=60)

    def _build_logs(self, parent):
        log_frame = ctk.CTkFrame(parent, fg_color=C["CARD"], corner_radius=14,
                                  border_width=1, border_color=C["BORDER"])
        log_frame.grid(row=1, column=1, sticky="nsew")
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(log_frame, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))

        ctk.CTkLabel(hdr, text="КОНСОЛЬ", font=FONT_HEADER,
                     text_color=C["SUBTEXT2"]).pack(side="left")

        ctk.CTkButton(hdr, text="Очистить", font=FONT_SMALL, width=70, height=24,
                       corner_radius=6, fg_color=C["BORDER"], hover_color=C["CARD2"],
                       text_color=C["SUBTEXT2"], command=self._clear_logs).pack(side="right")

        ctk.CTkFrame(log_frame, height=1, fg_color=C["BORDER"]).grid(
            row=0, column=0, sticky="ew", padx=0, pady=(46, 0))

        self._log_scroll = ctk.CTkScrollableFrame(
            log_frame, fg_color="transparent",
            scrollbar_button_color=C["BORDER"],
            scrollbar_button_hover_color=C["ACCENT"]
        )
        self._log_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

    # ── Логика ─────────────────────────────────────────────────────────────────
    def _log(self, level: str, message: str):
        """Добавить строку в консоль."""
        def _do():
            line = LogLine(self._log_scroll, level, message)
            line.pack(fill="x", pady=1)
            # Авто-скролл вниз
            self._log_scroll._parent_canvas.yview_moveto(1.0)
        self.after(0, _do)

    def _clear_logs(self):
        for w in self._log_scroll.winfo_children():
            w.destroy()

    def _clear_results(self):
        for w in self._results_scroll.winfo_children():
            w.destroy()
        self._empty_label = ctk.CTkLabel(
            self._results_scroll,
            text="Нет результатов\nЗапустите сканирование",
            font=FONT_BODY, text_color=C["SUBTEXT"]
        )
        self._empty_label.pack(expand=True, pady=60)
        self._duplicate_groups = []
        self._all_rows = []
        self._stat_total.set_value("—")
        self._stat_scanned.set_value("—")
        self._stat_dupes.set_value("—")
        self._stat_selected.set_value("0")
        self._delete_btn.configure(state="disabled", text_color=C["SUBTEXT2"])
        self._subtitle.configure(text="Готов к сканированию")

    def _check_update_on_start(self):
        """Проверяет обновления при запуске в фоновом потоке."""
        self._update_data = check_for_update()
        if self._update_data:
            version = self._update_data.get("version", "?")
            changelog = self._update_data.get("changelog", "")
            self.after(0, self._show_update_notification, version, changelog)

    def _show_update_notification(self, version: str, changelog: str):
        """Показывает кнопку обновления в сайдбаре."""
        self._log("WARNING", f"Доступна новая версия: v{version}!")
        self._update_btn.configure(
            text=f"⬆  Обновить до v{version}",
            height=32, corner_radius=8,
            fg_color=C["WARNING"], hover_color=C["ACCENT"],
            text_color="#000000"
        )

    def _do_update(self):
        """Запускает загрузку и установку обновления."""
        if not hasattr(self, "_update_data") or not self._update_data:
            return
        url = self._update_data.get("download_url", "")
        version = self._update_data.get("version", "?")
        if not url:
            messagebox.showerror("Ошибка", "Ссылка на обновление недоступна.")
            return

        if not messagebox.askyesno("Обновление",
            f"Доступна версия v{version}.\n\nСкачать и установить?\nПриложение перезапустится."):
            return

        self._update_btn.configure(text="⏳ Скачивание...", state="disabled")
        self._log("INFO", f"Скачиваю обновление v{version}...")

        def run():
            try:
                def on_progress(pct):
                    self.after(0, self._update_btn.configure,
                               {"text": f"⏳ {pct:.0f}%"})
                download_and_update(url, on_progress)
            except Exception as e:
                self.after(0, messagebox.showerror, "Ошибка обновления", str(e))
                self.after(0, self._update_btn.configure, {"state": "normal"})

        threading.Thread(target=run, daemon=True).start()

    def _watch_input(self):
        """Проверяет наличие нового input файла от плагина."""
        def check():
            while True:
                if os.path.exists(INPUT_FILE):
                    mtime = os.path.getmtime(INPUT_FILE)
                    if not hasattr(self, "_last_mtime") or mtime != self._last_mtime:
                        self._last_mtime = mtime
                        self.after(0, self._on_new_input)
                        self._connection_dot.configure(text="● Подключён", text_color=C["SUCCESS"])
                time.sleep(2)
        threading.Thread(target=check, daemon=True).start()

    def _on_new_input(self):
        textures = load_input_textures()
        if textures:
            self._log("SUCCESS", f"Получено {len(textures)} текстур от плагина")
            self._subtitle.configure(text=f"Загружено {len(textures)} текстур из Studio")
            self._stat_total.set_value(len(textures))

    def _start_scan(self):
        if self._scanning:
            return
        textures = load_input_textures()
        if not textures:
            self._log("ERROR", "Нет данных! Сначала экспортируйте текстуры из Roblox Studio")
            messagebox.showwarning("Нет данных",
                "Нет текстур для сканирования.\n\nИспользуйте плагин в Roblox Studio\nчтобы экспортировать текстуры.")
            return

        self._scanning = True
        self._scan_btn.configure(text="⏳ СКАНИРОВАНИЕ...", state="disabled",
                                  fg_color=C["CARD2"])
        self._clear_results()
        threading.Thread(target=self._scan_worker, args=(textures,), daemon=True).start()

    def _scan_worker(self, textures: list):
        self._log("INFO", f"Начало сканирования {len(textures)} текстур...")
        self._log("INFO", "Загрузка библиотеки VFX Studio с GitHub...")

        # 1. Загружаем библиотеку VFX Studio
        vfx_lib = fetch_vfx_library()
        if vfx_lib:
            self._log("SUCCESS", f"Библиотека VFX Studio: {len(vfx_lib)} текстур")
        else:
            self._log("WARNING", "Библиотека VFX Studio недоступна, работаем только с входными данными")

        # 2. Объединяем все текстуры
        all_textures = list(textures)
        for t in vfx_lib:
            all_textures.append({
                "id": t.get("id", ""),
                "grid": t.get("grid", ""),
                "type": t.get("type", ""),
                "author": t.get("author", "VFX Studio"),
                "source": "vfx_library"
            })

        total = len(all_textures)
        self._log("INFO", f"Всего текстур для анализа: {total}")
        self.after(0, self._stat_total.set_value, total)

        # 3. Вычисляем pHash для каждой текстуры
        hashes = {}
        for i, tex in enumerate(all_textures):
            asset_id = str(tex.get("id", "")).strip()
            if not asset_id:
                continue

            self._log("INFO", f"[{i+1}/{total}] Получаю хэш для ID: {asset_id}")
            phash = get_image_phash(asset_id)

            if phash:
                hashes[asset_id] = {
                    "hash": phash,
                    "meta": tex
                }
                self.after(0, self._stat_scanned.set_value, len(hashes))
            else:
                self._log("WARNING", f"Не удалось получить изображение для ID: {asset_id}")

        # 4. Поиск дубликатов (0 бит разницы = точная копия)
        self._log("INFO", "Анализ дубликатов...")
        duplicates = []
        processed = set()
        ids = list(hashes.keys())

        for i in range(len(ids)):
            if ids[i] in processed:
                continue
            group = [hashes[ids[i]]["meta"]]
            for j in range(i + 1, len(ids)):
                if ids[j] in processed:
                    continue
                h1 = imagehash.hex_to_hash(hashes[ids[i]]["hash"])
                h2 = imagehash.hex_to_hash(hashes[ids[j]]["hash"])
                diff = h1 - h2
                if diff == 0:  # Точная копия
                    group.append(hashes[ids[j]]["meta"])
                    processed.add(ids[j])
            if len(group) > 1:
                duplicates.append(group)
                processed.add(ids[i])
                self._log("FOUND", f"Дубликат: {' = '.join([str(g['id']) for g in group])}")

        # 5. Результаты
        self._duplicate_groups = duplicates
        self.after(0, self._show_results, duplicates, len(hashes))

    def _show_results(self, duplicates: list, scanned: int):
        self._scanning = False
        self._scan_btn.configure(text="▶  СКАНИРОВАТЬ", state="normal",
                                  fg_color=C["ACCENT"])
        self._stat_scanned.set_value(scanned)
        self._stat_dupes.set_value(len(duplicates))

        # Очищаем пустую метку
        for w in self._results_scroll.winfo_children():
            w.destroy()
        self._all_rows = []

        if not duplicates:
            self._log("SUCCESS", "Дубликатов не найдено!")
            ctk.CTkLabel(self._results_scroll,
                         text="✓ Дубликатов не найдено",
                         font=FONT_BODY, text_color=C["SUCCESS"]).pack(pady=60)
            self._subtitle.configure(text=f"Сканирование завершено — дубликатов нет")
            return

        self._log("SUCCESS", f"Найдено {len(duplicates)} групп дубликатов")
        self._subtitle.configure(text=f"Найдено {len(duplicates)} групп дубликатов")
        self._delete_btn.configure(state="normal", text_color=C["DANGER"])

        for i, group in enumerate(duplicates, 1):
            row = DuplicateRow(self._results_scroll, i, group,
                               on_select=self._update_selected_count)
            row.pack(fill="x", pady=3)
            self._all_rows.append(row)

    def _update_selected_count(self):
        count = sum(1 for r in self._all_rows if r.selected)
        self._stat_selected.set_value(count)

    def _toggle_select_all(self):
        val = self._select_all_var.get()
        for row in self._all_rows:
            row.check_var.set(val)
            row.selected = val
            if val:
                row.configure(fg_color=C["HIGHLIGHT"], border_color=C["ACCENT"])
            else:
                row.configure(fg_color=C["CARD2"], border_color=C["BORDER"])
        self._update_selected_count()

    def _export_for_deletion(self):
        selected_groups = [r.group for r in self._all_rows if r.selected]
        if not selected_groups:
            messagebox.showwarning("Не выбрано", "Выберите хотя бы одну группу дубликатов.")
            return

        # Собираем все ID дубликатов (оставляем первый в группе — оригинал)
        ids_to_delete = []
        for group in selected_groups:
            for tex in group[1:]:  # Первый оставляем, остальные удаляем
                ids_to_delete.append(str(tex.get("id", "")))

        save_pending_deletion(ids_to_delete)

        self._log("SUCCESS", f"Сохранено {len(ids_to_delete)} ID для удаления")
        self._log("INFO", f"Файл: {PENDING_FILE}")
        self._log("INFO", "Теперь нажмите 'Применить удаление' в плагине Roblox Studio")

        messagebox.showinfo(
            "Готово!",
            f"Сохранено {len(ids_to_delete)} текстур для удаления.\n\n"
            f"Теперь в Roblox Studio нажмите\n'Применить удаление' в плагине VFX Detector.\n\n"
            f"Текстуры будут перемещены в\nReplicatedStorage/PendingDeletion"
        )


if __name__ == "__main__":
    app = TextureDetectorApp()
    app.mainloop()
