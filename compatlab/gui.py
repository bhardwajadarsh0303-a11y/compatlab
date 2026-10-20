"""Modern Tkinter GUI for CompatLab."""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from compatlab import __version__
from compatlab.challenges import CHALLENGES
from compatlab.models import Report, Status, TestResult, Tier
from compatlab.report import from_json, to_html, to_json, to_text_summary
from compatlab.runner import collect_host_info, run_all
from compatlab.tests_catalog import TESTS

# Color palette
PALETTE = {
    "bg": "#F5F7FA",
    "surface": "#FFFFFF",
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "success": "#16A34A",
    "warning": "#D97706",
    "error": "#DC2626",
    "text": "#0F172A",
    "muted": "#64748B",
    "border": "#E2E8F0",
    "card_bg": "#FFFFFF",
    "highlight_col": "#EFF6FF",
}


def get_system_font(size: int = 10, bold: bool = False) -> tuple[str, int, str]:
    """Pick platform-native font family."""
    if sys.platform == "win32":
        family = "Segoe UI"
    elif sys.platform == "darwin":
        family = "Helvetica Neue"
    else:
        family = "DejaVu Sans"
    weight = "bold" if bold else "normal"
    return (family, size, weight)


class CompatLabApp:
    """Main CompatLab desktop interface."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CompatLab")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)
        self.root.configure(bg=PALETTE["bg"])

        self.center_window(1100, 720)
        self.host_info = collect_host_info()
        self.current_report: Report | None = None
        self.loaded_reports: list[Report] = []
        self.test_queue: queue.Queue[Any] = queue.Queue()
        self.is_running = False

        self.setup_styles()
        self.build_ui()
        self.bind_events()
        self.load_user_notes()
        self.update_status("Ready. Click 'Run All Tests' or press Ctrl+R to begin.")

    def center_window(self, width: int, height: int) -> None:
        """Center the application window on screen."""
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def setup_styles(self) -> None:
        """Configure ttk styles with clam theme."""
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        base_font = get_system_font(10)
        bold_font = get_system_font(10, bold=True)
        head_font = get_system_font(16, bold=True)

        self.style.configure(".", font=base_font, background=PALETTE["bg"], foreground=PALETTE["text"])
        self.style.configure("TFrame", background=PALETTE["bg"])
        self.style.configure("Card.TFrame", background=PALETTE["surface"], relief="flat")
        self.style.configure("TNotebook", background=PALETTE["bg"], tabmargins=[2, 5, 2, 0])
        self.style.configure(
            "TNotebook.Tab",
            font=bold_font,
            padding=[16, 8],
            background="#E2E8F0",
            foreground=PALETTE["muted"],
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", PALETTE["surface"])],
            foreground=[("selected", PALETTE["primary"])],
        )

        # Buttons
        self.style.configure(
            "Primary.TButton",
            font=bold_font,
            background=PALETTE["primary"],
            foreground="white",
            padding=[14, 6],
            relief="flat",
            borderwidth=0,
        )
        self.style.map(
            "Primary.TButton",
            background=[("active", PALETTE["primary_hover"]), ("disabled", "#93C5FD")],
            foreground=[("disabled", "#E0E7FF")],
        )

        self.style.configure(
            "Secondary.TButton",
            font=base_font,
            background=PALETTE["surface"],
            foreground=PALETTE["text"],
            padding=[10, 5],
            relief="flat",
            borderwidth=1,
        )
        self.style.map(
            "Secondary.TButton",
            background=[("active", "#E2E8F0")],
        )

        # Treeview styling
        self.style.configure(
            "Treeview",
            rowheight=28,
            font=base_font,
            background=PALETTE["surface"],
            fieldbackground=PALETTE["surface"],
            foreground=PALETTE["text"],
            borderwidth=1,
        )
        self.style.configure(
            "Treeview.Heading",
            font=bold_font,
            background="#F8FAFC",
            foreground=PALETTE["muted"],
            relief="flat",
        )
        self.style.map("Treeview.Heading", background=[("active", "#E2E8F0")])

        # Progress bar
        self.style.configure(
            "Horizontal.TProgressbar",
            troughcolor="#E2E8F0",
            background=PALETTE["primary"],
            relief="flat",
            thickness=6,
        )

    def build_ui(self) -> None:
        """Construct full application layout."""
        # Top Header Bar
        header = tk.Frame(self.root, bg=PALETTE["surface"], height=64, padx=20, pady=12)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        left_header = tk.Frame(header, bg=PALETTE["surface"])
        left_header.pack(side=tk.LEFT, fill=tk.Y)

        title_lbl = tk.Label(
            left_header,
            text="CompatLab",
            font=get_system_font(16, bold=True),
            bg=PALETTE["surface"],
            fg=PALETTE["primary"],
        )
        title_lbl.pack(side=tk.LEFT, padx=(0, 10))

        tagline_lbl = tk.Label(
            left_header,
            text="Same code. Different operating systems.",
            font=get_system_font(10),
            bg=PALETTE["surface"],
            fg=PALETTE["muted"],
        )
        tagline_lbl.pack(side=tk.LEFT, pady=3)

        # Host badge on right
        host_badge_text = f"Running on: {self.host_info.os_name} {self.host_info.os_release} | Python {self.host_info.python_version}"
        host_badge = tk.Label(
            header,
            text=host_badge_text,
            font=get_system_font(9, bold=True),
            bg="#EFF6FF",
            fg=PALETTE["primary"],
            padx=10,
            pady=4,
            relief="solid",
            bd=1,
        )
        host_badge.pack(side=tk.RIGHT, pady=4)

        # Main Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=(12, 4))

        # Build individual tabs
        self.build_run_tab()
        self.build_compare_tab()
        self.build_challenges_tab()
        self.build_about_tab()

        # Status Bar at bottom
        self.status_bar = tk.Frame(self.root, bg=PALETTE["surface"], height=28, padx=16, pady=4)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_bar.pack_propagate(False)

        self.status_lbl = tk.Label(
            self.status_bar,
            text="Ready",
            font=get_system_font(9),
            bg=PALETTE["surface"],
            fg=PALETTE["muted"],
        )
        self.status_lbl.pack(side=tk.LEFT)

        self.time_lbl = tk.Label(
            self.status_bar,
            text="",
            font=get_system_font(9),
            bg=PALETTE["surface"],
            fg=PALETTE["muted"],
        )
        self.time_lbl.pack(side=tk.RIGHT)

    def build_run_tab(self) -> None:
        """Tab 1: Run Tests tab."""
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text=" Run Tests ")

        # Toolbar
        toolbar = tk.Frame(tab, bg=PALETTE["bg"])
        toolbar.pack(fill=tk.X, pady=(0, 12))

        self.btn_run = ttk.Button(
            toolbar,
            text="Run All Tests (Ctrl+R)",
            style="Primary.TButton",
            command=self.start_test_run,
        )
        self.btn_run.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_export_json = ttk.Button(
            toolbar,
            text="Export JSON",
            style="Secondary.TButton",
            command=self.export_json_action,
        )
        self.btn_export_json.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_export_html = ttk.Button(
            toolbar,
            text="Export HTML",
            style="Secondary.TButton",
            command=self.export_html_action,
        )
        self.btn_export_html.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_copy_summary = ttk.Button(
            toolbar,
            text="Copy Summary",
            style="Secondary.TButton",
            command=self.copy_summary_action,
        )
        self.btn_copy_summary.pack(side=tk.LEFT, padx=(0, 16))

        # Filter combobox
        lbl_filter = tk.Label(toolbar, text="Filter:", font=get_system_font(10), bg=PALETTE["bg"], fg=PALETTE["muted"])
        lbl_filter.pack(side=tk.LEFT, padx=(0, 6))

        self.category_var = tk.StringVar(value="All")
        categories = ["All", "Paths", "Files", "Permissions", "Links", "Text", "Environment"]
        self.cb_filter = ttk.Combobox(toolbar, textvariable=self.category_var, values=categories, state="readonly", width=14)
        self.cb_filter.pack(side=tk.LEFT)
        self.cb_filter.bind("<<ComboboxSelected>>", lambda e: self.filter_treeview())

        # Progress indicator (right-aligned)
        self.progress_lbl = tk.Label(toolbar, text="", font=get_system_font(9), bg=PALETTE["bg"], fg=PALETTE["muted"])
        self.progress_lbl.pack(side=tk.RIGHT, padx=(8, 0))

        self.progress_bar = ttk.Progressbar(toolbar, style="Horizontal.TProgressbar", length=140, mode="determinate")
        self.progress_bar.pack(side=tk.RIGHT)

        # 4 Summary Cards
        cards_frame = tk.Frame(tab, bg=PALETTE["bg"])
        cards_frame.pack(fill=tk.X, pady=(0, 12))

        self.card_total = self.create_card(cards_frame, "TOTAL TESTS", "-", PALETTE["text"])
        self.card_differs = self.create_card(cards_frame, "OSES DIFFER", "-", PALETTE["warning"])
        self.card_confirmed = self.create_card(cards_frame, "CONFIRMED ON HOST", "-", PALETTE["success"])
        self.card_errors = self.create_card(cards_frame, "ERRORS", "-", PALETTE["error"])

        # Main PanedWindow for Table + Detail
        paned = tk.PanedWindow(tab, orient=tk.VERTICAL, bg=PALETTE["border"], sashwidth=4, bd=0)
        paned.pack(fill=tk.BOTH, expand=True)

        # Treeview frame
        tree_frame = tk.Frame(paned, bg=PALETTE["surface"], bd=1, relief="solid")
        paned.add(tree_frame, height=260)

        cols = ("id", "name", "category", "status", "host_value", "duration")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Test")
        self.tree.heading("category", text="Category")
        self.tree.heading("status", text="Status")
        self.tree.heading("host_value", text="This Machine (Host Value)")
        self.tree.heading("duration", text="Duration")

        self.tree.column("id", width=60, minwidth=50, stretch=False, anchor=tk.CENTER)
        self.tree.column("name", width=180, minwidth=140)
        self.tree.column("category", width=100, minwidth=90)
        self.tree.column("status", width=90, minwidth=80, anchor=tk.CENTER)
        self.tree.column("host_value", width=420, minwidth=250)
        self.tree.column("duration", width=80, minwidth=70, anchor=tk.E)

        # Scrollbar for tree
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure("even", background="#FFFFFF")
        self.tree.tag_configure("odd", background="#F8FAFC")
        self.tree.tag_configure("status_differs", foreground="#B45309")
        self.tree.tag_configure("status_same", foreground="#15803D")
        self.tree.tag_configure("status_error", foreground="#B91C1C")

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Detail Panel
        detail_frame = tk.Frame(paned, bg=PALETTE["surface"], bd=1, relief="solid", padx=16, pady=12)
        paned.add(detail_frame)

        self.lbl_detail_title = tk.Label(
            detail_frame,
            text="Select a test above to inspect details and cross-OS comparison.",
            font=get_system_font(12, bold=True),
            bg=PALETTE["surface"],
            fg=PALETTE["text"],
            anchor=tk.W,
        )
        self.lbl_detail_title.pack(fill=tk.X, pady=(0, 6))

        self.lbl_detail_explanation = tk.Label(
            detail_frame,
            text="",
            font=get_system_font(10),
            bg=PALETTE["surface"],
            fg=PALETTE["text"],
            justify=tk.LEFT,
            wraplength=980,
            anchor=tk.W,
        )
        self.lbl_detail_explanation.pack(fill=tk.X, pady=(0, 6))

        self.lbl_detail_pitfall = tk.Label(
            detail_frame,
            text="",
            font=get_system_font(9, bold=True),
            bg="#FEF3C7",
            fg="#92400E",
            padx=8,
            pady=4,
            anchor=tk.W,
            justify=tk.LEFT,
        )

        # OS Cells strip inside detail panel
        self.detail_cells_frame = tk.Frame(detail_frame, bg=PALETTE["surface"])
        self.detail_cells_frame.pack(fill=tk.X, pady=(8, 0))

    def create_card(self, parent: tk.Widget, label: str, value: str, text_color: str) -> tk.Label:
        """Helper to create summary metric card."""
        card = tk.Frame(parent, bg=PALETTE["surface"], bd=1, relief="solid", padx=16, pady=10)
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        lbl = tk.Label(
            card,
            text=label,
            font=get_system_font(8, bold=True),
            bg=PALETTE["surface"],
            fg=PALETTE["muted"],
        )
        lbl.pack(anchor=tk.W)

        val_lbl = tk.Label(
            card,
            text=value,
            font=get_system_font(20, bold=True),
            bg=PALETTE["surface"],
            fg=text_color,
        )
        val_lbl.pack(anchor=tk.W, pady=(2, 0))
        return val_lbl

    def build_compare_tab(self) -> None:
        """Tab 2: Compare matrix tab."""
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text=" Compare ")

        # Top banner with legend and Load Report button
        top_bar = tk.Frame(tab, bg=PALETTE["surface"], bd=1, relief="solid", padx=14, pady=10)
        top_bar.pack(fill=tk.X, pady=(0, 10))

        legend_text = (
            "Evidence Tiers: [MEASURED] Executed on this host  |  "
            "[SIMULATED] Pure logic simulation  |  "
            "[REFERENCE] Documented specification. "
            "(Only MEASURED values were observed on this machine.)"
        )
        lbl_legend = tk.Label(
            top_bar,
            text=legend_text,
            font=get_system_font(9),
            bg=PALETTE["surface"],
            fg=PALETTE["muted"],
        )
        lbl_legend.pack(side=tk.LEFT)

        btn_load = ttk.Button(
            top_bar,
            text="Load Report...",
            style="Secondary.TButton",
            command=self.load_report_action,
        )
        btn_load.pack(side=tk.RIGHT)

        # Matrix Treeview
        matrix_frame = tk.Frame(tab, bg=PALETTE["surface"], bd=1, relief="solid")
        matrix_frame.pack(fill=tk.BOTH, expand=True)

        m_cols = ("id", "test", "windows", "linux", "macos")
        self.matrix_tree = ttk.Treeview(matrix_frame, columns=m_cols, show="headings")
        self.matrix_tree.heading("id", text="ID")
        self.matrix_tree.heading("test", text="Compatibility Test")
        self.matrix_tree.heading("windows", text="Windows (Host)" if self.host_info.os_name == "Windows" else "Windows")
        self.matrix_tree.heading("linux", text="Linux (Host)" if self.host_info.os_name == "Linux" else "Linux")
        self.matrix_tree.heading("macos", text="macOS (Host)" if self.host_info.os_name == "macOS" else "macOS")

        self.matrix_tree.column("id", width=60, minwidth=50, stretch=False, anchor=tk.CENTER)
        self.matrix_tree.column("test", width=220, minwidth=180)
        self.matrix_tree.column("windows", width=260, minwidth=200)
        self.matrix_tree.column("linux", width=260, minwidth=200)
        self.matrix_tree.column("macos", width=260, minwidth=200)

        m_vsb = ttk.Scrollbar(matrix_frame, orient=tk.VERTICAL, command=self.matrix_tree.yview)
        self.matrix_tree.configure(yscrollcommand=m_vsb.set)
        self.matrix_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        m_vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.matrix_tree.tag_configure("even", background="#FFFFFF")
        self.matrix_tree.tag_configure("odd", background="#F8FAFC")

    def build_challenges_tab(self) -> None:
        """Tab 3: Challenges Faced and Developer Notes."""
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text=" Challenges ")

        paned = tk.PanedWindow(tab, orient=tk.HORIZONTAL, bg=PALETTE["border"], sashwidth=4, bd=0)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left: Scrollable challenge cards
        left_frame = tk.Frame(paned, bg=PALETTE["bg"])
        paned.add(left_frame, width=650)

        lbl_chal_head = tk.Label(
            left_frame,
            text="Built-in Challenges Faced Log",
            font=get_system_font(12, bold=True),
            bg=PALETTE["bg"],
            fg=PALETTE["text"],
        )
        lbl_chal_head.pack(anchor=tk.W, pady=(0, 6))

        canvas_frame = tk.Frame(left_frame, bg=PALETTE["surface"], bd=1, relief="solid")
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_frame, bg=PALETTE["surface"], highlightthickness=0)
        c_vsb = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_cards = tk.Frame(canvas, bg=PALETTE["surface"], padx=10, pady=10)

        scrollable_cards.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scrollable_cards, anchor="nw")
        canvas.configure(yscrollcommand=c_vsb.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        c_vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Mousewheel binding
        def _on_mousewheel(event: Any) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        for item in CHALLENGES:
            card = tk.Frame(scrollable_cards, bg="#F8FAFC", bd=1, relief="solid", padx=12, pady=10)
            card.pack(fill=tk.X, expand=True, pady=6)

            title_txt = f"{item.id}. {item.title}"
            tk.Label(card, text=title_txt, font=get_system_font(10, bold=True), bg="#F8FAFC", fg=PALETTE["primary"], anchor=tk.W).pack(fill=tk.X)
            tk.Label(card, text=f"Affected OS: {item.affected_os}", font=get_system_font(8, bold=True), bg="#F8FAFC", fg=PALETTE["muted"], anchor=tk.W).pack(fill=tk.X, pady=(1, 4))
            tk.Label(card, text=f"What happened: {item.what_happened}", font=get_system_font(9), bg="#F8FAFC", fg=PALETTE["text"], wraplength=580, justify=tk.LEFT, anchor=tk.W).pack(fill=tk.X)
            tk.Label(card, text=f"Solution: {item.how_handled}", font=get_system_font(9), bg="#F8FAFC", fg=PALETTE["success"], wraplength=580, justify=tk.LEFT, anchor=tk.W).pack(fill=tk.X, pady=(2, 0))

        # Right: My Notes
        right_frame = tk.Frame(paned, bg=PALETTE["surface"], bd=1, relief="solid", padx=14, pady=10)
        paned.add(right_frame)

        notes_top = tk.Frame(right_frame, bg=PALETTE["surface"])
        notes_top.pack(fill=tk.X, pady=(0, 6))

        tk.Label(notes_top, text="My Developer Notes", font=get_system_font(12, bold=True), bg=PALETTE["surface"], fg=PALETTE["text"]).pack(side=tk.LEFT)
        btn_save_notes = ttk.Button(notes_top, text="Save Notes", style="Primary.TButton", command=self.save_user_notes)
        btn_save_notes.pack(side=tk.RIGHT)

        tk.Label(
            right_frame,
            text="Autosaves to reports/my_notes.txt. Persists findings and lab notes across launches.",
            font=get_system_font(8),
            bg=PALETTE["surface"],
            fg=PALETTE["muted"],
            anchor=tk.W,
        ).pack(fill=tk.X, pady=(0, 6))

        self.txt_notes = tk.Text(
            right_frame,
            font=get_system_font(10),
            wrap=tk.WORD,
            bd=1,
            relief="solid",
            padx=8,
            pady=8,
        )
        self.txt_notes.pack(fill=tk.BOTH, expand=True)

    def build_about_tab(self) -> None:
        """Tab 4: About tab."""
        tab = ttk.Frame(self.notebook, padding=24)
        self.notebook.add(tab, text=" About ")

        card = tk.Frame(tab, bg=PALETTE["surface"], bd=1, relief="solid", padx=24, pady=20)
        card.pack(fill=tk.BOTH, expand=True)

        tk.Label(card, text=f"CompatLab v{__version__}", font=get_system_font(18, bold=True), bg=PALETTE["surface"], fg=PALETTE["primary"]).pack(anchor=tk.W, pady=(0, 4))
        tk.Label(card, text="Cross-Platform OS Compatibility Lab for Problem-Based Learning (PBL)", font=get_system_font(11, bold=True), bg=PALETTE["surface"], fg=PALETTE["text"]).pack(anchor=tk.W, pady=(0, 16))

        content = (
            "PROBLEM STATEMENT:\n"
            "'Cross-Platform Compatibility: Investigate how different operating systems handle compatibility. "
            "Develop a project that includes writing a simple application that runs on multiple OS platforms, "
            "highlighting the challenges faced.'\n\n"
            "HONEST THREE-TIER EVIDENCE MODEL:\n"
            "• MEASURED (Green): Test genuinely executed on this active host machine.\n"
            "• SIMULATED (Blue): Algorithmic simulation executed locally using real pure path parsing.\n"
            "• REFERENCE (Grey): Documented specification from OS documentation when direct execution is unavailable.\n"
            "Rule: CompatLab never presents reference or simulated data as measured.\n\n"
            "SAFETY & SANDBOX GUARANTEE:\n"
            "All filesystem tests operate exclusively inside an isolated temporary directory created "
            "via tempfile.TemporaryDirectory(). The app never modifies system files, requires zero "
            "administrator privileges, and leaves zero files behind.\n\n"
            "HOW TO RUN:\n"
            "• Desktop GUI: python main.py  or  run.bat\n"
            "• CLI Mode: python main.py --cli\n"
            "• Export reports: python main.py --cli --json report.json --html report.html\n"
            "• Run tests shortcut: Ctrl+R inside GUI"
        )

        lbl_body = tk.Label(
            card,
            text=content,
            font=get_system_font(10),
            bg=PALETTE["surface"],
            fg=PALETTE["text"],
            justify=tk.LEFT,
            wraplength=900,
        )
        lbl_body.pack(anchor=tk.W)

    def bind_events(self) -> None:
        """Bind keyboard shortcuts and event listeners."""
        self.root.bind("<Control-r>", lambda e: self.start_test_run())
        self.root.bind("<Control-R>", lambda e: self.start_test_run())

    def update_status(self, text: str) -> None:
        """Update status bar label and current timestamp."""
        self.status_lbl.config(text=text)
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.time_lbl.config(text=now_str)

    def start_test_run(self) -> None:
        """Trigger background test execution."""
        if self.is_running:
            return

        self.is_running = True
        self.btn_run.config(state=tk.DISABLED)
        self.progress_bar.config(mode="determinate", value=0, maximum=len(TESTS))
        self.progress_lbl.config(text="Starting tests...")
        self.update_status("Running compatibility suite in background...")

        # Clear treeview items
        for item in self.tree.get_children():
            self.tree.delete(item)

        thread = threading.Thread(target=self._run_tests_worker, daemon=True)
        thread.start()
        self.root.after(50, self._poll_test_queue)

    def _run_tests_worker(self) -> None:
        """Worker thread executing tests."""
        def on_prog(done: int, total: int, res: TestResult) -> None:
            self.test_queue.put(("progress", done, total, res))

        report = run_all(on_progress=on_prog)
        self.test_queue.put(("done", report))

    def _poll_test_queue(self) -> None:
        """Poll thread messages to update GUI seamlessly."""
        try:
            while not self.test_queue.empty():
                msg = self.test_queue.get_nowait()
                if msg[0] == "progress":
                    done, total, res = msg[1], msg[2], msg[3]
                    self.progress_bar.config(value=done)
                    self.progress_lbl.config(text=f"Running {res.id} of {total}...")
                    self.append_test_result_row(res)
                elif msg[0] == "done":
                    report: Report = msg[1]
                    self.current_report = report
                    self.is_running = False
                    self.btn_run.config(state=tk.NORMAL)
                    self.progress_lbl.config(text="Completed.")
                    self.update_summary_cards(report)
                    self.populate_compare_matrix(report)
                    self.update_status(f"Run complete: {report.summary['total']} tests finished in {round(sum(r.duration_ms for r in report.results), 1)} ms.")
                    return
        except queue.Empty:
            pass

        if self.is_running:
            self.root.after(50, self._poll_test_queue)

    def append_test_result_row(self, res: TestResult) -> None:
        """Insert single test result into Treeview."""
        status_tag = f"status_{res.status.value.lower()}"
        row_parity = "odd" if len(self.tree.get_children()) % 2 == 1 else "even"
        tags = (row_parity, status_tag)

        self.tree.insert(
            "",
            tk.END,
            iid=res.id,
            values=(
                res.id,
                res.name,
                res.category,
                res.status.value,
                res.host_value,
                f"{res.duration_ms:.1f} ms",
            ),
            tags=tags,
        )

    def update_summary_cards(self, report: Report) -> None:
        """Update metrics in 4 summary cards."""
        self.card_total.config(text=str(report.summary["total"]))
        self.card_differs.config(text=str(report.summary["differs"]))
        self.card_confirmed.config(text=str(report.summary["confirmed"]))
        self.card_errors.config(text=str(report.summary["errors"]))

    def on_tree_select(self, event: Any) -> None:
        """Handle row selection in Run tab Treeview."""
        selected = self.tree.selection()
        if not selected or not self.current_report:
            return

        test_id = selected[0]
        res = next((r for r in self.current_report.results if r.id == test_id), None)
        if not res:
            return

        self.lbl_detail_title.config(text=f"[{res.id}] {res.name} — {res.summary}")
        self.lbl_detail_explanation.config(
            text=f"WHY OSES DIFFER:\n{res.explanation}\n\nOBSERVED ON THIS MACHINE:\n{res.host_value}"
        )

        if res.challenge_note:
            self.lbl_detail_pitfall.config(text=f"Developer Pitfall: {res.challenge_note}")
            self.lbl_detail_pitfall.pack(fill=tk.X, pady=(0, 6))
        else:
            self.lbl_detail_pitfall.pack_forget()

        # Update OS cells strip
        for widget in self.detail_cells_frame.winfo_children():
            widget.destroy()

        for c in res.cells:
            cell_box = tk.Frame(self.detail_cells_frame, bg="#F1F5F9", bd=1, relief="solid", padx=10, pady=6)
            cell_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

            tier_bg = "#DCFCE7" if c.tier == Tier.MEASURED else ("#DBEAFE" if c.tier == Tier.SIMULATED else "#E2E8F0")
            tier_fg = "#15803D" if c.tier == Tier.MEASURED else ("#1D4ED8" if c.tier == Tier.SIMULATED else "#475569")

            head_frame = tk.Frame(cell_box, bg="#F1F5F9")
            head_frame.pack(fill=tk.X)

            tk.Label(head_frame, text=c.os_name, font=get_system_font(9, bold=True), bg="#F1F5F9", fg=PALETTE["text"]).pack(side=tk.LEFT)
            tk.Label(head_frame, text=f" {c.tier.value} ", font=get_system_font(8, bold=True), bg=tier_bg, fg=tier_fg).pack(side=tk.RIGHT)
            tk.Label(cell_box, text=c.value, font=get_system_font(9), bg="#F1F5F9", fg=PALETTE["text"], wraplength=280, justify=tk.LEFT, anchor=tk.W).pack(fill=tk.X, pady=(4, 0))

    def filter_treeview(self) -> None:
        """Filter rows in Treeview by selected category."""
        selected_cat = self.category_var.get()
        if not self.current_report:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        for res in self.current_report.results:
            if selected_cat == "All" or res.category == selected_cat:
                self.append_test_result_row(res)

    def populate_compare_matrix(self, report: Report) -> None:
        """Populate Compare matrix tab."""
        for item in self.matrix_tree.get_children():
            self.matrix_tree.delete(item)

        for idx, res in enumerate(report.results):
            cells = {c.os_name: c for c in res.cells}
            win_c = cells.get("Windows")
            lin_c = cells.get("Linux")
            mac_c = cells.get("macOS")

            def tag(c: Any) -> str:
                return f"[{c.tier.value[:4]}] {c.value}" if c else "-"

            parity = "odd" if idx % 2 == 1 else "even"
            self.matrix_tree.insert(
                "",
                tk.END,
                iid=f"m_{res.id}",
                values=(
                    res.id,
                    res.name,
                    tag(win_c),
                    tag(lin_c),
                    tag(mac_c),
                ),
                tags=(parity,),
            )

    def export_json_action(self) -> None:
        """Handle Export JSON button click with Save As dialog."""
        if not self.current_report:
            messagebox.showinfo("Export JSON", "Please run the compatibility tests first.")
            return

        now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        default_name = f"compatlab_{self.host_info.os_name}_{now_str}.json"
        initial_dir = Path("reports").resolve()
        initial_dir.mkdir(parents=True, exist_ok=True)

        path = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile=default_name,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return

        try:
            to_json(self.current_report, path)
            self.update_status(f"Exported JSON to {Path(path).name}")
            messagebox.showinfo("Export Successful", f"Report successfully saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Error", f"Unable to save JSON report:\n{exc}")

    def export_html_action(self) -> None:
        """Handle Export HTML button click with Save As dialog."""
        if not self.current_report:
            messagebox.showinfo("Export HTML", "Please run the compatibility tests first.")
            return

        now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        default_name = f"compatlab_{self.host_info.os_name}_{now_str}.html"
        initial_dir = Path("reports").resolve()
        initial_dir.mkdir(parents=True, exist_ok=True)

        path = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile=default_name,
            defaultextension=".html",
            filetypes=[("HTML files", "*.html")],
        )
        if not path:
            return

        try:
            to_html(self.current_report, path)
            self.update_status(f"Exported HTML to {Path(path).name}")
            messagebox.showinfo("Export Successful", f"HTML report successfully saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Error", f"Unable to save HTML report:\n{exc}")

    def copy_summary_action(self) -> None:
        """Copy text summary of current report to clipboard."""
        if not self.current_report:
            messagebox.showinfo("Copy Summary", "Please run the compatibility tests first.")
            return

        summary_text = to_text_summary(self.current_report)
        self.root.clipboard_clear()
        self.root.clipboard_append(summary_text)
        self.update_status("Summary copied to system clipboard.")
        messagebox.showinfo("Clipboard", "Plain-text report summary copied to clipboard.")

    def load_report_action(self) -> None:
        """Load external JSON report and overlay measured values into Compare matrix."""
        initial_dir = Path("reports").resolve()
        path = filedialog.askopenfilename(
            initialdir=initial_dir,
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return

        try:
            loaded_rep = from_json(path)
            self.loaded_reports.append(loaded_rep)

            if not self.current_report:
                self.current_report = loaded_rep
                self.populate_compare_matrix(loaded_rep)
                self.update_summary_cards(loaded_rep)
            else:
                # Merge loaded measured values into current matrix
                loaded_os = loaded_rep.host.os_name
                for loaded_res in loaded_rep.results:
                    matching = next((r for r in self.current_report.results if r.id == loaded_res.id), None)
                    if matching:
                        for cell in matching.cells:
                            if cell.os_name == loaded_os and cell.tier == Tier.REFERENCE:
                                loaded_host_cell = next((c for c in loaded_res.cells if c.os_name == loaded_os), None)
                                if loaded_host_cell and loaded_host_cell.tier == Tier.MEASURED:
                                    cell.value = f"{loaded_host_cell.value} (Loaded)"
                                    cell.tier = Tier.MEASURED
                self.populate_compare_matrix(self.current_report)

            self.update_status(f"Loaded external report: {Path(path).name} ({loaded_rep.host.os_name})")
            messagebox.showinfo(
                "Report Loaded",
                f"Successfully loaded {Path(path).name} from {loaded_rep.host.os_name}.\n"
                "Compare matrix updated with loaded measured data.",
            )
        except Exception as exc:
            messagebox.showerror("Load Error", f"Unable to parse selected report:\n{exc}")

    def load_user_notes(self) -> None:
        """Load user notes from reports/my_notes.txt if it exists."""
        notes_path = Path("reports/my_notes.txt")
        if notes_path.exists():
            try:
                with open(notes_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.txt_notes.insert("1.0", content)
            except Exception:
                pass

    def save_user_notes(self) -> None:
        """Save user notes to reports/my_notes.txt."""
        notes_path = Path("reports/my_notes.txt")
        notes_path.parent.mkdir(parents=True, exist_ok=True)
        content = self.txt_notes.get("1.0", tk.END).strip()
        try:
            with open(notes_path, "w", encoding="utf-8") as f:
                f.write(content + "\n")
            self.update_status("Notes saved to reports/my_notes.txt")
            messagebox.showinfo("Notes Saved", "Your notes have been saved to reports/my_notes.txt.")
        except Exception as exc:
            messagebox.showerror("Save Error", f"Failed to save notes:\n{exc}")


def launch_gui() -> int:
    """Initialize Tkinter application and start main loop."""
    # Set Windows High-DPI awareness
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    root = tk.Tk()
    app = CompatLabApp(root)
    root.mainloop()
    return 0
