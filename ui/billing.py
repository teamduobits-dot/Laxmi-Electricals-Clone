import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
import platform
import os
import subprocess

from ui.autocomplete import SuggestionPopup
from database.lookups_repo import list_customers, list_services
from database.bills_repo import create_bill
from database.customers_repo import create_customer, get_customer
from database.services_repo import create_service
from utils.formatting import smart_title
from utils.validators import sanitize_phone_entry, clean_phone, is_valid_phone
from pdf.invoice_generator import generate_invoice_pdf
from ui.theme import SURFACE, BORDER, TEXT, TEXT_MUTED, ROW_BG, PRIMARY, PRIMARY_HOV, SUCCESS, SUCCESS_HOV, BTN_SOFT_BG, BTN_SOFT_TX, BTN_SOFT_HV, FONT_FAMILY


class CustomAddressForm(ctk.CTkToplevel):
    def __init__(self, master, initial_address: str, on_save):
        super().__init__(master)
        self.on_save = on_save
        self.title("Custom Bill Address")
        self.geometry("580x400")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        box = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        box.pack(expand=True, fill="both", padx=16, pady=16)
        box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(box, text="Custom Bill Address", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold")).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 6))
        ctk.CTkLabel(box, text="This address will appear only on this invoice (e.g., site/work location).", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), wraplength=500, justify="left").grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))

        self.addr = ctk.CTkTextbox(box, height=150, border_width=1, border_color=BORDER, corner_radius=10)
        self.addr.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        self.addr.insert("1.0", initial_address or "")

        self.msg = ctk.CTkLabel(box, text="", text_color="#EF4444", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.msg.grid(row=3, column=0, sticky="w", padx=18, pady=(0, 6))

        btns = ctk.CTkFrame(box, fg_color="transparent")
        btns.grid(row=4, column=0, sticky="e", padx=18, pady=(10, 18))
        ctk.CTkButton(btns, text="Cancel", fg_color="transparent", border_width=1, border_color=BORDER, text_color=TEXT, hover_color=BTN_SOFT_BG, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), command=self.destroy).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btns, text="Save Address", fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), command=self.save).pack(side="right")

    def save(self):
        address = self.addr.get("1.0", "end").strip()
        if not address:
            self.msg.configure(text="Address cannot be empty.")
            return
        if len(address) < 5:
            self.msg.configure(text="Address too short.")
            return
        self.on_save(address)
        self.destroy()


class QuickCustomerForm(ctk.CTkToplevel):
    def __init__(self, master, on_created):
        super().__init__(master)
        self.on_created = on_created
        self.title("Quick Add Customer")
        self.geometry("600x460")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        box = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        box.pack(expand=True, fill="both", padx=16, pady=16)
        box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(box, text="Quick Add Customer", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=17, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 14))
        ctk.CTkLabel(box, text="Name *", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=1, column=0, sticky="w", padx=18, pady=10)
        self.name = ctk.CTkEntry(box, placeholder_text="e.g. Rahul Sharma", height=36, border_width=1, border_color=BORDER)
        self.name.grid(row=1, column=1, sticky="ew", padx=18, pady=10)

        ctk.CTkLabel(box, text="Phone *", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=2, column=0, sticky="w", padx=18, pady=10)
        self.phone = ctk.CTkEntry(box, placeholder_text="10 digit phone", height=36, border_width=1, border_color=BORDER)
        self.phone.grid(row=2, column=1, sticky="ew", padx=18, pady=10)
        self.phone.bind("<KeyRelease>", lambda e: sanitize_phone_entry(self.phone))

        ctk.CTkLabel(box, text="Address", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=3, column=0, sticky="nw", padx=18, pady=10)
        self.addr = ctk.CTkTextbox(box, height=90, border_width=1, border_color=BORDER, corner_radius=10)
        self.addr.grid(row=3, column=1, sticky="ew", padx=18, pady=10)

        self.msg = ctk.CTkLabel(box, text="", text_color="#EF4444", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.msg.grid(row=4, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 8))

        btns = ctk.CTkFrame(box, fg_color="transparent")
        btns.grid(row=5, column=0, columnspan=2, sticky="e", padx=18, pady=(8, 18))
        ctk.CTkButton(btns, text="Cancel", fg_color="transparent", border_width=1, border_color=BORDER, text_color=TEXT, hover_color=BTN_SOFT_BG, corner_radius=8, command=self.destroy).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btns, text="Create & Select", fg_color=SUCCESS, hover_color=SUCCESS_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold"), command=self.save).pack(side="right")
        self.name.focus_set()
        self.name.bind("<Return>", lambda e: self.save())

    def save(self):
        try:
            name = self.name.get().strip()
            phone = clean_phone(self.phone.get().strip())
            address = self.addr.get("1.0", "end").strip()
            if not name:
                self.msg.configure(text="Name is required.")
                return
            if len(name) < 2:
                self.msg.configure(text="Name must be at least 2 characters.")
                return
            if not is_valid_phone(phone):
                self.msg.configure(text="Phone must be exactly 10 digits.")
                return
            new_id = create_customer(name, phone, address)
            self.on_created(new_id)
            self.destroy()
        except Exception as e:
            self.msg.configure(text=str(e))


class ServiceItemRow(ctk.CTkFrame):
    def __init__(self, master, idx: int, get_services, get_default_price, on_new_service, on_change, on_remove):
        super().__init__(master, fg_color=ROW_BG, corner_radius=12, border_width=1, border_color=BORDER)
        self.idx = idx
        self.get_services = get_services
        self.get_default_price = get_default_price
        self.on_new_service = on_new_service
        self.on_change = on_change
        self.on_remove = on_remove
        self.grid_columnconfigure(1, weight=1)

        self.sr = ctk.CTkLabel(self, text=f"{idx:02d}", width=36, text_color="#FFFFFF", fg_color=PRIMARY, corner_radius=6, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"))
        self.sr.grid(row=0, column=0, sticky="w", padx=(10, 0), pady=10)

        self.service_entry = ctk.CTkEntry(self, placeholder_text="Type service name...", height=34, border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.service_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

        self.qty = ctk.CTkEntry(self, width=70, height=34, placeholder_text="Qty", border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.qty.insert(0, "1")
        self.qty.grid(row=0, column=2, padx=(0, 10), pady=10)

        self.rate = ctk.CTkEntry(self, width=100, height=34, placeholder_text="Rate", border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.rate.insert(0, "0")
        self.rate.grid(row=0, column=3, padx=(0, 10), pady=10)

        self.amount_label = ctk.CTkLabel(self, text="₹0.00", width=100, text_color=TEXT, anchor="e", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"))
        self.amount_label.grid(row=0, column=4, padx=(0, 10), pady=10, sticky="e")

        self.remove_btn = ctk.CTkButton(self, text="✕", width=34, height=32, fg_color="#FEE2E2", text_color="#991B1B", hover_color="#FECACA", corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"), command=self.on_remove)
        self.remove_btn.grid(row=0, column=5, padx=(0, 10), pady=10)

        self.popup = SuggestionPopup(self.service_entry, on_select=self._select_service)
        self.service_entry.bind("<KeyRelease>", self._on_service_type)
        self.service_entry.bind("<Return>", self._on_service_enter)
        self.qty.bind("<KeyRelease>", lambda e: self.on_change())
        self.qty.bind("<FocusOut>", lambda e: self.on_change())
        self.rate.bind("<KeyRelease>", lambda e: self.on_change())
        self.rate.bind("<FocusOut>", lambda e: self.on_change())
        self.on_change()

    def set_index(self, idx: int):
        self.idx = idx
        self.sr.configure(text=f"{idx:02d}")

    def _on_service_type(self, _e=None):
        text = (self.service_entry.get() or "").strip().lower()
        if not text:
            self.popup.hide()
            return
        names = self.get_services()
        matches = [n for n in names if text in n.lower()]
        self.popup.show(matches[:12])

    def _select_service(self, name: str):
        self.service_entry.delete(0, "end")
        self.service_entry.insert(0, name)
        default_price = self.get_default_price(name)
        if default_price is not None and float(default_price) > 0:
            self.rate.delete(0, "end")
            self.rate.insert(0, str(float(default_price)))
        self.on_change()

    def _on_service_enter(self, _e=None):
        typed = smart_title(self.service_entry.get().strip())
        if not typed:
            return "break"
        names = self.get_services()
        exact = next((n for n in names if n.lower() == typed.lower()), None)
        if exact:
            self._select_service(exact)
            return "break"
        rate_text = self.rate.get().strip() or "0"
        try:
            rate_val = float(rate_text)
        except:
            rate_val = 0.0
        save_it = messagebox.askyesno("New Service", f"New service detected:\n\n{typed}\nRate: ₹{rate_val:.2f}\n\nSave to Services catalog?")
        if save_it:
            try:
                saved_name = self.on_new_service(typed, rate_val)
                self._select_service(saved_name)
            except Exception as e:
                messagebox.showerror("Save Failed", str(e))
        else:
            self.service_entry.delete(0, "end")
            self.service_entry.insert(0, typed)
            self.on_change()
        return "break"

    def get_item(self):
        service_name = smart_title(self.service_entry.get().strip())
        try:
            qty = float(self.qty.get().strip() or 0)
        except:
            qty = 0.0
        try:
            rate = float(self.rate.get().strip() or 0)
        except:
            rate = 0.0
        amount = qty * rate
        return {"service_name": service_name, "qty": qty, "rate": rate, "amount": amount}

    def update_amount_display(self):
        it = self.get_item()
        self.amount_label.configure(text=f"₹{it['amount']:,.2f}")


class BillingPage(ctk.CTkFrame):
    def __init__(self, master, navigate=None):
        super().__init__(master, fg_color="transparent")
        self.navigate = navigate
        self.customer_labels = []
        self.customer_id_by_label = {}
        self.selected_customer_id = None
        self.selected_customer_label = None
        self.default_customer_address = ""
        self.bill_address_override = ""
        self.services = []
        self.service_names = []
        self.service_price_by_name_lower = {}
        self.item_rows = []

        # Top bar
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", pady=(0, 14))
        top.grid_columnconfigure(0, weight=1)

        title_box = ctk.CTkFrame(top, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(title_box, text="Create New Bill", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold")).pack(side="left", padx=(0, 16))
        # Date with label
        date_frame = ctk.CTkFrame(title_box, fg_color=SURFACE, corner_radius=10, border_width=1, border_color=BORDER)
        date_frame.pack(side="left")
        ctk.CTkLabel(date_frame, text="📅 Date:", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(side="left", padx=(10,4), pady=6)
        self.date_entry = ctk.CTkEntry(date_frame, width=110, height=28, placeholder_text="DD-MM-YYYY", border_width=0, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.date_entry.pack(side="left", padx=(0,10), pady=6)
        self.date_entry.insert(0, datetime.now().strftime("%d-%m-%Y"))

        ctk.CTkButton(top, text="↻ Refresh", width=90, height=32, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), command=self.load_lookups).grid(row=0, column=1, sticky="e")

        # Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.grid_rowconfigure(5, weight=1)

        # Customer section header
        sec_head = ctk.CTkFrame(left, fg_color="transparent")
        sec_head.pack(fill="x", padx=18, pady=(18, 10))
        ctk.CTkLabel(sec_head, text="Customer Details", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(side="left")
        ctk.CTkLabel(sec_head, text="Search existing customer or add new", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(side="left", padx=(12,0))

        # Customer search row
        cust = ctk.CTkFrame(left, fg_color="transparent")
        cust.pack(fill="x", padx=18, pady=(0, 10))
        cust.grid_columnconfigure(0, weight=1)

        self.customer_entry = ctk.CTkEntry(cust, placeholder_text="🔍 Search customer by name or phone...", height=42, border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.customer_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.customer_popup = SuggestionPopup(self.customer_entry, on_select=self.select_customer)
        self.customer_entry.bind("<KeyRelease>", self.on_customer_type)
        self.customer_entry.bind("<Return>", self.on_customer_enter)

        ctk.CTkButton(cust, text="+ New Customer", width=130, height=42, fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=10, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), command=self.quick_add_customer).grid(row=0, column=1, sticky="e")

        # Pinned card
        self.pinned_card = ctk.CTkFrame(left, fg_color=("#EEF2FF", "#1E293B"), corner_radius=12, border_width=1, border_color=("#C7D2FE", "#334155"))
        self.pinned_card.pack(fill="x", padx=18, pady=(0, 10))
        self.pinned_card.grid_columnconfigure(0, weight=1)

        self.pinned_label = ctk.CTkLabel(self.pinned_card, text="No customer selected — search above or create new", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), anchor="w")
        self.pinned_label.grid(row=0, column=0, sticky="ew", padx=14, pady=12)

        btns = ctk.CTkFrame(self.pinned_card, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e", padx=10, pady=10)
        self.custom_addr_btn = ctk.CTkButton(btns, text="📍 Site Address", width=118, height=30, fg_color=SURFACE, text_color=TEXT, border_width=1, border_color=BORDER, hover_color=BTN_SOFT_BG, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), command=self.custom_address)
        self.custom_addr_btn.pack(side="left", padx=(0, 8))
        self.custom_addr_btn.configure(state="disabled")
        self.change_btn = ctk.CTkButton(btns, text="Change", width=70, height=30, fg_color=SURFACE, text_color=TEXT, border_width=1, border_color=BORDER, hover_color=BTN_SOFT_BG, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), command=self.clear_customer)
        self.change_btn.pack(side="left")
        self.change_btn.configure(state="disabled")

        self.addr_preview = ctk.CTkLabel(left, text="", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), justify="left", anchor="w")
        self.addr_preview.pack(fill="x", padx=18, pady=(0, 12))

        # Items header
        items_header = ctk.CTkFrame(left, fg_color="transparent")
        items_header.pack(fill="x", padx=18, pady=(6, 8))
        ctk.CTkLabel(items_header, text="Service Items", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(items_header, text="+ Add Item", width=100, height=32, fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), command=self.add_item).pack(side="right")

        headings = ctk.CTkFrame(left, fg_color=("#F8FAFC", "#1E293B"), corner_radius=8)
        headings.pack(fill="x", padx=18, pady=(0, 8))
        labels = [("No", 50), ("Service Description", 1), ("Qty", 80), ("Rate", 110), ("Amount", 110), ("", 50)]
        for i, (t, w) in enumerate(labels):
            if w == 1:
                headings.grid_columnconfigure(i, weight=1)
            else:
                headings.grid_columnconfigure(i, minsize=w)
            ctk.CTkLabel(headings, text=t, text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")).grid(row=0, column=i, sticky="w", padx=(10 if i==0 else 8), pady=10)

        ctk.CTkFrame(left, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(0, 8))
        self.items_area = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.items_area.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Right summary card - premium
        right = ctk.CTkFrame(body, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        right.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(right, text="Bill Summary", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold")).pack(anchor="w", padx=18, pady=(18, 12))

        self.subtotal_label = ctk.CTkLabel(right, text="Subtotal: ₹0.00", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), anchor="w")
        self.subtotal_label.pack(anchor="w", padx=18, pady=6)

        # Input groups with modern look
        def summary_row(parent, label):
            row = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=10)
            row.pack(fill="x", padx=12, pady=5)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=label, text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=0, column=0, sticky="w", padx=12, pady=10)
            entry = ctk.CTkEntry(row, width=110, height=32, border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), justify="right")
            entry.grid(row=0, column=1, sticky="e", padx=10, pady=6)
            return entry

        self.discount_entry = summary_row(right, "Discount (₹)")
        self.discount_entry.insert(0, "0")
        self.discount_entry.bind("<KeyRelease>", lambda e: self.recalculate())
        self.discount_entry.bind("<FocusOut>", lambda e: self.recalculate())

        self.gst_entry = summary_row(right, "GST (%)")
        self.gst_entry.insert(0, "0")
        self.gst_entry.bind("<KeyRelease>", lambda e: self.recalculate())
        self.gst_entry.bind("<FocusOut>", lambda e: self.recalculate())

        self.advance_check = ctk.CTkCheckBox(right, text="Use Advance", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), onvalue=True, offvalue=False)
        self.advance_check.pack(anchor="w", padx=12, pady=(0,4))
        self.advance_entry = summary_row(right, "Advance (₹)")
        self.advance_check.select()  # default unchecked
        def toggle_advance():
            if self.advance_check.get():
                self.advance_entry.configure(state="normal")
            else:
                self.advance_entry.configure(state="disabled")
                self.advance_entry.delete(0, "end")
                self.advance_entry.insert(0, "0")
                self.recalculate()
        self.advance_check.configure(command=toggle_advance)
        toggle_advance()
        self.advance_entry.insert(0, "0")
        self.advance_entry.bind("<KeyRelease>", lambda e: self.recalculate())
        self.advance_entry.bind("<FocusOut>", lambda e: self.recalculate())

        pm_row = ctk.CTkFrame(right, fg_color="#F8FAFC", corner_radius=10)
        pm_row.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(pm_row, text="Payment Mode", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(side="left", padx=12, pady=10)
        self.payment_var = ctk.StringVar(value="Cash")
        self.payment_menu = ctk.CTkOptionMenu(pm_row, values=["Cash", "UPI", "Bank Transfer"], variable=self.payment_var, width=120, height=28, fg_color=SURFACE, text_color=TEXT, button_color=PRIMARY, button_hover_color=PRIMARY_HOV, dropdown_fg_color=SURFACE, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.payment_menu.pack(side="right", padx=10, pady=6)

        # Calculation preview box
        self.calc_box = ctk.CTkFrame(right, fg_color=("#EFF6FF", "#0F172A"), corner_radius=12, border_width=1, border_color=("#BFDBFE", "#1E3A5F"))
        self.calc_box.pack(fill="x", padx=12, pady=(12, 12))

        self.due_label = ctk.CTkLabel(self.calc_box, text="Due: ₹0.00", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), anchor="w")
        self.due_label.pack(anchor="w", padx=14, pady=(12,4))
        self.total_label = ctk.CTkLabel(self.calc_box, text="Total: ₹0.00", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), anchor="w")
        self.total_label.pack(anchor="w", padx=14, pady=(0,2))
        self.status_label = ctk.CTkLabel(self.calc_box, text="Status: Due", text_color="#FFFFFF", fg_color="#F97316", corner_radius=20, width=100, height=24, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), anchor="center")
        self.status_label.pack(anchor="w", padx=14, pady=(6,12))

        ctk.CTkButton(right, text="✓ Generate Bill & PDF", height=46, fg_color=SUCCESS, hover_color=SUCCESS_HOV, corner_radius=12, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), command=self.generate_bill).pack(fill="x", padx=12, pady=(0, 12))

        self.msg = ctk.CTkLabel(right, text="", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), justify="left", wraplength=220, anchor="w")
        self.msg.pack(anchor="w", padx=18, pady=(0, 18))

        self.load_lookups()
        self.add_item()

    def load_lookups(self):
        self.customer_labels = []
        self.customer_id_by_label = {}
        customers = [dict(r) for r in list_customers()]
        for c in customers:
            label = smart_title(c.get("name", ""))
            phone = (c.get("phone") or "").strip()
            if phone:
                label = f"{label} ({phone})"
            self.customer_labels.append(label)
            self.customer_id_by_label[label] = c["id"]

        self.services = [dict(r) for r in list_services()]
        self.service_names = [smart_title(s.get("service_name", "")) for s in self.services]
        self.service_price_by_name_lower = {
            smart_title(s.get("service_name", "")).lower(): float(s.get("default_price") or 0)
            for s in self.services
        }

    def on_customer_type(self, _e=None):
        if self.selected_customer_id:
            return
        text = (self.customer_entry.get() or "").strip().lower()
        if not text:
            self.customer_popup.hide()
            return
        matches = [lbl for lbl in self.customer_labels if text in lbl.lower()]
        self.customer_popup.show(matches[:12])

    def on_customer_enter(self, _e=None):
        if self.selected_customer_id:
            return "break"
        typed = (self.customer_entry.get() or "").strip().lower()
        if not typed:
            return "break"
        exact = next((lbl for lbl in self.customer_labels if lbl.lower() == typed), None)
        if exact:
            self.select_customer(exact)
            return "break"
        matches = [lbl for lbl in self.customer_labels if typed in lbl.lower()]
        if len(matches) == 1:
            self.select_customer(matches[0])
        return "break"

    def select_customer(self, label: str):
        cid = self.customer_id_by_label.get(label)
        if not cid:
            return
        self.selected_customer_id = cid
        self.selected_customer_label = label
        row = get_customer(cid)
        self.default_customer_address = (row["address"] if row else "") or ""
        self.bill_address_override = ""
        self.customer_entry.delete(0, "end")
        self.customer_entry.insert(0, label)
        self.customer_entry.configure(state="disabled")
        self.pinned_label.configure(text=f"✓ {label}")
        self.pinned_card.configure(fg_color=("#DCFCE7", "#064E3B"), border_color=("#86EFAC", "#166534"))
        self.pinned_label.configure(text_color=("#166534", "#BBF7D0"))
        self.custom_addr_btn.configure(state="normal")
        self.change_btn.configure(state="normal")
        self._refresh_address_preview()

    def clear_customer(self):
        self.selected_customer_id = None
        self.selected_customer_label = None
        self.default_customer_address = ""
        self.bill_address_override = ""
        self.customer_entry.configure(state="normal")
        self.customer_entry.delete(0, "end")
        self.customer_entry.focus_set()
        self.pinned_label.configure(text="No customer selected — search above or create new")
        self.pinned_card.configure(fg_color=("#EEF2FF", "#1E293B"), border_color=("#C7D2FE", "#334155"))
        self.pinned_label.configure(text_color=TEXT_MUTED)
        self.addr_preview.configure(text="")
        self.custom_addr_btn.configure(state="disabled")
        self.change_btn.configure(state="disabled")

    def _refresh_address_preview(self):
        addr = self.bill_address_override.strip() or self.default_customer_address.strip()
        if not addr:
            self.addr_preview.configure(text="📍 Bill Address: Not set")
            return
        short = addr.replace("\n", " • ")
        if len(short) > 110:
            short = short[:110] + "..."
        tag = "Custom Site" if self.bill_address_override.strip() else "Customer Address"
        self.addr_preview.configure(text=f"📍 {tag}: {short}")

    def custom_address(self):
        if not self.selected_customer_id:
            return
        initial = self.bill_address_override.strip() or self.default_customer_address.strip()
        def on_save(addr: str):
            self.bill_address_override = addr
            self._refresh_address_preview()
        CustomAddressForm(self, initial, on_save=on_save)

    def quick_add_customer(self):
        def on_created(new_id: int):
            self.load_lookups()
            for lbl, cid in self.customer_id_by_label.items():
                if cid == new_id:
                    self.select_customer(lbl)
                    break
        QuickCustomerForm(self, on_created=on_created)

    def get_service_names(self):
        return self.service_names

    def get_default_price(self, service_name: str):
        return self.service_price_by_name_lower.get((service_name or "").strip().lower())

    def handle_new_service(self, service_name: str, default_price: float):
        create_service(service_name, float(default_price or 0))
        self.load_lookups()
        return smart_title(service_name)

    def add_item(self):
        idx = len(self.item_rows) + 1
        def remove_row(row_ref):
            if len(self.item_rows) <= 1:
                messagebox.showwarning("Items", "At least one item is required.")
                return
            row_ref.destroy()
            self.item_rows.remove(row_ref)
            for i, r in enumerate(self.item_rows, start=1):
                r.set_index(i)
            self.recalculate()
        row = ServiceItemRow(
            self.items_area,
            idx=idx,
            get_services=self.get_service_names,
            get_default_price=self.get_default_price,
            on_new_service=self.handle_new_service,
            on_change=self.recalculate,
            on_remove=lambda: remove_row(row)
        )
        row.pack(fill="x", padx=8, pady=6)
        self.item_rows.append(row)
        self.recalculate()

    def recalculate(self):
        subtotal = 0.0
        for r in self.item_rows:
            r.update_amount_display()
            try:
                subtotal += r.get_item()["amount"]
            except:
                pass

        try:
            discount = float(self.discount_entry.get().strip() or 0)
        except:
            discount = 0.0
        try:
            gst_percent = float(self.gst_entry.get().strip() or 0)
        except:
            gst_percent = 0.0

        # Validation visual feedback
        if discount < 0:
            discount = 0.0
        if gst_percent < 0:
            gst_percent = 0.0
        if discount > subtotal and subtotal > 0:
            self.discount_entry.configure(border_color="#EF4444")
        else:
            self.discount_entry.configure(border_color=BORDER)

        taxable = subtotal - discount
        if taxable < 0:
            taxable = 0

        tax_amount = (taxable * gst_percent) / 100.0
        total = taxable + tax_amount

        try:
            advance = float(self.advance_entry.get().strip() or 0)
        except:
            advance = 0.0
        if advance < 0:
            advance = 0.0
        if advance > total and total>0:
            self.advance_entry.configure(border_color="#EF4444")
        else:
            self.advance_entry.configure(border_color=BORDER)

        due = total - advance
        if due < 0:
            due = 0.0

        if advance <= 0:
            status = "Due"
            status_color = "#F97316"
        elif advance >= total and total > 0:
            status = "Paid"
            status_color = "#16A34A"
        else:
            status = "Partial"
            status_color = "#EAB308"

        self.subtotal_label.configure(text=f"Subtotal: ₹{subtotal:,.2f}")
        self.total_label.configure(text=f"Total (incl. GST): ₹{total:,.2f} | Taxable: ₹{taxable:,.2f} | GST: ₹{tax_amount:,.2f}")
        self.due_label.configure(text=f"Balance Due: ₹{due:,.2f}")
        self.status_label.configure(text=f"● {status}", fg_color=status_color)

    def generate_bill(self):
        if not self.selected_customer_id:
            messagebox.showinfo("Create Bill", "Please select a customer first.\nSearch or add new customer.")
            self.customer_entry.focus_set()
            return
        if not self.item_rows:
            messagebox.showinfo("Create Bill", "Please add at least one service item.")
            return

        # Validate items
        for i, r in enumerate(self.item_rows, start=1):
            it = r.get_item()
            if not it["service_name"]:
                messagebox.showerror("Validation", f"Row {i}: Service name cannot be empty.")
                return
            if it["qty"] <= 0:
                messagebox.showerror("Validation", f"Row {i}: Qty must be > 0.")
                return
            if it["rate"] < 0:
                messagebox.showerror("Validation", f"Row {i}: Rate cannot be negative.")
                return

        date_str = self.date_entry.get().strip()
        custom_iso_date = None
        if date_str:
            try:
                dt = datetime.strptime(date_str, "%d-%m-%Y")
                now_time = datetime.now().time()
                dt_combined = datetime.combine(dt.date(), now_time)
                custom_iso_date = dt_combined.isoformat(timespec="seconds")
            except ValueError:
                messagebox.showerror("Invalid Date", "Date must be in DD-MM-YYYY format.\nExample: 07-08-2026")
                return

        items = []
        for r in self.item_rows:
            it = r.get_item()
            items.append({"service_name": it["service_name"], "qty": it["qty"], "rate": it["rate"]})

        advance_text = self.advance_entry.get().strip() or "0"
        discount_text = self.discount_entry.get().strip() or "0"
        gst_text = self.gst_entry.get().strip() or "0"
        payment_mode = self.payment_var.get()
        bill_address = self.bill_address_override.strip() or self.default_customer_address.strip()

        try:
            bill_id, bill_number = create_bill(
                self.selected_customer_id,
                items,
                float(advance_text),
                payment_mode,
                bill_address=bill_address,
                custom_date=custom_iso_date,
                tax_percent=float(gst_text),
                discount_amount=float(discount_text)
            )
        except Exception as e:
            messagebox.showerror("Bill Failed", str(e))
            return

        try:
            pdf_path = generate_invoice_pdf(bill_id)
        except Exception as e:
            messagebox.showerror("PDF Failed", f"Bill saved ({bill_number}), but PDF failed:\n{e}")
            return

        self.msg.configure(text=f"✓ Saved: {bill_number}\n📄 {pdf_path[-60:]}")
        # Open PDF automatically?
        try:
            if platform.system() == "Windows":
                os.startfile(pdf_path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", pdf_path])
            else:
                subprocess.Popen(["xdg-open", pdf_path])
        except:
            pass

        messagebox.showinfo("Bill Saved", f"Bill saved successfully!\n\nBill No: {bill_number}\nCustomer: {self.selected_customer_label}\n\nPDF opened automatically.\n\nPath:\n{pdf_path}")

        for r in self.item_rows:
            r.destroy()
        self.item_rows = []
        self.advance_entry.delete(0, "end")
        self.advance_entry.insert(0, "0")
        self.discount_entry.delete(0, "end")
        self.discount_entry.insert(0, "0")
        self.gst_entry.delete(0, "end")
        self.gst_entry.insert(0, "0")
        self.add_item()
        self.recalculate()
