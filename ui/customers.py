import os
import platform
import subprocess
import customtkinter as ctk
from tkinter import messagebox

from utils.date_utils import fmt_date
from utils.storage import get_pdf_path, best_pdf_path_for_bill_number
from utils.validators import sanitize_phone_entry, clean_phone, is_valid_phone
from ui.widgets import style_status_label
from ui.theme import SURFACE, BORDER, TEXT, TEXT_MUTED, ROW_BG, ROW_SELECTED_BG, BTN_SOFT_BG, BTN_SOFT_TX, BTN_SOFT_HV, PRIMARY, PRIMARY_HOV, SUCCESS, SUCCESS_HOV, FONT_FAMILY

from database.customers_repo import create_customer, update_customer, delete_customer, search_customers, get_customer
from database.customer_bills_repo import list_bills_for_customer, customer_bill_stats
from database.dues_repo import receive_payment
from pdf.invoice_generator import generate_invoice_pdf


def money(v) -> str:
    try:
        return f"₹{float(v):,.2f}"
    except:
        return "₹0.00"

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


class PaymentForm(ctk.CTkToplevel):
    def __init__(self, master, bill_id: int, bill_number: str, due_amount: float, on_saved):
        super().__init__(master)
        self.bill_id = bill_id
        self.bill_number = bill_number
        self.due_amount = float(due_amount or 0)
        self.on_saved = on_saved
        self.title("Receive Payment")
        self.geometry("460x360")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        box = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        box.pack(expand=True, fill="both", padx=16, pady=16)
        ctk.CTkLabel(box, text="Receive Payment", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold")).pack(anchor="w", padx=18, pady=(18,6))
        ctk.CTkLabel(box, text=f"{bill_number} • Due: {money(self.due_amount)}", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(anchor="w", padx=18, pady=(0,12))
        form = ctk.CTkFrame(box, fg_color="transparent")
        form.pack(fill="x", padx=18)
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(form, text="Amount ₹", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=0, column=0, sticky="w", pady=10)
        self.amount_entry = ctk.CTkEntry(form, height=36, border_width=1, border_color=BORDER)
        self.amount_entry.grid(row=0, column=1, sticky="ew", padx=(10,0), pady=10)
        self.amount_entry.insert(0, str(self.due_amount))
        ctk.CTkLabel(form, text="Mode", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=1, column=0, sticky="w", pady=10)
        self.mode_var = ctk.StringVar(value="Cash")
        self.mode_menu = ctk.CTkOptionMenu(form, values=["Cash","UPI","Bank Transfer"], variable=self.mode_var, fg_color=SURFACE, text_color=TEXT, button_color=PRIMARY)
        self.mode_menu.grid(row=1, column=1, sticky="w", padx=(10,0), pady=10)
        self.msg = ctk.CTkLabel(box, text="", text_color="#EF4444", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.msg.pack(anchor="w", padx=18, pady=(8,0))
        btns = ctk.CTkFrame(box, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=(18,18))
        ctk.CTkButton(btns, text="Cancel", fg_color="transparent", border_width=1, border_color=BORDER, text_color=TEXT, hover_color=BTN_SOFT_BG, corner_radius=8, command=self.destroy).pack(side="right", padx=(10,0))
        ctk.CTkButton(btns, text="✓ Collect", fg_color=SUCCESS, hover_color=SUCCESS_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold"), command=self.save).pack(side="right")
        self.amount_entry.focus_set()
        self.amount_entry.bind("<Return>", lambda e: self.save())

    def save(self):
        try:
            amt = float(self.amount_entry.get().strip() or 0)
            mode = self.mode_var.get()
            receive_payment(self.bill_id, amt, mode)
            generate_invoice_pdf(self.bill_id)
            self.on_saved()
            self.destroy()
        except Exception as e:
            self.msg.configure(text=str(e))


class CustomerBillsModal(ctk.CTkToplevel):
    def __init__(self, master, customer_id: int, customer_name: str):
        super().__init__(master)
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.title(f"Bills - {customer_name}")
        self.geometry("1060x640")
        self.transient(master)
        self.grab_set()
        box = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        box.pack(expand=True, fill="both", padx=16, pady=16)
        box.grid_columnconfigure(0, weight=1)
        box.grid_rowconfigure(5, weight=1)

        head = ctk.CTkFrame(box, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(18,8))
        ctk.CTkLabel(head, text=f"Bill History: {customer_name}", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold")).pack(side="left")
        ctk.CTkButton(head, text="✕ Close", width=80, height=30, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, command=self.destroy).pack(side="right")

        self.summary_label = ctk.CTkLabel(box, text="", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.summary_label.grid(row=1, column=0, sticky="w", padx=18, pady=(0,10))

        self.cols = [("bill","Bill No",120, "center","center"),("date","Date",110,"center","center"),("status","Status",90,"center","center"),("total","Total",110,"center","e"),("paid","Paid",100,"center","e"),("due","Due",100,"center","e"),("update","Collect",100,"center","center"),("pdf","PDF",80,"center","center"),("spacer","",1,"center","center")]

        header = ctk.CTkFrame(box, fg_color="#F8FAFC", corner_radius=10)
        header.grid(row=2, column=0, sticky="ew", padx=14, pady=6)
        for i, (_k,_t,w,ha,ca) in enumerate(self.cols):
            if w==1:
                header.grid_columnconfigure(i, weight=1)
            else:
                header.grid_columnconfigure(i, weight=0, minsize=w)
        for i, (_k,title,_w,h_anchor,_ca) in enumerate(self.cols):
            if title:
                ctk.CTkLabel(header, text=title, text_color=TEXT_MUTED, anchor=h_anchor, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")).grid(row=0, column=i, sticky="ew", padx=4, pady=10)

        ctk.CTkFrame(box, height=1, fg_color=BORDER).grid(row=3, column=0, sticky="ew", padx=14, pady=(4,0))
        self.rows = ctk.CTkScrollableFrame(box, fg_color="transparent")
        self.rows.grid(row=5, column=0, sticky="nsew", padx=14, pady=(10, 16))
        self.refresh()

    def refresh(self):
        stats = customer_bill_stats(self.customer_id)
        self.summary_label.configure(text=f"📊 Bills: {stats['bill_count']} • Total: {money(stats['total_amount'])} • Received: {money(stats['received'])} • Due: {money(stats['due'])}")
        for w in self.rows.winfo_children():
            w.destroy()
        bills = list_bills_for_customer(self.customer_id)
        if not bills:
            ctk.CTkLabel(self.rows, text="No bills found for this customer.", text_color=TEXT_MUTED).pack(pady=20)
            return
        for b in bills:
            self._add_bill_row(b)

    def _add_bill_row(self, b: dict):
        bill_id = b.get("id")
        bill_no = b.get("bill_number","")
        due_amt = float(b.get("due_amount") or 0)
        rf = ctk.CTkFrame(self.rows, fg_color=ROW_BG, corner_radius=12, border_width=1, border_color=BORDER)
        rf.pack(fill="x", padx=8, pady=5)
        row = ctk.CTkFrame(rf, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=10)
        for i, (_k,_t,w,ha,ca) in enumerate(self.cols):
            if w==1:
                row.grid_columnconfigure(i, weight=1)
            else:
                row.grid_columnconfigure(i, weight=0, minsize=w)
        values = {"bill":bill_no,"date":fmt_date(b.get("created_at")),"status":b.get("status",""),"total":money(b.get("total_amount",0)),"paid":money(b.get("advance_paid",0)),"due":money(due_amt)}
        for i, (k,_t,_w,ha,cell_anchor) in enumerate(self.cols):
            if k=="pdf":
                ctk.CTkButton(row, text="PDF", width=60, height=28, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), command=lambda bn=bill_no: open_pdf_path(best_pdf_path_for_bill_number(bn) or get_pdf_path(bn))).grid(row=0, column=i, sticky="e", padx=4)
            elif k=="update":
                btn = ctk.CTkButton(row, text="Pay", width=60, height=28, fg_color=SUCCESS, hover_color=SUCCESS_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), command=lambda: self._update_payment(bill_id, bill_no, due_amt))
                if due_amt <= 0:
                    btn.configure(state="disabled", fg_color="#E5E7EB", text_color="#9CA3AF")
                btn.grid(row=0, column=i, sticky="ew", padx=4)
            elif k=="spacer":
                pass
            else:
                if k=="status":
                    lbl = ctk.CTkLabel(row, text=str(values.get(k,"")), width=70, height=22, corner_radius=20, font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"))
                    style_status_label(lbl, values.get("status",""))
                    lbl.grid(row=0, column=i, sticky="ew", padx=4)
                else:
                    lbl = ctk.CTkLabel(row, text=str(values.get(k,"")), text_color=TEXT, anchor=cell_anchor, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
                    lbl.grid(row=0, column=i, sticky="ew", padx=4)

    def _update_payment(self, bill_id: int, bill_number: str, due_amount: float):
        PaymentForm(self, bill_id=bill_id, bill_number=bill_number, due_amount=due_amount, on_saved=self.refresh)


class CustomerForm(ctk.CTkToplevel):
    def __init__(self, master, title: str, on_save, initial=None):
        super().__init__(master)
        self.title(title)
        self.geometry("620x480")
        self.resizable(False, False)
        self.on_save = on_save
        self.initial = initial or {}
        self.transient(master)
        self.grab_set()
        container = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        container.pack(expand=True, fill="both", padx=16, pady=16)
        ctk.CTkLabel(container, text=title, text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold")).pack(anchor="w", padx=18, pady=(18,12))
        form = ctk.CTkFrame(container, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=18, pady=(0,10))
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(form, text="Name *", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=0, column=0, sticky="w", pady=10)
        self.name = ctk.CTkEntry(form, placeholder_text="Full name", height=36, border_width=1, border_color=BORDER)
        self.name.grid(row=0, column=1, sticky="ew", padx=(10,0), pady=10)
        ctk.CTkLabel(form, text="Phone *", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=1, column=0, sticky="w", pady=10)
        self.phone = ctk.CTkEntry(form, placeholder_text="10 digits", height=36, border_width=1, border_color=BORDER)
        self.phone.grid(row=1, column=1, sticky="ew", padx=(10,0), pady=10)
        self.phone.bind("<KeyRelease>", lambda e: sanitize_phone_entry(self.phone))
        ctk.CTkLabel(form, text="Address", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=2, column=0, sticky="nw", pady=10)
        self.address = ctk.CTkTextbox(form, height=100, border_width=1, border_color=BORDER, corner_radius=10)
        self.address.grid(row=2, column=1, sticky="ew", padx=(10,0), pady=10)
        self.name.insert(0, self.initial.get("name",""))
        self.phone.insert(0, clean_phone(self.initial.get("phone","")))
        self.address.insert("1.0", self.initial.get("address","") or "")
        self.msg = ctk.CTkLabel(container, text="", text_color="#EF4444", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.msg.pack(anchor="w", padx=18, pady=(0,8))
        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=(0,18))
        ctk.CTkButton(btns, text="Cancel", fg_color="transparent", border_width=1, border_color=BORDER, text_color=TEXT, hover_color=BTN_SOFT_BG, corner_radius=8, command=self.destroy).pack(side="right", padx=(10,0))
        ctk.CTkButton(btns, text="✓ Save", fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold"), command=self._save).pack(side="right")

    def _save(self):
        name = self.name.get().strip()
        phone = clean_phone(self.phone.get().strip())
        address = self.address.get("1.0","end").strip()
        if not name or len(name)<2:
            self.msg.configure(text="Name must be at least 2 characters.")
            return
        if not is_valid_phone(phone):
            self.msg.configure(text="Phone must be exactly 10 digits.")
            return
        try:
            self.on_save(name, phone, address)
            self.destroy()
        except Exception as e:
            self.msg.configure(text=str(e))


class CustomersPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.selected_id = None
        self.selected_name = ""
        self.cols = [("id","ID",70,"center","center"),("name","Customer",240,"w","w"),("phone","Phone",140,"center","center"),("bill_count","Bills",70,"center","center"),("total_due","Due",110,"center","e"),("address","Address",1,"w","w"),("created","Added",110,"center","center")]

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0,16))
        header.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(left, text="Customers", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(left, text="Manage customer profiles and view billing history", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(anchor="w")
        self.count_label = ctk.CTkLabel(left, text="", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.count_label.pack(anchor="w", pady=(4,0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")
        self.search_entry = ctk.CTkEntry(right, width=260, height=36, placeholder_text="🔍 Search name / phone / address", border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.search_entry.pack(side="left", padx=(0,10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh())

        ctk.CTkButton(right, text="📄 View Bills", width=100, height=34, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), command=self.view_bills).pack(side="left", padx=(0,8))
        ctk.CTkButton(right, text="+ Add Customer", width=120, height=34, fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), command=self.add_customer).pack(side="left", padx=(0,8))
        self.new_customer_btn = right
        ctk.CTkButton(right, text="✎ Edit", width=70, height=34, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), command=self.edit_customer).pack(side="left", padx=(0,8))
        ctk.CTkButton(right, text="🗑", width=40, height=34, fg_color="#FEE2E2", text_color="#991B1B", hover_color="#FECACA", corner_radius=8, command=self.delete_customer).pack(side="left")

        table_card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        table_card.pack(fill="both", expand=True)

        header_row = ctk.CTkFrame(table_card, fg_color="#F8FAFC", corner_radius=12)
        header_row.pack(fill="x", padx=14, pady=(14,8))
        for i, (_k,_t,w,ha,ca) in enumerate(self.cols):
            if w==1:
                header_row.grid_columnconfigure(i, weight=1)
            else:
                header_row.grid_columnconfigure(i, weight=0, minsize=w)
        for i, (_k,title,_w,h_anchor,_ca) in enumerate(self.cols):
            ctk.CTkLabel(header_row, text=title, text_color=TEXT_MUTED, anchor=h_anchor, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")).grid(row=0, column=i, sticky="ew", padx=8, pady=10)

        ctk.CTkFrame(table_card, height=1, fg_color=BORDER).pack(fill="x", padx=14, pady=(0,8))
        self.rows_area = ctk.CTkScrollableFrame(table_card, fg_color="transparent")
        self.rows_area.pack(fill="both", expand=True, padx=8, pady=(0,10))
        self.refresh()

    def refresh(self):
        q = self.search_entry.get().strip()
        rows = search_customers(q, limit=100)
        for w in self.rows_area.winfo_children():
            w.destroy()
        self.count_label.configure(text=f"{len(rows)} customers • Click row to select • View Bills to see transactions")
        self.selected_id = None
        self.selected_name = ""
        if not rows:
            empty = ctk.CTkFrame(self.rows_area, fg_color="transparent")
            empty.pack(pady=60)
            ctk.CTkLabel(empty, text="👥", font=ctk.CTkFont(size=32)).pack()
            ctk.CTkLabel(empty, text="No customers found", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")).pack(pady=(8,2))
            ctk.CTkLabel(empty, text="Add your first customer to start billing", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack()
            return
        for r in rows:
            self._add_row(r)

    def _add_row(self, r):
        row_id = r["id"]
        rf = ctk.CTkFrame(self.rows_area, fg_color=ROW_BG, corner_radius=12, border_width=1, border_color=BORDER)
        rf.pack(fill="x", padx=8, pady=6)
        def select(_event=None):
            self.selected_id = row_id
            self.selected_name = r["name"] or ""
            self._highlight_selected()
        rf.bind("<Button-1>", select)
        row = ctk.CTkFrame(rf, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=10)
        for i, (_k,_t,w,ha,ca) in enumerate(self.cols):
            if w==1:
                row.grid_columnconfigure(i, weight=1)
            else:
                row.grid_columnconfigure(i, weight=0, minsize=w)
        total_due = float(r["total_due"] or 0) if "total_due" in r.keys() else 0
        values = {
            "id": str(r["id"]),
            "name": r["name"] or "",
            "phone": r["phone"] or "",
            "bill_count": str(r["bill_count"] or 0),
            "total_due": money(total_due) if total_due>0 else "-",
            "address": (r["address"] or "").replace("\n"," ").strip()[:60],
            "created": fmt_date(r["created_at"]),
        }
        for i, (k,_t,_w,ha,cell_anchor) in enumerate(self.cols):
            if k=="total_due" and total_due>0:
                lbl = ctk.CTkLabel(row, text=values.get(k,""), text_color="#DC2626", anchor=cell_anchor, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"))
            else:
                lbl = ctk.CTkLabel(row, text=values.get(k,""), text_color=TEXT, anchor=cell_anchor, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
            lbl.grid(row=0, column=i, sticky="ew", padx=8)
            lbl.bind("<Button-1>", select)
        rf._customer_id = row_id
        self._highlight_selected()

    def _highlight_selected(self):
        for rf in self.rows_area.winfo_children():
            cid = getattr(rf, "_customer_id", None)
            if cid == self.selected_id:
                rf.configure(fg_color=ROW_SELECTED_BG, border_color=PRIMARY)
            else:
                rf.configure(fg_color=ROW_BG, border_color=BORDER)

    def view_bills(self):
        if not self.selected_id:
            messagebox.showinfo("Customer Bills", "Please select a customer first — click on a row.")
            return
        CustomerBillsModal(self, self.selected_id, self.selected_name)

    def add_customer(self):
        def on_save(name, phone, address):
            create_customer(name, phone, address)
            self.refresh()
        CustomerForm(self, "Add New Customer", on_save=on_save)

    def edit_customer(self):
        if not self.selected_id:
            messagebox.showinfo("Edit Customer", "Please select a customer first.")
            return
        row = get_customer(self.selected_id)
        if not row:
            messagebox.showerror("Error", "Selected customer not found.")
            self.refresh()
            return
        initial = {"name": row["name"], "phone": row["phone"], "address": row["address"]}
        def on_save(name, phone, address):
            update_customer(self.selected_id, name, phone, address)
            self.refresh()
        CustomerForm(self, "Edit Customer", on_save=on_save, initial=initial)

    def delete_customer(self):
        if not self.selected_id:
            messagebox.showinfo("Delete Customer", "Please select a customer first.")
            return
        ok = messagebox.askyesno("Delete Customer", f"Delete customer '{self.selected_name}'?\n\nThis will only work if no bills exist for this customer.\nThis cannot be undone.", icon="warning")
        if not ok:
            return
        try:
            delete_customer(self.selected_id)
            self.selected_id = None
            self.refresh()
        except Exception as e:
            messagebox.showerror("Delete Failed", str(e))
