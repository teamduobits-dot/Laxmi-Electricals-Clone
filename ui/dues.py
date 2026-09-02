import customtkinter as ctk
from tkinter import messagebox
import os
import platform
import subprocess

from database.dues_repo import list_due_bills, list_customers_for_filter, receive_payment
from pdf.invoice_generator import generate_invoice_pdf
from utils.storage import get_pdf_path, best_pdf_path_for_bill_number
from ui.widgets import style_status_label
from utils.date_utils import fmt_date
from ui.theme import SURFACE, BORDER, TEXT, TEXT_MUTED, ROW_BG, ROW_SELECTED_BG, BTN_SOFT_BG, BTN_SOFT_TX, BTN_SOFT_HV, PRIMARY, SUCCESS, SUCCESS_HOV, FONT_FAMILY


def money(v) -> str:
    try:
        return f"₹{float(v):,.2f}"
    except:
        return "₹0.00"

def open_pdf_path(path):
    if not os.path.exists(path):
        messagebox.showerror("PDF", f"PDF not found:\n{path}")
        return
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        messagebox.showerror("Open PDF", str(e))


class PaymentForm(ctk.CTkToplevel):
    def __init__(self, master, bill_id: int, bill_number: str, due_amount: float, on_saved):
        super().__init__(master)
        self.bill_id = bill_id
        self.bill_number = bill_number
        self.due_amount = float(due_amount or 0)
        self.on_saved = on_saved
        self.title("Receive Payment")
        self.geometry("500x400")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        box = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        box.pack(expand=True, fill="both", padx=16, pady=16)

        ctk.CTkLabel(box, text="Collect Payment", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold")).pack(anchor="w", padx=18, pady=(18,6))
        ctk.CTkLabel(box, text=f"Bill: {bill_number} • Due: {money(self.due_amount)}", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(anchor="w", padx=18, pady=(0,12))

        # Progress
        prog_frame = ctk.CTkFrame(box, fg_color="#F8FAFC", corner_radius=10)
        prog_frame.pack(fill="x", padx=18, pady=(0,14))
        ctk.CTkLabel(prog_frame, text="💡 You can collect full or partial payment", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(anchor="w", padx=12, pady=10)

        form = ctk.CTkFrame(box, fg_color="transparent")
        form.pack(fill="x", padx=18)
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Amount to Collect ₹ *", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=0, column=0, sticky="w", pady=10)
        self.amount_entry = ctk.CTkEntry(form, height=40, border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.amount_entry.grid(row=0, column=1, sticky="ew", padx=(10,0), pady=10)
        self.amount_entry.insert(0, str(self.due_amount))

        quick_row = ctk.CTkFrame(form, fg_color="transparent")
        quick_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,8))
        ctk.CTkLabel(quick_row, text="Quick:", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=10)).pack(side="left")
        for pct in [25,50,75,100]:
            amt = round(self.due_amount * pct/100, 2)
            ctk.CTkButton(quick_row, text=f"{pct}% (₹{amt:.0f})", width=70, height=24, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=6, font=ctk.CTkFont(family=FONT_FAMILY, size=10), command=lambda a=amt: self.set_amount(a)).pack(side="left", padx=4)

        ctk.CTkLabel(form, text="Payment Mode *", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=2, column=0, sticky="w", pady=10)
        self.mode_var = ctk.StringVar(value="Cash")
        self.mode_menu = ctk.CTkOptionMenu(form, values=["Cash","UPI","Bank Transfer"], variable=self.mode_var, height=36, fg_color=SURFACE, text_color=TEXT, button_color=PRIMARY, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.mode_menu.grid(row=2, column=1, sticky="w", padx=(10,0), pady=10)

        self.msg = ctk.CTkLabel(box, text="", text_color="#EF4444", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.msg.pack(anchor="w", padx=18, pady=(8,0))

        btns = ctk.CTkFrame(box, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=(18,18))
        ctk.CTkButton(btns, text="Cancel", fg_color="transparent", border_width=1, border_color=BORDER, text_color=TEXT, hover_color=BTN_SOFT_BG, corner_radius=8, command=self.destroy).pack(side="right", padx=(10,0))
        ctk.CTkButton(btns, text="✓ Confirm Payment", fg_color=SUCCESS, hover_color=SUCCESS_HOV, corner_radius=8, height=36, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold"), command=self.save).pack(side="right")
        self.amount_entry.focus_set()
        self.amount_entry.bind("<Return>", lambda e: self.save())

    def set_amount(self, amt):
        self.amount_entry.delete(0,"end")
        self.amount_entry.insert(0, str(amt))

    def save(self):
        try:
            amt = float(self.amount_entry.get().strip() or 0)
            mode = self.mode_var.get()
            receive_payment(self.bill_id, amt, mode)
            pdf_path = generate_invoice_pdf(self.bill_id)
            messagebox.showinfo("Payment Saved", f"✓ Payment received: {money(amt)} via {mode}\n\nPDF updated:\n{pdf_path}")
            self.on_saved()
            self.destroy()
        except Exception as e:
            self.msg.configure(text=str(e))


class DuesPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.selected_bill_id = None
        self.selected_bill_number = None
        self.selected_due_amount = 0.0

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0,16))
        header.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(left, text="Pending Dues", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(left, text="Collect outstanding payments and update bill status", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(anchor="w")
        self.count_label = ctk.CTkLabel(left, text="", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"))
        self.count_label.pack(anchor="w", pady=(6,0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")

        self.customers = list_customers_for_filter()
        self.customer_map = {"All Customers": None}
        customer_values = ["All Customers"]
        for c in self.customers:
            label = c["name"]
            if c.get("phone"):
                label = f"{c['name']} ({c['phone']})"
            customer_values.append(label)
            self.customer_map[label] = c["id"]

        self.customer_var = ctk.StringVar(value="All Customers")
        self.customer_menu = ctk.CTkOptionMenu(right, values=customer_values, variable=self.customer_var, width=200, height=36, fg_color=SURFACE, text_color=TEXT, button_color=PRIMARY, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), command=lambda v: self.refresh())
        self.customer_menu.pack(side="left", padx=(0,10))

        self.search_entry = ctk.CTkEntry(right, width=220, height=36, placeholder_text="🔍 Search bill / customer", border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.search_entry.pack(side="left", padx=(0,10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh())

        ctk.CTkButton(right, text="📄 PDF", width=70, height=34, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), command=self.open_pdf).pack(side="left", padx=(0,8))
        ctk.CTkButton(right, text="✓ Collect Payment", width=130, height=34, fg_color=SUCCESS, hover_color=SUCCESS_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), command=self.receive_payment).pack(side="left")

        card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        card.pack(fill="both", expand=True)

        head = ctk.CTkFrame(card, fg_color="#FEF2F2", corner_radius=12)
        head.pack(fill="x", padx=14, pady=(14,8))
        cols = ["Bill No", "Date", "Customer", "Total", "Paid", "Due", "Status", "Mode"]
        widths = [110, 90, 250, 90, 90, 90, 90, 120]
        for i, (t,w) in enumerate(zip(cols, widths)):
            head.grid_columnconfigure(i, minsize=w)
            ctk.CTkLabel(head, text=t, text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")).grid(row=0, column=i, sticky="w", padx=4, pady=10)

        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(fill="x", padx=14, pady=(0,8))
        self.rows_area = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self.rows_area.pack(fill="both", expand=True, padx=8, pady=(0,10))

        self.refresh()

    def refresh(self):
        q = self.search_entry.get().strip()
        customer_id = self.customer_map.get(self.customer_var.get(), None)
        rows = list_due_bills(search=q, customer_id=customer_id, limit=300)
        for w in self.rows_area.winfo_children():
            w.destroy()
        total_due = sum(float(r.get("due_amount",0) or 0) for r in rows)
        self.count_label.configure(text=f"⏳ {len(rows)} pending • Total due: {money(total_due)} • Select a bill to collect payment")
        self.selected_bill_id = None
        self.selected_bill_number = None
        self.selected_due_amount = 0.0
        if not rows:
            empty = ctk.CTkFrame(self.rows_area, fg_color="transparent")
            empty.pack(pady=60)
            ctk.CTkLabel(empty, text="🎉", font=ctk.CTkFont(size=32)).pack()
            ctk.CTkLabel(empty, text="No pending dues!", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")).pack(pady=(8,2))
            ctk.CTkLabel(empty, text="All bills are paid — great job!", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack()
            return
        widths = [110, 90, 250, 90, 90, 90, 90, 120]
        for r in rows:
            rid = r["id"]
            bn = r["bill_number"]
            due_amt = float(r.get("due_amount") or 0)
            rf = ctk.CTkFrame(self.rows_area, fg_color=ROW_BG, corner_radius=12, border_width=1, border_color=BORDER)
            rf.pack(fill="x", padx=8, pady=6)
            def select(_e=None, _id=rid, _bn=bn, _due=due_amt):
                self.selected_bill_id = _id
                self.selected_bill_number = _bn
                self.selected_due_amount = _due
                self._highlight()
            rf.bind("<Button-1>", select)
            inner = ctk.CTkFrame(rf, fg_color="transparent")
            inner.pack(fill="x", padx=10, pady=10)
            created = fmt_date(r.get("created_at"))
            vals = [bn, created, r.get("customer_name",""), money(r.get("total_amount",0)), money(r.get("advance_paid",0)), money(due_amt), r.get("status",""), r.get("payment_mode","")]
            for i, (val,w) in enumerate(zip(vals, widths)):
                inner.grid_columnconfigure(i, minsize=w)
                if i==6:
                    lbl = ctk.CTkLabel(inner, text=str(val), width=70, height=22, corner_radius=20, font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"))
                    style_status_label(lbl, val)
                    lbl.grid(row=0, column=i, sticky="w")
                    lbl.bind("<Button-1>", select)
                else:
                    fg = "#DC2626" if i==5 else TEXT
                    fw = "bold" if i==5 else "normal"
                    lbl = ctk.CTkLabel(inner, text=str(val), text_color=fg, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight=fw))
                    lbl.grid(row=0, column=i, sticky="w", padx=2)
                    lbl.bind("<Button-1>", select)
            rf._bill_id = rid
        self._highlight()

    def _highlight(self):
        for rf in self.rows_area.winfo_children():
            bid = getattr(rf, "_bill_id", None)
            if bid == self.selected_bill_id:
                rf.configure(fg_color=ROW_SELECTED_BG, border_color="#F87171")
            else:
                rf.configure(fg_color=ROW_BG, border_color=BORDER)

    def open_pdf(self):
        if not self.selected_bill_number:
            messagebox.showinfo("Dues", "Please select a bill first — click on a row.")
            return
        p = best_pdf_path_for_bill_number(self.selected_bill_number) or get_pdf_path(self.selected_bill_number)
        open_pdf_path(p)

    def receive_payment(self):
        if not self.selected_bill_id or not self.selected_bill_number:
            messagebox.showinfo("Dues", "Please select a bill first — click on a row with due amount.")
            return
        PaymentForm(self, bill_id=self.selected_bill_id, bill_number=self.selected_bill_number, due_amount=self.selected_due_amount, on_saved=self.refresh)
