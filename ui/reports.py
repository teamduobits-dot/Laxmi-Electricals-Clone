import customtkinter as ctk
from tkinter import messagebox, filedialog
import csv
from datetime import datetime

from utils.date_utils import fmt_date
from ui.widgets import style_status_label
from ui.theme import SURFACE, BORDER, TEXT, TEXT_MUTED, ROW_BG, PRIMARY, PRIMARY_HOV, BTN_SOFT_BG, BTN_SOFT_TX, BTN_SOFT_HV, FONT_FAMILY
from database.reports_repo import daily_summary, daily_bills, monthly_summary, monthly_bills, available_years


def _money(x) -> str:
    try:
        return f"₹{float(x):,.2f}"
    except:
        return "₹0.00"


class ReportsPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0,10))
        ctk.CTkLabel(header, text="Reports & Analytics", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text="Daily and monthly insights with CSV export", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).pack(side="left", padx=(12,0))

        self.tabs = ctk.CTkTabview(self, fg_color="transparent", segmented_button_fg_color=SURFACE, segmented_button_selected_color=PRIMARY, segmented_button_selected_hover_color=PRIMARY_HOV, text_color=TEXT, corner_radius=12)
        self.tabs.pack(fill="both", expand=True)
        self.tabs._segmented_button.configure(font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"))

        self.daily_tab = self.tabs.add("📅 Daily Report")
        self.monthly_tab = self.tabs.add("🗓 Monthly Report")

        self._build_daily()
        self._build_monthly()

    def _build_daily(self):
        top = ctk.CTkFrame(self.daily_tab, fg_color=SURFACE, corner_radius=12, border_width=1, border_color=BORDER)
        top.pack(fill="x", padx=6, pady=10)
        ctk.CTkLabel(top, text="Select Date", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).pack(side="left", padx=(14,8), pady=12)
        self.daily_date = ctk.CTkEntry(top, width=140, height=32, border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.daily_date.pack(side="left", padx=4, pady=10)
        today = datetime.now().strftime("%Y-%m-%d")
        self.daily_date.insert(0, today)
        ctk.CTkButton(top, text="🔍 Show", width=80, height=32, fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), command=self.refresh_daily).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(top, text="⬇ Export CSV", width=110, height=32, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=11), command=lambda: self.export_csv("daily")).pack(side="left", padx=4, pady=10)

        self.daily_cards = self._summary_row(self.daily_tab)
        self.daily_table = self._bills_table(self.daily_tab)
        self.refresh_daily()

    def refresh_daily(self):
        d = self.daily_date.get().strip()
        try:
            s = daily_summary(d)
            rows = daily_bills(d)
        except Exception as e:
            messagebox.showerror("Daily Report", str(e))
            return
        self._fill_summary(self.daily_cards, s)
        self._fill_table(self.daily_table, rows)

    def _build_monthly(self):
        top = ctk.CTkFrame(self.monthly_tab, fg_color=SURFACE, corner_radius=12, border_width=1, border_color=BORDER)
        top.pack(fill="x", padx=6, pady=10)
        years = available_years()
        this_year = datetime.now().year
        if this_year not in years:
            years = [this_year] + years
        years = sorted(set(years), reverse=True)
        ctk.CTkLabel(top, text="Year", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).pack(side="left", padx=(14,6), pady=12)
        self.year_var = ctk.StringVar(value=str(years[0]))
        self.year_menu = ctk.CTkOptionMenu(top, values=[str(y) for y in years], variable=self.year_var, width=90, height=32, fg_color=SURFACE, text_color=TEXT, button_color=PRIMARY, font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.year_menu.pack(side="left", padx=4, pady=10)
        ctk.CTkLabel(top, text="Month", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).pack(side="left", padx=(12,6), pady=12)
        months = [f"{i:02d}" for i in range(1,13)]
        self.month_var = ctk.StringVar(value=datetime.now().strftime("%m"))
        self.month_menu = ctk.CTkOptionMenu(top, values=months, variable=self.month_var, width=70, height=32, fg_color=SURFACE, text_color=TEXT, button_color=PRIMARY, font=ctk.CTkFont(family=FONT_FAMILY, size=11))
        self.month_menu.pack(side="left", padx=4, pady=10)
        ctk.CTkButton(top, text="🔍 Show", width=80, height=32, fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), command=self.refresh_monthly).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(top, text="⬇ Export CSV", width=110, height=32, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=11), command=lambda: self.export_csv("monthly")).pack(side="left", padx=4, pady=10)

        self.monthly_cards = self._summary_row(self.monthly_tab)
        self.monthly_table = self._bills_table(self.monthly_tab)
        self.refresh_monthly()

    def refresh_monthly(self):
        try:
            y = int(self.year_var.get())
            m = int(self.month_var.get())
            s = monthly_summary(y, m)
            rows = monthly_bills(y, m)
        except Exception as e:
            messagebox.showerror("Monthly Report", str(e))
            return
        self._fill_summary(self.monthly_cards, s)
        self._fill_table(self.monthly_table, rows)

    def export_csv(self, report_type):
        rows = []
        filename = f"report_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            if report_type == "daily":
                d = self.daily_date.get().strip()
                rows = daily_bills(d)
                filename = f"daily_report_{d}.csv"
            else:
                y = int(self.year_var.get())
                m = int(self.month_var.get())
                rows = monthly_bills(y, m)
                filename = f"monthly_report_{y}_{m:02d}.csv"
        except Exception as e:
            messagebox.showerror("Export", f"Error gathering data: {e}")
            return
        if not rows:
            messagebox.showinfo("Export", "No data to export for selected period.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files","*.csv")], initialfile=filename)
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            messagebox.showinfo("Export", f"✓ Report exported successfully!\n\n{len(rows)} rows saved to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export", f"Failed to save CSV:\n{e}")

    def _summary_row(self, master):
        row = ctk.CTkFrame(master, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=(0,10))
        for i in range(4):
            row.grid_columnconfigure(i, weight=1, uniform="summary")
        def card(title, icon, color):
            f = ctk.CTkFrame(row, fg_color=SURFACE, corner_radius=14, border_width=1, border_color=BORDER)
            top = ctk.CTkFrame(f, fg_color="transparent")
            top.pack(fill="x", padx=14, pady=(12,0))
            ctk.CTkLabel(top, text=icon, fg_color=color, width=28, height=28, corner_radius=8, text_color=TEXT).pack(side="left")
            ctk.CTkLabel(top, text=title, text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).pack(side="left", padx=(8,0))
            val = ctk.CTkLabel(f, text="—", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"), anchor="w")
            val.pack(anchor="w", padx=14, pady=(8,12))
            return f, val
        f1,v1 = card("Total Billed","💰",("#DBEAFE","#1E3A5F"))
        f2,v2 = card("Received","✅",("#DCFCE7","#064E3B"))
        f3,v3 = card("Pending Due","⏳",("#FFEDD5","#7C2D12"))
        f4,v4 = card("Invoices","🧾",("#F3E8FF","#581C87"))
        f1.grid(row=0, column=0, sticky="ew", padx=(0,8))
        f2.grid(row=0, column=1, sticky="ew", padx=(0,8))
        f3.grid(row=0, column=2, sticky="ew", padx=(0,8))
        f4.grid(row=0, column=3, sticky="ew")
        return {"total":v1,"received":v2,"due":v3,"bill_count":v4}

    def _fill_summary(self, cards, s: dict):
        cards["total"].configure(text=_money(s.get("total",0)))
        cards["received"].configure(text=_money(s.get("received",0)))
        cards["due"].configure(text=_money(s.get("due",0)))
        cards["bill_count"].configure(text=str(s.get("bill_count",0)))

    def _bills_table(self, master):
        card = ctk.CTkFrame(master, fg_color=SURFACE, corner_radius=14, border_width=1, border_color=BORDER)
        card.pack(fill="both", expand=True, padx=6, pady=(0,6))
        head = ctk.CTkFrame(card, fg_color="#F8FAFC", corner_radius=10)
        head.pack(fill="x", padx=14, pady=(14,8))
        cols = ["Bill No", "Date", "Customer", "Total", "Paid", "Due", "Status", "Mode"]
        widths = [100, 90, 220, 90, 90, 90, 80, 100]
        for i, (cname,w) in enumerate(zip(cols, widths)):
            head.grid_columnconfigure(i, minsize=w)
            ctk.CTkLabel(head, text=cname, text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), anchor="w").grid(row=0, column=i, sticky="w", padx=4, pady=8)
        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(fill="x", padx=14, pady=(0,8))
        rows_area = ctk.CTkScrollableFrame(card, fg_color="transparent")
        rows_area.pack(fill="both", expand=True, padx=8, pady=(0,10))
        return {"rows_area":rows_area,"widths":widths}

    def _fill_table(self, table, rows):
        area = table["rows_area"]
        widths = table["widths"]
        for w in area.winfo_children():
            w.destroy()
        if not rows:
            empty = ctk.CTkFrame(area, fg_color="transparent")
            empty.pack(pady=30)
            ctk.CTkLabel(empty, text="📊", font=ctk.CTkFont(size=28)).pack()
            ctk.CTkLabel(empty, text="No bills for this period", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold")).pack(pady=(8,2))
            ctk.CTkLabel(empty, text="Try a different date/month", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=11)).pack()
            return
        for r in rows:
            rf = ctk.CTkFrame(area, fg_color=ROW_BG, corner_radius=10, border_width=1, border_color=BORDER)
            rf.pack(fill="x", padx=6, pady=3)
            inner = ctk.CTkFrame(rf, fg_color="transparent")
            inner.pack(fill="x", padx=10, pady=9)
            created = fmt_date(r.get("created_at"))
            vals = [r.get("bill_number",""), created, r.get("customer_name",""), _money(r.get("total_amount",0)), _money(r.get("advance_paid",0)), _money(r.get("due_amount",0)), r.get("status",""), r.get("payment_mode","")]
            for i, (val,w) in enumerate(zip(vals, widths)):
                inner.grid_columnconfigure(i, minsize=w)
                if i==6:
                    lbl = ctk.CTkLabel(inner, text=str(val), width=64, height=20, corner_radius=20, font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"))
                    style_status_label(lbl, val)
                    lbl.grid(row=0, column=i, sticky="w")
                else:
                    lbl = ctk.CTkLabel(inner, text=str(val), text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=11), anchor="w")
                    lbl.grid(row=0, column=i, sticky="w", padx=2)
