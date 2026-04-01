import customtkinter as ctk
import requests
import json
import threading
import pandas as pd
import os
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, Menu

# --- CONFIGURATION ---
DB_BASE_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app/tasks"
SETTINGS_URL = "https://office-task-ledger-default-rtdb.asia-southeast1.firebasedatabase.app/settings.json"
DB_URL = f"{DB_BASE_URL}.json"

# --- SECURE PASSWORDS ---
STAFF_PASSWORD = "1234"
ADMIN_PASSWORD = "1586"

class TaskApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Report Correction Ledger Pro")
        self.geometry("1400x850")
        ctk.set_appearance_mode("dark")
        
        # --- MIDNIGHT COLOR PALETTE ---
        self.bg_color = "#000000"
        self.card_bg = "#0A0A0A"
        self.card_border = "#1A1A1A"
        self.accent_blue = "#3E91D4"
        self.success_green = "#1B5E20"
        self.danger_red = "#B71C1C"
        self.hold_pink = "#880E4F"
        self.pending_gold = "#C29100"
        self.text_main = "#E0E0E0"
        self.text_dim = "#808080" 
        
        self.configure(fg_color=self.bg_color)
        
        self.main_font = "Cambria"
        self.tasks_dict = {}  
        self.task_inputs = {} 
        self.priorities = ["Normal", "Medium", "High"]
        self.sort_by_priority = False 
        self.pending_filter_active = False 
        self.all_finance_names = []
        
        self.hidden_finances = set()
        self.renamed_finances = {}
        self.global_card_height = 50  
        self.is_resizing = False 
        self.is_fetching = False

        identity = self.get_user_identity()
        if identity:
            self.username, self.designation, self.role = identity
            self.setup_main_ui()
            self.start_sync_thread()
        else:
            self.show_login_screen()

    def format_date_to_alpha(self, date_str):
        if not date_str: return ""
        try:
            dt = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
            return dt.strftime("%d/%b/%Y %H:%M:%S")
        except:
            return date_str

    def show_toast(self, task_data):
        toast = ctk.CTkToplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(fg_color="#121212")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        toast.geometry(f"450x220+{sw-470}+{sh-280}")
        ctk.CTkLabel(toast, text="🔔 NEW INCOMING TASK", font=(self.main_font, 12, "bold"), text_color=self.accent_blue).pack(pady=(12, 2))
        assigner = task_data.get('assigner', 'UNKNOWN')
        finance = task_data.get('finance', 'N/A').upper()
        details = task_data.get('task', '')
        ctk.CTkLabel(toast, text=f"FROM: {assigner}", font=(self.main_font, 13, "bold"), text_color="#FFFFFF").pack()
        ctk.CTkLabel(toast, text=f"FINANCE: {finance}", font=(self.main_font, 12, "bold"), text_color=self.pending_gold).pack(pady=2)
        t_msg = ctk.CTkTextbox(toast, font=(self.main_font, 12), fg_color="#000000", height=80, width=410, wrap="word", border_width=1, border_color="#222222")
        t_msg.pack(pady=10, padx=10)
        t_msg.insert("0.0", details)
        t_msg.configure(state="disabled")
        ctk.CTkFrame(toast, height=4, fg_color=self.accent_blue).pack(side="bottom", fill="x")
        toast.after(6000, toast.destroy)

    def refresh_ui(self):
        if self.is_resizing: return 
        for w in self.scroll_frame.winfo_children(): w.destroy()
        self.task_inputs = {}
        query = self.search_entry.get().lower()
        selected_fin = self.nav_fin_filter.get()
        keys = sorted(self.tasks_dict.keys(), key=lambda k: ({"High":3,"Medium":2,"Normal":1}.get(self.tasks_dict[k].get('priority'),1) if self.sort_by_priority else k), reverse=True)
        
        for tid in keys:
            task = self.tasks_dict[tid]
            status, f_raw, t_text = task.get('status', 'Pending'), task.get('finance', '').upper(), task.get('task', '')
            display_fin = self.renamed_finances.get(f_raw, f_raw)
            if display_fin in self.hidden_finances: continue
            if self.pending_filter_active and status != "Pending": continue
            if selected_fin != "--- ALL FINANCES ---" and display_fin != selected_fin: continue
            if query and query not in f"{display_fin.lower()} {t_text.lower()} {task.get('assigner','').lower()}": continue
            
            lines = t_text.count('\n') + (len(t_text) // 110) + 1
            needed_h = (lines * 22) + 60 
            final_h = max(self.global_card_height, needed_h)
            
            accent = {"Pending": self.pending_gold, "Completed": self.success_green, "Hold": self.hold_pink}.get(status, self.pending_gold)
            card = ctk.CTkFrame(self.scroll_frame, height=final_h, corner_radius=12, fg_color=self.card_bg, border_width=1, border_color=self.card_border)
            card.pack(pady=2, fill="x", padx=5); card.pack_propagate(False)
            ctk.CTkFrame(card, width=4, fg_color=accent).pack(side="left", fill="y")
            
            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", padx=12, pady=1, expand=True, fill="both")
            
            alpha_date = self.format_date_to_alpha(task.get('assigned_at', ''))
            p_color = self.danger_red if task.get('priority') == "High" else self.accent_blue
            ctk.CTkLabel(info, text=f"[{task.get('priority','').upper()}] {display_fin} • {task.get('assigner')} • {alpha_date}", font=(self.main_font, 11, "bold"), text_color=p_color, anchor="w").pack(fill="x")
            
            t_box = ctk.CTkTextbox(info, font=(self.main_font, 14), fg_color="transparent", text_color=self.text_main, wrap="word", activate_scrollbars=False, height=10)
            t_box.pack(fill="both", expand=True, pady=0); t_box.insert("0.0", t_text); t_box.configure(state="disabled")
            
            # FIXED STATUS LABEL LOGIC
            if status != "Pending":
                f_date = self.format_date_to_alpha(task.get('finished_at', ''))
                # Shows "HOLD" if status is Hold, otherwise shows "COMPLETED"
                status_label = status.upper()
                meta = f"✓ {status_label} | {task.get('completed_by')} | {f_date} | {task.get('comment','')}"
                ctk.CTkLabel(info, text=meta, font=(self.main_font, 10, "italic"), text_color=self.text_dim, anchor="w").pack(fill="x")
            
            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.pack(side="right", padx=8)
            if status != "Completed":
                cmt = ctk.CTkEntry(actions, placeholder_text="Note...", width=100, height=26); cmt.pack(side="left", padx=3); self.task_inputs[tid] = cmt
                ctk.CTkButton(actions, text="Completed", width=70, height=26, fg_color=self.success_green, command=lambda x=tid: self.update_status(x, "Completed")).pack(side="left", padx=2)
                ctk.CTkButton(actions, text="Hold" if status=="Pending" else "Unhold", width=55, height=28, fg_color=self.hold_pink, command=lambda x=tid, s=status: self.update_status(x, "Hold" if s=="Pending" else "Pending")).pack(side="left", padx=2)
                if self.role == "ADMIN" or task.get('assigner') == self.username: 
                    ctk.CTkButton(actions, text="×", width=26, height=26, fg_color="#111111", hover_color=self.danger_red, command=lambda x=tid: self.delete_task(x)).pack(side="left", padx=3)
            
            h = ctk.CTkFrame(card, height=4, fg_color="#111111", cursor="sb_v_double_arrow", corner_radius=0)
            h.pack(side="bottom", fill="x")
            h.bind("<Button-1>", self.start_global_resize); h.bind("<B1-Motion>", self.do_global_resize); h.bind("<ButtonRelease-1>", self.stop_global_resize)

    def get_user_identity(self):
        config_file = "user_config.txt"
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f: 
                    data = f.read().strip().split(",")
                    if len(data) == 3: return data[0], data[1], data[2]
            except: pass
        return None

    def show_login_screen(self):
        self.login_frame = ctk.CTkFrame(self, width=420, height=580, corner_radius=15, fg_color="#050505")
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(self.login_frame, text="OFFICE LEDGER", font=(self.main_font, 28, "bold"), text_color=self.accent_blue).pack(pady=(50, 5))
        self.user_entry = ctk.CTkEntry(self.login_frame, placeholder_text="Full Name", width=300, height=45, corner_radius=10, fg_color="#000000")
        self.user_entry.pack(pady=10)
        self.designation_entry = ctk.CTkEntry(self.login_frame, placeholder_text="Designation", width=300, height=45, corner_radius=10, fg_color="#000000")
        self.designation_entry.pack(pady=10)
        self.pass_entry = ctk.CTkEntry(self.login_frame, placeholder_text="Password", width=300, height=45, corner_radius=10, fg_color="#000000", show="*")
        self.pass_entry.pack(pady=10)
        ctk.CTkButton(self.login_frame, text="LOGIN", command=self.handle_auth, width=300, height=50, corner_radius=10, font=(self.main_font, 16, "bold"), fg_color=self.accent_blue).pack(pady=40)

    def handle_auth(self):
        n, d, p = self.user_entry.get().strip(), self.designation_entry.get().strip(), self.pass_entry.get().strip()
        if not n or not d:
            messagebox.showwarning("Error", "All fields are required"); return
        if p == ADMIN_PASSWORD: role = "ADMIN"
        elif p == STAFF_PASSWORD: role = "STAFF"
        else:
            messagebox.showerror("Error", "Invalid Password"); return
        with open("user_config.txt", "w") as f: f.write(f"{n.upper()},{d.upper()},{role}")
        self.username, self.designation, self.role = n.upper(), d.upper(), role
        self.login_frame.destroy(); self.setup_main_ui(); self.start_sync_thread()

    def setup_main_ui(self):
        self.nav_frame = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color="#000000", border_width=1, border_color="#111111")
        self.nav_frame.pack(side="top", fill="x")
        u_info = f"{self.designation} | {self.username}"
        ctk.CTkLabel(self.nav_frame, text=u_info, text_color=self.accent_blue, font=(self.main_font, 14, "bold")).pack(side="left", padx=25)
        self.search_entry = ctk.CTkEntry(self.nav_frame, placeholder_text="🔍 Filter records...", width=350, height=35, corner_radius=20, fg_color="#080808", border_color="#1A1A1A")
        self.search_entry.pack(side="left", padx=15)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_ui())
        self.nav_fin_filter = ctk.CTkComboBox(self.nav_frame, values=["--- ALL FINANCES ---"], command=lambda x: self.refresh_ui(), width=180, height=35, corner_radius=10)
        self.nav_fin_filter.set("--- ALL FINANCES ---"); self.nav_fin_filter.pack(side="left", padx=10)
        self.filter_btn = ctk.CTkButton(self.nav_frame, text="🕒 PENDING", command=self.toggle_pending_filter, width=100, height=35, fg_color="#111111", font=(self.main_font, 12, "bold"))
        self.filter_btn.pack(side="left", padx=2)
        self.priority_btn = ctk.CTkButton(self.nav_frame, text="📌 TIME", command=self.toggle_priority_sort, width=80, height=35, fg_color="#111111", font=(self.main_font, 12, "bold"))
        self.priority_btn.pack(side="left", padx=2)
        ctk.CTkButton(self.nav_frame, text="📊 EXPORT", command=self.export_to_excel, width=90, height=35, fg_color="#0B3D23", font=(self.main_font, 12, "bold")).pack(side="right", padx=25)
        self.input_container = ctk.CTkFrame(self, corner_radius=15, fg_color="#050505", border_width=1, border_color="#111111")
        self.input_container.pack(pady=15, padx=25, fill="x")
        self.lp = ctk.CTkFrame(self.input_container, fg_color="transparent")
        self.lp.pack(side="left", padx=15, pady=15)
        self.finance_entry = ctk.CTkComboBox(self.lp, values=["Loading..."], width=220, height=38, corner_radius=8)
        self.finance_entry.set(""); self.finance_entry.pack(pady=5)
        self.finance_entry._entry.bind("<KeyRelease>", self.filter_finance_list)
        self.finance_entry._entry.bind("<Button-3>", self.show_finance_context_menu)
        cats = ["1. Rate Correction", "2. Spelling/Address", "3. Digital Sign", "4. Report Upload", "5. Photos/Drafting"]
        self.cat_dropdown = ctk.CTkComboBox(self.lp, values=cats, width=220, height=38, corner_radius=8)
        self.cat_dropdown.set("Select Category"); self.cat_dropdown.pack(pady=5)
        self.priority_dropdown = ctk.CTkComboBox(self.lp, values=self.priorities, width=220, height=38, corner_radius=8)
        self.priority_dropdown.set("Normal"); self.priority_dropdown.pack(pady=5)
        self.task_entry = ctk.CTkTextbox(self.input_container, height=135, corner_radius=10, fg_color="#000000", border_width=1, border_color="#1A1A1A", font=(self.main_font, 15))
        self.task_entry.pack(side="left", padx=10, pady=15, fill="both", expand=True)
        self.add_btn = ctk.CTkButton(self.input_container, text="ADD TO\nLEDGER", command=self.add_task, width=120, height=135, font=(self.main_font, 14, "bold")); self.add_btn.pack(side="right", padx=15, pady=15)
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="REPORTS CORRECTION LEDGER", label_font=(self.main_font, 14, "bold"))
        self.scroll_frame.pack(pady=0, padx=20, fill="both", expand=True)
        self.status_bar = ctk.CTkLabel(self, text="System Online", font=(self.main_font, 11), text_color="#222222")
        self.status_bar.pack(side="bottom", pady=5)

    def start_sync_thread(self):
        def loop():
            import time
            while True: self.fetch_data(); time.sleep(4) 
        threading.Thread(target=loop, daemon=True).start()

    def fetch_data(self):
        if self.is_fetching or self.is_resizing: return 
        self.is_fetching = True
        def run():
            try:
                self.fetch_global_settings()
                res = requests.get(DB_URL, timeout=5)
                if res.status_code == 200:
                    nd = res.json() or {}
                    if json.dumps(nd, sort_keys=True) != json.dumps(self.tasks_dict, sort_keys=True):
                        if self.tasks_dict:
                            for k in (set(nd.keys()) - set(self.tasks_dict.keys())): self.after(0, lambda key=k: self.show_toast(nd[key]))
                        self.tasks_dict = nd
                        raw = set(t.get('finance', '').upper() for t in self.tasks_dict.values() if t.get('finance'))
                        self.all_finance_names = sorted([self.renamed_finances.get(n, n) for n in raw if n not in self.hidden_finances])
                        self.after(0, self.update_ui_state)
            except: pass
            finally: self.is_fetching = False
        threading.Thread(target=run, daemon=True).start()

    def update_ui_state(self):
        self.finance_entry.configure(values=self.all_finance_names)
        self.nav_fin_filter.configure(values=["--- ALL FINANCES ---"] + self.all_finance_names)
        self.refresh_ui()

    def update_status(self, tid, ns):
        note = self.task_inputs[tid].get().strip() if tid in self.task_inputs else "Updated"
        if ns == "Completed" and not note: messagebox.showwarning("Note Required", "Enter a completion note."); return
        finished_time = datetime.now().strftime("%d/%b/%Y %H:%M:%S")
        d = {"status": ns, "comment": note, "completed_by": self.username, "finished_at": finished_time}
        threading.Thread(target=lambda: requests.patch(f"{DB_BASE_URL}/{tid}.json", json=d)).start()
        self.after(500, self.fetch_data)

    def add_task(self):
        f, c, p, t = self.finance_entry.get().strip(), self.cat_dropdown.get(), self.priority_dropdown.get(), self.task_entry.get("1.0", "end-1c").strip()
        if not f or c == "Select Category" or not t: return
        assigned_time = datetime.now().strftime("%d/%b/%Y %H:%M:%S")
        pld = {"finance": f.upper(), "task": f"[{c}] {t}", "priority": p, "assigner": self.username, "status": "Pending", "assigned_at": assigned_time}
        threading.Thread(target=lambda: requests.post(DB_URL, json=pld)).start()
        self.task_entry.delete("1.0", "end"); self.after(500, self.fetch_data)

    def delete_task(self, tid):
        if self.role != "ADMIN" and self.tasks_dict.get(tid, {}).get('assigner') != self.username:
            messagebox.showerror("Denied", "Access Restricted."); return
        if messagebox.askyesno("Delete", "Permanently remove?"):
            threading.Thread(target=lambda: requests.delete(f"{DB_BASE_URL}/{tid}.json")).start()
            self.after(500, self.fetch_data)

    def fetch_global_settings(self):
        try:
            res = requests.get(SETTINGS_URL, timeout=5)
            if res.status_code == 200:
                data = res.json() or {}
                self.hidden_finances = set(data.get("hidden", []))
                self.renamed_finances = data.get("renamed", {})
        except: pass

    def toggle_pending_filter(self): self.pending_filter_active = not self.pending_filter_active; self.filter_btn.configure(fg_color="#7F4D00" if self.pending_filter_active else "#111111"); self.refresh_ui()
    def toggle_priority_sort(self): self.sort_by_priority = not self.sort_by_priority; self.priority_btn.configure(text="📌 PRIORITY" if self.sort_by_priority else "📌 TIME"); self.refresh_ui()
    def export_to_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if path: pd.DataFrame.from_dict(self.tasks_dict, orient='index').to_excel(path, index=False)

    def filter_finance_list(self, event):
        typed = self.finance_entry.get().upper()
        self.finance_entry.configure(values=[n for n in self.all_finance_names if typed in n] if typed else self.all_finance_names)

    def show_finance_context_menu(self, event):
        if self.role != "ADMIN": return 
        val = self.finance_entry.get().upper()
        if not val: return
        m = Menu(self, tearoff=0); m.add_command(label=f"Rename {val}", command=lambda: self.rename_fin(val)); m.add_command(label=f"Hide {val}", command=lambda: self.hide_fin(val)); m.tk_popup(event.x_root, event.y_root)

    def rename_fin(self, old):
        new = simpledialog.askstring("Rename", f"New name for {old}:")
        if new: self.renamed_finances[old] = new.upper(); self.push_settings()
    def hide_fin(self, name):
        if messagebox.askyesno("Hide", f"Hide {name} globally?"): self.hidden_finances.add(name.upper()); self.push_settings()
    def push_settings(self):
        threading.Thread(target=lambda: requests.put(SETTINGS_URL, json={"hidden": list(self.hidden_finances), "renamed": self.renamed_finances})).start(); self.refresh_ui()

    def start_global_resize(self, event): self.is_resizing = True; self._r_s_y = event.y_root; self._r_s_h = self.global_card_height
    def do_global_resize(self, event):
        self.global_card_height = max(40, self._r_s_h + (event.y_root - self._r_s_y))
        for card in self.scroll_frame.winfo_children(): 
            if isinstance(card, ctk.CTkFrame): card.configure(height=self.global_card_height)
    def stop_global_resize(self, event): self.is_resizing = False; self.refresh_ui()

if __name__ == "__main__":
    TaskApp().mainloop()