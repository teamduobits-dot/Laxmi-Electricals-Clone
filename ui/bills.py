import os
import platform
import subprocess
import customtkinter as ctk
from tkinter import messagebox

from database.bills_repo import get_bill_bundle
from database.bills_manage_repo import list_bills, update_bill, delete_bill
from database.lookups_repo import list_customers, list_services
from pdf.invoice_generator import generate_invoice_pdf
from utils.storage import get_pdf_path, best_pdf_path_for_bill_number, delete_pdf_files_for_bill_number
from utils.whatsapp_share import open_whatsapp_chat, reveal_file_in_explorer
from ui.widgets import style_status_label
from utils.date_utils import fmt_date
from ui.theme import SURFACE, BORDER, TEXT, TEXT_MUTED, ROW_BG, ROW_SELECTED_BG, BTN_SOFT_BG, BTN_SOFT_TX, BTN_SOFT_HV, PRIMARY, PRIMARY_HOV, SUCCESS, SUCCESS_HOV, FONT_FAMILY


def money(v) -> str:
    try:
        return f"₹{float(v):,.2f}"
    except:
        return "₹0.00"

def open_pdf_file(bill_number: str):
    path = best_pdf_path_for_bill_number(bill_number) or get_pdf_path(bill_number)
    if not os.path.exists(path):
        try:
            path = generate_invoice_pdf(get_bill_bundle_by_number(bill_number))
        except:
            pass
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

def get_bill_bundle_by_number(bill_number: str):
    from database.db import get_connection
    con = get_connection()
    try:
        row = con.execute("SELECT id FROM Bills WHERE bill_number=? LIMIT 1;", (bill_number,)).fetchone()
        return row["id"] if row else None
    finally:
        con.close()

def open_pdf_path(p):
    if not os.path.exists(p):
        messagebox.showerror("PDF", f"PDF not found:\n{p}")
        return
    try:
        if platform.system() == "Windows":
            os.startfile(p)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", p])
        else:
            subprocess.Popen(["xdg-open", p])
    except Exception as e:
        messagebox.showerror("Open", str(e))


class EditItemRow(ctk.CTkFrame):
    def __init__(self, master, idx: int, services: list, on_change, on_remove):
        super().__init__(master, fg_color=ROW_BG, corner_radius=12, border_width=1, border_color=BORDER)
        self.services = services
        self.on_change = on_change
        self.on_remove = on_remove
        self.grid_columnconfigure(1, weight=1)

        self.sr = ctk.CTkLabel(self, text=f"{idx:02d}", width=36, fg_color=PRIMARY, text_color="white", corner_radius=6, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"))
        self.sr.grid(row=0, column=0, sticky="w", padx=(10, 0), pady=10)

        service_names = [s["service_name"] for s in services] if services else ["(No services)"]
        self.service_var = ctk.StringVar(value=service_names[0])
        self.service_menu = ctk.CTkOptionMenu(self, values=service_names, variable=self.service_var, command=lambda v: self.on_change(), width=180, fg_color=SURFACE, text_color=TEXT, button_color=PRIMARY, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.service_menu.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

        self.qty = ctk.CTkEntry(self, width=70, height=32, border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.qty.insert(0, "1")
        self.qty.grid(row=0, column=2, padx=(0, 10), pady=10)

        self.rate = ctk.CTkEntry(self, width=100, height=32, border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.rate.insert(0, "0")
        self.rate.grid(row=0, column=3, padx=(0, 10), pady=10)

        self.amount_label = ctk.CTkLabel(self, text="₹0.00", width=90, text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"))
        self.amount_label.grid(row=0, column=4, padx=(0, 10), pady=10)

        self.remove_btn = ctk.CTkButton(self, text="✕", width=32, height=30, fg_color="#FEE2E2", text_color="#991B1B", hover_color="#FECACA", corner_radius=8, command=self.on_remove)
        self.remove_btn.grid(row=0, column=5, padx=(0, 10), pady=10)

        self.qty.bind("<KeyRelease>", lambda e: self.on_change())
        self.qty.bind("<FocusOut>", lambda e: self.on_change())
        self.rate.bind("<KeyRelease>", lambda e: self.on_change())
        self.rate.bind("<FocusOut>", lambda e: self.on_change())

    def set_index(self, idx: int):
        self.sr.configure(text=f"{idx:02d}")

    def set_values(self, service_name: str, qty, rate):
        vals = list(self.service_menu.cget("values"))
        if service_name in vals:
            self.service_var.set(service_name)
        else:
            # add if not in list (preserve history)
            vals.append(service_name)
            self.service_menu.configure(values=vals)
            self.service_var.set(service_name)
        self.qty.delete(0, "end")
        self.qty.insert(0, str(qty))
        self.rate.delete(0, "end")
        self.rate.insert(0, str(rate))

    def get_item(self):
        name = (self.service_var.get() or "").strip()
        try:
            qty = float(self.qty.get().strip() or 0)
        except:
            qty = 0.0
        try:
            rate = float(self.rate.get().strip() or 0)
        except:
            rate = 0.0
        return {"service_name": name, "qty": qty, "rate": rate, "amount": qty * rate}

    def update_amount(self):
        it = self.get_item()
        self.amount_label.configure(text=f"₹{it['amount']:,.2f}")


class BillEditForm(ctk.CTkToplevel):
    def __init__(self, master, bill_id: int, on_saved):
        super().__init__(master)
        self.bill_id = bill_id
        self.on_saved = on_saved
        self.title("Edit Bill")
        self.geometry("1060x720")
        self.transient(master)
        self.grab_set()

        self.bundle = get_bill_bundle(bill_id)
        self.bill = self.bundle["bill"]
        self.items = self.bundle["items"] or []

        self.customers = [dict(r) for r in list_customers()]
        self.services = [dict(r) for r in list_services()]

        self.customer_map = {}
        cust_values = []
        for c in self.customers:
            label = c["name"]
            if c.get("phone"):
                label = f"{c['name']} ({c['phone']})"
            cust_values.append(label)
            self.customer_map[label] = c["id"]

        container = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        container.pack(expand=True, fill="both", padx=16, pady=16)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=f"Edit Bill: {self.bill['bill_number']}", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text=f"Created: {fmt_date(self.bill.get('created_at'))} | Status: {self.bill.get('status')}", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=1, column=0, sticky="w", pady=(2,0))

        top = ctk.CTkFrame(container, fg_color="transparent")
        top.grid(row=1, column=0, sticky="ew", padx=18, pady=6)
        top.grid_columnconfigure(1, weight=1)

        # Customer
        ctk.CTkLabel(top, text="Customer", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=0, column=0, sticky="w", pady=6)
        self.customer_var = ctk.StringVar(value=cust_values[0] if cust_values else "")
        self.customer_menu = ctk.CTkOptionMenu(top, values=cust_values, variable=self.customer_var, width=260, fg_color=SURFACE, text_color=TEXT, button_color=PRIMARY)
        self.customer_menu.grid(row=0, column=1, sticky="w", padx=(12, 18), pady=6)

        current_id = self.bill["customer_id"]
        for label, cid in self.customer_map.items():
            if cid == current_id:
                self.customer_var.set(label)
                break

        ctk.CTkLabel(top, text="Payment Mode", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=0, column=2, sticky="w", pady=6)
        self.payment_var = ctk.StringVar(value=self.bill.get("payment_mode", "Cash"))
        self.payment_menu = ctk.CTkOptionMenu(top, values=["Cash", "UPI", "Bank Transfer"], variable=self.payment_var, fg_color=SURFACE, text_color=TEXT, button_color=PRIMARY)
        self.payment_menu.grid(row=0, column=3, sticky="w", padx=(12, 0), pady=6)

        # Second row: Discount GST
        ctk.CTkLabel(top, text="Discount (₹)", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=1, column=0, sticky="w", pady=6)
        self.discount_entry = ctk.CTkEntry(top, width=120, height=30, border_width=1, border_color=BORDER)
        self.discount_entry.grid(row=1, column=1, sticky="w", padx=12, pady=6)
        self.discount_entry.insert(0, str(float(self.bill.get("discount_amount", 0) or 0)))
        self.discount_entry.bind("<KeyRelease>", lambda e: self.recalc())
        self.discount_entry.bind("<FocusOut>", lambda e: self.recalc())

        ctk.CTkLabel(top, text="GST (%)", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=1, column=2, sticky="w", pady=6)
        self.gst_entry = ctk.CTkEntry(top, width=120, height=30, border_width=1, border_color=BORDER)
        self.gst_entry.grid(row=1, column=3, sticky="w", padx=12, pady=6)
        self.gst_entry.insert(0, str(float(self.bill.get("tax_percent", 0) or 0)))
        self.gst_entry.bind("<KeyRelease>", lambda e: self.recalc())
        self.gst_entry.bind("<FocusOut>", lambda e: self.recalc())

        # Address override
        ctk.CTkLabel(top, text="Bill Address (optional)", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=2, column=0, sticky="nw", pady=10)
        self.addr_entry = ctk.CTkTextbox(top, height=60, width=500, border_width=1, border_color=BORDER, corner_radius=8)
        self.addr_entry.grid(row=2, column=1, columnspan=3, sticky="ew", padx=12, pady=6)
        self.addr_entry.insert("1.0", self.bill.get("bill_address","") or "")

        items_head = ctk.CTkFrame(container, fg_color="transparent")
        items_head.grid(row=2, column=0, sticky="ew", padx=18, pady=(12, 6))
        ctk.CTkLabel(items_head, text="Items", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")).pack(side="left")
        ctk.CTkButton(items_head, text="+ Add Item", fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), command=self.add_item).pack(side="right")

        self.items_area = ctk.CTkScrollableFrame(container, fg_color="transparent")
        self.items_area.grid(row=3, column=0, sticky="nsew", padx=18, pady=(0, 10))

        self.item_rows = []
        for it in self.items:
            self.add_item(prefill=it)
        if not self.item_rows:
            self.add_item()

        bottom = ctk.CTkFrame(container, fg_color="#F8FAFC", corner_radius=12)
        bottom.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 18))
        bottom.grid_columnconfigure(0, weight=1)

        self.subtotal_label = ctk.CTkLabel(bottom, text="Subtotal: ₹0.00", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.subtotal_label.grid(row=0, column=0, sticky="w", padx=12, pady=(12,2))
        self.total_label = ctk.CTkLabel(bottom, text="Total: ₹0.00 | Due: ₹0.00", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"))
        self.total_label.grid(row=1, column=0, sticky="w", padx=12, pady=(2,12))

        adv_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        adv_frame.grid(row=0, column=1, rowspan=2, sticky="e", padx=12, pady=10)
        ctk.CTkLabel(adv_frame, text="Advance ₹", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(side="left", padx=(0, 8))
        self.advance_entry = ctk.CTkEntry(adv_frame, width=120, height=32, border_width=1, border_color=BORDER)
        self.advance_entry.pack(side="left")
        self.advance_entry.insert(0, str(float(self.bill.get("advance_paid", 0) or 0)))
        self.advance_entry.bind("<KeyRelease>", lambda e: self.recalc())
        self.advance_entry.bind("<FocusOut>", lambda e: self.recalc())

        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.grid(row=5, column=0, sticky="e", padx=18, pady=(0, 18))
        ctk.CTkButton(btns, text="Cancel", fg_color="transparent", border_width=1, border_color=BORDER, text_color=TEXT, hover_color=BTN_SOFT_BG, corner_radius=8, command=self.destroy).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btns, text="✓ Save + Regenerate PDF", fg_color=SUCCESS, hover_color=SUCCESS_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold"), command=self.save).pack(side="right")

        self.recalc()

    def add_item(self, prefill=None):
        def on_change():
            self.recalc()
        def on_remove():
            self.remove_item(row)
        row = EditItemRow(self.items_area, len(self.item_rows) + 1, self.services, on_change=on_change, on_remove=on_remove)
        row.pack(fill="x", padx=8, pady=6)
        if prefill:
            row.set_values(prefill.get("service_name", ""), prefill.get("qty", 1), prefill.get("rate", 0))
        self.item_rows.append(row)
        self.recalc()

    def remove_item(self, row):
        if len(self.item_rows) <= 1:
            messagebox.showwarning("Items", "At least one item is required.")
            return
        if row in self.item_rows:
            row.destroy()
            self.item_rows.remove(row)
        for i, r in enumerate(self.item_rows, start=1):
            r.set_index(i)
        self.recalc()

    def recalc(self):
        if not hasattr(self, "advance_entry"):
            return
        subtotal = 0.0
        for r in self.item_rows:
            r.update_amount()
            subtotal += r.get_item()["amount"]

        try:
            adv = float(self.advance_entry.get().strip() or 0)
        except:
            adv = 0.0
        try:
            disc = float(self.discount_entry.get().strip() or 0)
        except:
            disc = 0.0
        try:
            gst = float(self.gst_entry.get().strip() or 0)
        except:
            gst = 0.0

        if disc < 0:
            disc = 0
        if gst < 0:
            gst = 0
        if disc > subtotal:
            self.discount_entry.configure(border_color="#EF4444")
        else:
            self.discount_entry.configure(border_color=BORDER)

        taxable = max(0, subtotal - disc)
        tax_amount = (taxable * gst)/100.0
        total = taxable + tax_amount
        if adv <0:
            adv=0
        if adv>total and total>0:
            self.advance_entry.configure(border_color="#EF4444")
        else:
            self.advance_entry.configure(border_color=BORDER)

        due = max(0, total - adv)
        self.subtotal_label.configure(text=f"Subtotal: ₹{subtotal:,.2f} | Discount: ₹{disc:,.2f} | Taxable: ₹{taxable:,.2f} | GST {gst}%: ₹{tax_amount:,.2f}")
        self.total_label.configure(text=f"Total: ₹{total:,.2f} | Advance: ₹{adv:,.2f} | Due: ₹{due:,.2f}")

    def save(self):
        customer_id = self.customer_map.get(self.customer_var.get())
        if not customer_id:
            messagebox.showerror("Edit Bill", "Customer is required.")
            return
        items = [{"service_name": r.get_item()["service_name"], "qty": r.get_item()["qty"], "rate": r.get_item()["rate"]} for r in self.item_rows]
        if not items or any(not i["service_name"] for i in items):
            messagebox.showerror("Edit Bill", "All items must have a valid service name.")
            return

        try:
            adv = float(self.advance_entry.get().strip() or 0)
            disc = float(self.discount_entry.get().strip() or 0)
            gst = float(self.gst_entry.get().strip() or 0)
            mode = self.payment_var.get()
            addr = self.addr_entry.get("1.0","end").strip()
            update_bill(self.bill_id, customer_id, items, adv, mode, tax_percent=gst, discount_amount=disc, bill_address=addr)
            pdf_path = generate_invoice_pdf(self.bill_id)
        except Exception as e:
            messagebox.showerror("Edit Bill Failed", str(e))
            return

        messagebox.showinfo("Edit Bill", f"Saved successfully!\n\nBill edited and PDF regenerated:\n{pdf_path}")
        self.on_saved()
        self.destroy()


class BillsPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.selected_id = None
        self.selected_bill_number = None

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        header.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(left, text="Bills History", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(left, text="Search, view, edit and share your invoices", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(anchor="w")
        self.count_label = ctk.CTkLabel(left, text="", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.count_label.pack(anchor="w", pady=(4,0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")

        self.search_entry = ctk.CTkEntry(right, width=260, height=36, placeholder_text="🔍 Search bill / customer / phone", border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh())

        ctk.CTkButton(right, text="📄 Open PDF", width=90, height=34, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), command=self.open_pdf).pack(side="left", padx=(0, 8))
        ctk.CTkButton(right, text="💬 WhatsApp", width=100, height=34, fg_color="#DCFCE7", text_color="#166534", hover_color="#BBF7D0", corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), command=self.share_whatsapp).pack(side="left", padx=(0, 8))
        ctk.CTkButton(right, text="✎ Edit", width=70, height=34, fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), command=self.edit_bill).pack(side="left", padx=(0, 8))
        ctk.CTkButton(right, text="🗑 Delete", width=80, height=34, fg_color="#FEE2E2", text_color="#991B1B", hover_color="#FECACA", corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), command=self.delete_bill).pack(side="left")

        card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        card.pack(fill="both", expand=True)

        head = ctk.CTkFrame(card, fg_color="#F8FAFC", corner_radius=12)
        head.pack(fill="x", padx=14, pady=(14, 8))
        cols = ["Bill No", "Date", "Customer", "Total", "Paid", "Due", "Status", "Mode"]
        widths = [110, 90, 260, 90, 90, 90, 90, 120]
        for i, (t, w) in enumerate(zip(cols, widths)):
            head.grid_columnconfigure(i, minsize=w)
            ctk.CTkLabel(head, text=t, text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")).grid(row=0, column=i, sticky="w", padx=4, pady=10)

        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(fill="x", padx=14, pady=(0, 8))
        self.rows_area = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self.rows_area.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        self.refresh()

    def refresh(self):
        q = self.search_entry.get().strip()
        rows = list_bills(q, limit=120)

        for w in self.rows_area.winfo_children():
            w.destroy()

        self.count_label.configure(text=f"Showing {len(rows)} bills • Select a row to take action")
        self.selected_id = None
        self.selected_bill_number = None

        if not rows:
            empty = ctk.CTkFrame(self.rows_area, fg_color="transparent")
            empty.pack(pady=60)
            ctk.CTkLabel(empty, text="📭", font=ctk.CTkFont(size=32)).pack()
            ctk.CTkLabel(empty, text="No bills found", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")).pack(pady=(8,2))
            ctk.CTkLabel(empty, text="Try different search or create a new bill", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack()
            return

        widths = [110, 90, 260, 90, 90, 90, 90, 120]
        for r in rows:
            rid = r["id"]
            bn = r["bill_number"]
            rf = ctk.CTkFrame(self.rows_area, fg_color=ROW_BG, corner_radius=12, border_width=1, border_color=BORDER)
            rf.pack(fill="x", padx=8, pady=6)

            def select(_e=None, _id=rid, _bn=bn):
                self.selected_id = _id
                self.selected_bill_number = _bn
                self._highlight()

            rf.bind("<Button-1>", select)
            inner = ctk.CTkFrame(rf, fg_color="transparent")
            inner.pack(fill="x", padx=10, pady=10)
            created = fmt_date(r.get("created_at"))
            vals = [
                r.get("bill_number", ""),
                created,
                r.get("customer_name", ""),
                money(r.get("total_amount", 0)),
                money(r.get("advance_paid", 0)),
                money(r.get("due_amount", 0)),
                r.get("status", ""),
                r.get("payment_mode", ""),
            ]
            for i, (val, w) in enumerate(zip(vals, widths)):
                inner.grid_columnconfigure(i, minsize=w)
                if i == 6:
                    lbl = ctk.CTkLabel(inner, text=str(val), width=70, height=22, corner_radius=20, font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"))
                    style_status_label(lbl, val)
                    lbl.grid(row=0, column=i, sticky="w")
                    lbl.bind("<Button-1>", select)
                else:
                    lbl = ctk.CTkLabel(inner, text=str(val), text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), anchor="w")
                    lbl.grid(row=0, column=i, sticky="w", padx=2)
                    lbl.bind("<Button-1>", select)
            rf._bill_id = rid
        self._highlight()

    def _highlight(self):
        for rf in self.rows_area.winfo_children():
            bid = getattr(rf, "_bill_id", None)
            if bid == self.selected_id:
                rf.configure(fg_color=ROW_SELECTED_BG, border_color=PRIMARY)
            else:
                rf.configure(fg_color=ROW_BG, border_color=BORDER)

    def open_pdf(self):
        if not self.selected_bill_number:
            messagebox.showinfo("Bills", "Please select a bill first — click on any row.")
            return
        path = best_pdf_path_for_bill_number(self.selected_bill_number) or get_pdf_path(self.selected_bill_number)
        if not os.path.exists(path):
            # try generate
            try:
                from database.db import get_connection
                con = get_connection()
                try:
                    row = con.execute("SELECT id FROM Bills WHERE bill_number=?", (self.selected_bill_number,)).fetchone()
                    if row:
                        path = generate_invoice_pdf(row["id"])
                finally:
                    con.close()
            except Exception as e:
                messagebox.showerror("PDF", f"PDF not found and regeneration failed:\n{e}")
                return
        open_pdf_path(path)

    def share_whatsapp(self):
        if not self.selected_id or not self.selected_bill_number:
            messagebox.showinfo("WhatsApp", "Please select a bill first.")
            return
        bundle = get_bill_bundle(self.selected_id)
        bill = bundle.get("bill", {})
        customer = bundle.get("customer", {}) or {}
        phone = (customer.get("phone") or "").strip()
        cname = (customer.get("name") or "").strip()
        bill_no = bill.get("bill_number") or self.selected_bill_number
        pdf_path = get_pdf_path(bill_no, customer_name=cname, customer_phone=phone)
        if not os.path.exists(pdf_path):
            try:
                pdf_path = generate_invoice_pdf(self.selected_id)
            except Exception as e:
                messagebox.showerror("WhatsApp", f"PDF not found and regeneration failed:\n{e}")
                return
        total = bill.get("total_amount", 0)
        due = bill.get("due_amount", 0)
        msg = f"Hello {cname},\n\nInvoice: {bill_no}\nTotal: ₹{float(total):,.2f}\nDue: ₹{float(due):,.2f}\n\nThank you for your business!\n- Laxmi Electricals"
        try:
            open_whatsapp_chat(phone, msg)
            reveal_file_in_explorer(pdf_path)
            messagebox.showinfo("WhatsApp", f"✅ WhatsApp opened!\n\nTo send PDF:\n1) File Explorer highlighted the PDF.\n2) Drag & drop into WhatsApp Web OR click 📎 Attach → Document.\n\nPDF:\n{pdf_path}")
        except Exception as e:
            messagebox.showerror("WhatsApp", str(e))

    def edit_bill(self):
        if not self.selected_id:
            messagebox.showinfo("Bills", "Please select a bill first.")
            return
        BillEditForm(self, self.selected_id, on_saved=self.refresh)

    def delete_bill(self):
        if not self.selected_id or not self.selected_bill_number:
            messagebox.showinfo("Bills", "Please select a bill first.")
            return
        ok = messagebox.askyesno("Delete Bill", f"Delete bill {self.selected_bill_number}?\n\nThis will permanently delete:\n• Bill from database\n• All PDFs matching this bill\n• Payment history\n\nThis cannot be undone!", icon="warning")
        if not ok:
            return
        bn = self.selected_bill_number
        try:
            delete_bill(self.selected_id)
            deleted_count = delete_pdf_files_for_bill_number(bn)
        except Exception as e:
            messagebox.showerror("Delete Bill Failed", str(e))
            return
        self.refresh()
        messagebox.showinfo("Delete Bill", f"✓ Bill deleted.\nPDF files removed: {deleted_count}")
