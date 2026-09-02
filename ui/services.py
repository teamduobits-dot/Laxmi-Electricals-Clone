import customtkinter as ctk
from tkinter import messagebox
from utils.date_utils import fmt_date
from database.services_repo import create_service, update_service, delete_service, get_service, search_services, service_usage_count
from ui.theme import SURFACE, BORDER, TEXT, TEXT_MUTED, ROW_BG, ROW_SELECTED_BG, BTN_SOFT_BG, BTN_SOFT_TX, BTN_SOFT_HV, PRIMARY, PRIMARY_HOV, FONT_FAMILY


class ServiceForm(ctk.CTkToplevel):
    def __init__(self, master, title: str, on_save, initial=None):
        super().__init__(master)
        self.title(title)
        self.geometry("520x360")
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
        ctk.CTkLabel(form, text="Service Name *", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=0, column=0, sticky="w", pady=10)
        self.service_name = ctk.CTkEntry(form, placeholder_text="e.g. Fan fitting, Wiring", height=36, border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.service_name.grid(row=0, column=1, sticky="ew", padx=(10,0), pady=10)
        ctk.CTkLabel(form, text="Default Price ₹", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).grid(row=1, column=0, sticky="w", pady=10)
        self.default_price = ctk.CTkEntry(form, placeholder_text="e.g. 250", height=36, border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.default_price.grid(row=1, column=1, sticky="ew", padx=(10,0), pady=10)
        self.service_name.insert(0, self.initial.get("service_name","") or "")
        self.default_price.insert(0, str(self.initial.get("default_price","") or ""))
        self.msg = ctk.CTkLabel(container, text="", text_color="#EF4444", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.msg.pack(anchor="w", padx=18, pady=(0,8))
        btns = ctk.CTkFrame(container, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=(0,18))
        ctk.CTkButton(btns, text="Cancel", fg_color="transparent", border_width=1, border_color=BORDER, text_color=TEXT, hover_color=BTN_SOFT_BG, corner_radius=8, command=self.destroy).pack(side="right", padx=(10,0))
        ctk.CTkButton(btns, text="✓ Save Service", fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, weight="bold"), command=self._save).pack(side="right")
        self.service_name.focus_set()
        self.service_name.bind("<Return>", lambda e: self._save())
        self.default_price.bind("<Return>", lambda e: self._save())

    def _save(self):
        name = self.service_name.get().strip()
        price_text = self.default_price.get().strip()
        if not name:
            self.msg.configure(text="Service name is required.")
            return
        if len(name)<2:
            self.msg.configure(text="Name must be at least 2 characters.")
            return
        if price_text == "":
            price_text = "0"
        try:
            self.on_save(name, float(price_text))
            self.destroy()
        except Exception as e:
            self.msg.configure(text=str(e))


class ServicesPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.selected_id = None

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0,16))
        header.grid_columnconfigure(0, weight=1)
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(left, text="Services Catalog", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(left, text="Manage your service list and default pricing", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack(anchor="w")
        self.count_label = ctk.CTkLabel(left, text="", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.count_label.pack(anchor="w", pady=(4,0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")
        self.search_entry = ctk.CTkEntry(right, width=260, height=36, placeholder_text="🔍 Search service...", border_width=1, border_color=BORDER, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"))
        self.search_entry.pack(side="left", padx=(0,10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh())
        ctk.CTkButton(right, text="+ Add Service", width=120, height=34, fg_color=PRIMARY, hover_color=PRIMARY_HOV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), command=self.add_service).pack(side="left", padx=(0,8))
        ctk.CTkButton(right, text="✎ Edit", width=70, height=34, fg_color=BTN_SOFT_BG, text_color=BTN_SOFT_TX, hover_color=BTN_SOFT_HV, corner_radius=8, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), command=self.edit_service).pack(side="left", padx=(0,8))
        ctk.CTkButton(right, text="🗑", width=40, height=34, fg_color="#FEE2E2", text_color="#991B1B", hover_color="#FECACA", corner_radius=8, command=self.delete_service).pack(side="left")

        table_card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        table_card.pack(fill="both", expand=True)

        header_row = ctk.CTkFrame(table_card, fg_color="#F8FAFC", corner_radius=12)
        header_row.pack(fill="x", padx=14, pady=(14,8))
        cols = ["ID", "Service Name", "Default Price", "Usage", "Created"]
        widths = [60, 380, 140, 80, 140]
        for i, (c,w) in enumerate(zip(cols, widths)):
            header_row.grid_columnconfigure(i, minsize=w)
            ctk.CTkLabel(header_row, text=c, text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")).grid(row=0, column=i, sticky="w", padx=8, pady=10)

        ctk.CTkFrame(table_card, height=1, fg_color=BORDER).pack(fill="x", padx=14, pady=(0,8))
        self.rows_area = ctk.CTkScrollableFrame(table_card, fg_color="transparent")
        self.rows_area.pack(fill="both", expand=True, padx=8, pady=(0,10))
        self.refresh()

    def refresh(self):
        query = self.search_entry.get().strip()
        rows = search_services(query)
        for w in self.rows_area.winfo_children():
            w.destroy()
        self.count_label.configure(text=f"{len(rows)} services • Click to select")
        if not rows:
            empty = ctk.CTkFrame(self.rows_area, fg_color="transparent")
            empty.pack(pady=60)
            ctk.CTkLabel(empty, text="🛠", font=ctk.CTkFont(size=32)).pack()
            ctk.CTkLabel(empty, text="No services found", text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold")).pack(pady=(8,2))
            ctk.CTkLabel(empty, text="Add your first service to use in billing", text_color=TEXT_MUTED, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")).pack()
            self.selected_id = None
            return
        for r in rows:
            self._add_row(r)

    def _add_row(self, r):
        row_id = r["id"]
        rf = ctk.CTkFrame(self.rows_area, fg_color=ROW_BG, corner_radius=12, border_width=1, border_color=BORDER)
        rf.pack(fill="x", padx=8, pady=6)
        def select(_event=None):
            self.selected_id = row_id
            self._highlight_selected()
        rf.bind("<Button-1>", select)
        usage = service_usage_count(row_id) if hasattr(r, '__getitem__') else 0
        values = [str(r["id"]), r["service_name"] or "", f'₹{float(r["default_price"] or 0):,.2f}', f"{usage} bills", fmt_date(r["created_at"])]
        widths = [60, 380, 140, 80, 140]
        row_inner = ctk.CTkFrame(rf, fg_color="transparent")
        row_inner.pack(fill="x", padx=12, pady=11)
        for i, (val,w) in enumerate(zip(values, widths)):
            lbl = ctk.CTkLabel(row_inner, text=val, text_color=TEXT, font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), anchor="w")
            if i==1:
                lbl.configure(font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"))
            lbl.grid(row=0, column=i, sticky="w", padx=4)
            row_inner.grid_columnconfigure(i, minsize=w)
            lbl.bind("<Button-1>", select)
        rf._service_id = row_id
        self._highlight_selected()

    def _highlight_selected(self):
        for rf in self.rows_area.winfo_children():
            sid = getattr(rf, "_service_id", None)
            if sid == self.selected_id:
                rf.configure(fg_color=ROW_SELECTED_BG, border_color=PRIMARY)
            else:
                rf.configure(fg_color=ROW_BG, border_color=BORDER)

    def add_service(self):
        def on_save(name, price):
            create_service(name, price)
            self.refresh()
        ServiceForm(self, "Add New Service", on_save=on_save)

    def edit_service(self):
        if not self.selected_id:
            messagebox.showinfo("Edit Service", "Please select a service first — click a row.")
            return
        row = get_service(self.selected_id)
        if not row:
            messagebox.showerror("Error", "Selected service not found.")
            self.refresh()
            return
        initial = {"service_name": row["service_name"], "default_price": row["default_price"]}
        def on_save(name, price):
            update_service(self.selected_id, name, price)
            self.refresh()
        ServiceForm(self, "Edit Service", on_save=on_save, initial=initial)

    def delete_service(self):
        if not self.selected_id:
            messagebox.showinfo("Delete Service", "Please select a service first.")
            return
        usage = service_usage_count(self.selected_id)
        warn = f"\n\n⚠ This service was used in {usage} bill items. Deleting won't affect past bills (service name is preserved in bill history)." if usage>0 else ""
        ok = messagebox.askyesno("Delete Service", f"Delete this service?{warn}\n\nThis cannot be undone.", icon="warning")
        if not ok:
            return
        delete_service(self.selected_id)
        self.selected_id = None
        self.refresh()
