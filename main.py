import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import shutil
import json
from datetime import datetime
import threading
import time
import hashlib
import sys

# =======================================================
# 📂 إعداد مسار حفظ الملفات الآمن في AppData
# =======================================================
app_data = os.getenv('APPDATA')
config_folder = os.path.join(app_data, "SmartOrganizerPro")

if not os.path.exists(config_folder):
    os.makedirs(config_folder)

CONFIG_FILE = os.path.join(config_folder, "config.json")
HISTORY_FILE = os.path.join(config_folder, "undo_history.json")
# =======================================================

def resource_path(relative_path):
    """دالة احترافية لمعرفة مسار الملفات داخل الـ exe"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# إعدادات المظهر
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DEFAULT_CONFIG = {
    'PowerPoint': ['.pptx', '.ppt', '.pps', '.ppsx'],
    'PDF_Files': ['.pdf'],
    'Word_Docs': ['.docx', '.doc', '.rtf'],
    'Excel_Sheets': ['.xlsx', '.xls', '.csv'],
    'Images': ['.jpg', '.png', '.jpeg', '.gif', '.svg', '.webp'],
    'Videos': ['.mp4', '.mov', '.avi', '.mkv', '.wmv'],
    'Archives': ['.zip', '.rar', '.7z'],
    'Programming': ['.py', '.php', '.js', '.html', '.css', '.json'],
    'Audio': ['.mp3', '.wav', '.ogg']
}

IGNORED_FOLDERS = {
    '$RECYCLE.BIN', 'System Volume Information', 'Windows',
    'Program Files', 'Program Files (x86)', 'ProgramData',
    'AppData', 'Boot', 'Recovery', 'Windows.old'
}

IGNORED_FILES = {'desktop.ini', 'thumbs.db', 'ntuser.dat'}

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("الإعدادات")
        self.geometry("500x500")
        self.attributes("-topmost", True)

        self.label = ctk.CTkLabel(self, text="تعديل قواعد الفرز ⚙️", font=("Arial", 18, "bold"))
        self.label.pack(pady=10)

        self.txt_config = ctk.CTkTextbox(self, width=450, height=350, font=("Consolas", 12))
        self.txt_config.pack(pady=10)
        
        current_config = self.parent.load_config()
        self.txt_config.insert("0.0", json.dumps(current_config, indent=4))

        self.btn_save = ctk.CTkButton(self, text="حفظ الإعدادات 💾", command=self.save_config, fg_color="green", font=("Arial", 14, "bold"))
        self.btn_save.pack(pady=10)

    def save_config(self):
        try:
            new_config = json.loads(self.txt_config.get("0.0", "end"))
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=4)
            messagebox.showinfo("نجاح", "تم الحفظ بنجاح")
            self.destroy()
        except Exception as e:
            messagebox.showerror("خطأ", f"صيغة غير صحيحة: {e}")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Smart Organizer Pro v1.6")
        self.geometry("950x850")
        
        # --- استدعاء الأيقونة بطريقة آمنة ---
        try:
            self.iconbitmap(resource_path("Productiv_Tool.ico"))
        except:
            pass 
        # -------------------------------

        self.history = []
        self.load_history() # استرجاع السجل عند الفتح
        
        self.is_running = False
        self.is_paused = False
        self.stop_requested = False
        self.file_count = 0

        self.label = ctk.CTkLabel(self, text="مُنظّم الملفات الذكي 🗂️", font=("Arial", 30, "bold"))
        self.label.pack(pady=15)

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(pady=5, fill="both", expand=True, padx=20)

        self.stats_frame = ctk.CTkFrame(self.main_container, width=250, corner_radius=15)
        self.stats_frame.pack(side="right", fill="y", padx=(10, 0))

        self.stats_title = ctk.CTkLabel(self.stats_frame, text="تحليل المساحة 📊", font=("Arial", 18, "bold"))
        self.stats_title.pack(pady=15)

        self.stat_labels = {}
        categories = ["Images", "Videos", "Documents", "Programming", "Others"]
        for cat in categories:
            lbl = ctk.CTkLabel(self.stats_frame, text=f"{cat}: 0.00 MB", font=("Arial", 13))
            lbl.pack(pady=5, padx=20, anchor="e")
            self.stat_labels[cat] = lbl

        self.total_size_label = ctk.CTkLabel(self.stats_frame, text="الحجم الكلي: 0.00 MB", font=("Arial", 14, "bold"), text_color="#3498db")
        self.total_size_label.pack(pady=30)

        self.work_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.work_frame.pack(side="left", fill="both", expand=True)

        self.btn_frame = ctk.CTkFrame(self.work_frame, fg_color="transparent")
        self.btn_frame.pack(pady=5)

        self.btn_start = ctk.CTkButton(self.btn_frame, text="التنظيف الذكي 🚀", command=self.start_process, 
                                       fg_color="#2ecc71", hover_color="#27ae60", font=("Arial", 14, "bold"))
        self.btn_start.grid(row=0, column=2, padx=5)

        self.btn_duplicates = ctk.CTkButton(self.btn_frame, text="صيد المكررات 🕵️", command=self.start_duplicate_finder, 
                                          fg_color="#8e44ad", hover_color="#9b59b6", font=("Arial", 14, "bold"))
        self.btn_duplicates.grid(row=0, column=1, padx=5)

        self.btn_stop = ctk.CTkButton(self.btn_frame, text="إيقاف 🛑", command=self.request_stop, 
                                       fg_color="#e74c3c", hover_color="#c0392b", state="disabled", font=("Arial", 14, "bold"))
        self.btn_stop.grid(row=0, column=0, padx=5)

        self.progress_bar = ctk.CTkProgressBar(self.work_frame, width=550)
        self.progress_bar.pack(pady=15)
        self.progress_bar.set(0)

        self.info_frame = ctk.CTkFrame(self.work_frame, fg_color="transparent")
        self.info_frame.pack(pady=5, fill="x", padx=10)

        self.status_label = ctk.CTkLabel(self.info_frame, text="الحالة: جاهز", font=("Arial", 14))
        self.status_label.pack(side="right")

        self.counter_label = ctk.CTkLabel(self.info_frame, text="العمليات: 0", font=("Arial", 14, "bold"), text_color="#3498db")
        self.counter_label.pack(side="left")

        self.log_box = ctk.CTkTextbox(self.work_frame, width=600, height=350, font=("Consolas", 13))
        self.log_box.pack(pady=10)
        self.log_insert("للعمل جاهز البرنامج ✅")

        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.pack(pady=10)

        # تفعيل زر التراجع إذا كان هناك سجل سابق
        undo_state = "normal" if self.history else "disabled"
        self.btn_undo = ctk.CTkButton(self.bottom_frame, text="الرجوع للحالة القديمة ⏪", command=self.handle_emergency_undo, 
                                     fg_color="transparent", border_width=2, text_color="#ecf0f1", height=35, font=("Arial", 13, "bold"), state=undo_state)
        self.btn_undo.grid(row=0, column=0, padx=10)

        self.btn_settings = ctk.CTkButton(self.bottom_frame, text="الإعدادات 🎛️", command=self.open_settings, 
                                          fg_color="#34495e", hover_color="#2c3e50", font=("Arial", 13, "bold"))
        self.btn_settings.grid(row=0, column=1, padx=10)

        self.btn_pause = ctk.CTkButton(self.bottom_frame, text="إيقاف مؤقت ⏳", command=self.toggle_pause, state="disabled", font=("Arial", 13, "bold"))
        self.btn_pause.grid(row=0, column=2, padx=10)
        
        self.btn_about = ctk.CTkButton(self.bottom_frame, text="عن البرنامج ℹ️", command=self.show_about, 
                                      fg_color="#f39c12", hover_color="#d35400", font=("Arial", 13, "bold"))
        self.btn_about.grid(row=0, column=3, padx=10)

    # --- دوال التعامل مع السجل والإعدادات ---
    def save_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False)
            if self.history:
                self.btn_undo.configure(state="normal")
            else:
                self.btn_undo.configure(state="disabled")
        except:
            pass

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except:
                self.history = []

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: 
                json.dump(DEFAULT_CONFIG, f, indent=4)
            return DEFAULT_CONFIG
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: 
                return json.load(f)
        except:
            return DEFAULT_CONFIG
    # ----------------------------------------

    def show_about(self):
        about_win = ctk.CTkToplevel(self)
        about_win.title("عن البرنامج")
        about_win.geometry("450x280")
        about_win.attributes("-topmost", True)

        lbl_title = ctk.CTkLabel(about_win, text="مُنظّم الملفات الذكي Pro v1.6", font=("Arial", 20, "bold"), text_color="#3498db")
        lbl_title.pack(pady=(20, 10))

        lbl_desc = ctk.CTkLabel(about_win, text="أداة احترافية وآمنة لتنظيم وتحليل مساحة العمل", font=("Arial", 13))
        lbl_desc.pack(pady=5)

        lbl_dev = ctk.CTkLabel(about_win, text="تطوير وبرمجة: محمد بن بوشتى", font=("Arial", 15, "bold"), text_color="#ecf0f1")
        lbl_dev.pack(pady=10)

        lbl_fed = ctk.CTkLabel(about_win, text="الفيدرالية المغربية لصناع المحتوى", font=("Arial", 16, "bold"), text_color="#2ecc71")
        lbl_fed.pack(pady=5)

        lbl_year = ctk.CTkLabel(about_win, text="© 2026 جميع الحقوق محفوظة", font=("Arial", 12))
        lbl_year.pack(pady=10)

    def log_insert(self, text):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    def open_settings(self): 
        SettingsWindow(self)

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.status_label.configure(text="الحالة: متوقف مؤقتاً" if self.is_paused else "الحالة: جاري العمل")
        self.btn_pause.configure(text="استمرار ▶️" if self.is_paused else "إيقاف مؤقت ⏳")

    def request_stop(self): 
        self.stop_requested = True

    def get_size_mb(self, filepath):
        try: return os.path.getsize(filepath) / (1024 * 1024)
        except: return 0

    def update_dashboard_thread(self, target_dir):
        config = self.load_config()
        stats = {"Images": 0, "Videos": 0, "Documents": 0, "Programming": 0, "Others": 0}
        total_size = 0
        doc_cats = ['PDF_Files', 'Word_Docs', 'Excel_Sheets', 'PowerPoint']

        for root, dirs, files in os.walk(target_dir):
            if self.stop_requested: break
            
            dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS and not d.startswith('.') and d != "Duplicates_Found"]

            for filename in files:
                if filename.startswith('.') or filename.lower() in IGNORED_FILES:
                    continue

                filepath = os.path.join(root, filename)
                size = self.get_size_mb(filepath)
                total_size += size
                ext = os.path.splitext(filename)[1].lower()
                
                found = False
                for cat, exts in config.items():
                    if ext in exts:
                        if cat in stats: stats[cat] += size
                        elif cat in doc_cats: stats["Documents"] += size
                        else: stats["Others"] += size
                        found = True
                        break
                if not found: stats["Others"] += size

        def update_ui():
            for cat, size in stats.items():
                if cat in self.stat_labels:
                    self.stat_labels[cat].configure(text=f"{cat}: {size:.2f} MB")
            self.total_size_label.configure(text=f"الحجم الكلي: {total_size:.2f} MB")
        self.after(0, update_ui)

    def setup_ui_for_run(self):
        self.is_running = True
        self.stop_requested = False
        self.is_paused = False
        self.file_count = 0
        self.progress_bar.set(0)
        self.btn_start.configure(state="disabled")
        self.btn_duplicates.configure(state="disabled")
        self.btn_pause.configure(state="normal")
        self.btn_stop.configure(state="normal")
        self.btn_undo.configure(state="disabled")

    def hash_file(self, filepath):
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                buf = f.read(65536)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
            return hasher.hexdigest()
        except: return None

    def start_process(self):
        target_dir = filedialog.askdirectory()
        if not target_dir: return
        self.setup_ui_for_run()
        self.log_insert("جاري فحص الديسك وبدء العملية ⏳")
        threading.Thread(target=self.run_organize_tasks, args=(target_dir,), daemon=True).start()

    def start_duplicate_finder(self):
        target_dir = filedialog.askdirectory()
        if not target_dir: return
        self.setup_ui_for_run()
        self.log_insert("جاري فحص الديسك وبدء العملية ⏳")
        threading.Thread(target=self.run_duplicate_tasks, args=(target_dir,), daemon=True).start()

    def run_organize_tasks(self, target_dir):
        threading.Thread(target=self.update_dashboard_thread, args=(target_dir,), daemon=True).start()
        self.organize_engine(target_dir)

    def run_duplicate_tasks(self, target_dir):
        threading.Thread(target=self.update_dashboard_thread, args=(target_dir,), daemon=True).start()
        self.duplicate_engine(target_dir)

    def duplicate_engine(self, target_dir):
        start_time = time.time()
        hashes = {}
        dupes_found = 0
        dupes_dir = os.path.join(target_dir, "Duplicates_Found")

        self.after(0, lambda: self.status_label.configure(text="الحالة: جاري إحصاء الملفات..."))
        
        total_files = 0
        for r, d, f in os.walk(target_dir):
            d[:] = [dr for dr in d if dr not in IGNORED_FOLDERS and not dr.startswith('.')]
            total_files += len([fl for fl in f if not fl.startswith('.') and fl.lower() not in IGNORED_FILES])
        if total_files == 0: total_files = 1

        self.after(0, lambda: self.status_label.configure(text="الحالة: جاري قراءة البصمات"))

        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS and not d.startswith('.') and d != "Duplicates_Found"]

            for filename in files:
                if filename.startswith('.') or filename.lower() in IGNORED_FILES:
                    continue

                while self.is_paused and not self.stop_requested: time.sleep(0.5)
                if self.stop_requested: break

                filepath = os.path.join(root, filename)
                file_hash = self.hash_file(filepath)

                if file_hash:
                    if file_hash in hashes:
                        if not os.path.exists(dupes_dir): os.makedirs(dupes_dir)
                        new_path = os.path.join(dupes_dir, filename)
                        
                        if os.path.exists(new_path):
                            new_path = os.path.join(dupes_dir, f"{int(time.time())}_{filename}")

                        try:
                            shutil.move(filepath, new_path)
                            self.history.append((new_path, filepath))
                            self.save_history() # حفظ التراجع
                            dupes_found += 1
                            self.after(0, lambda f=filename: self.log_insert(f"{f} :مكرر ملف ⚠️"))
                        except Exception as e:
                            self.after(0, lambda f=filename: self.log_insert(f"تعذر نقل الملف المكرر قيد الاستخدام: {f} ❌"))
                    else:
                        hashes[file_hash] = filepath

                self.file_count += 1
                self.after(0, lambda c=self.file_count, t=total_files: self.progress_bar.set(c / t))
                self.after(0, lambda c=self.file_count: self.counter_label.configure(text=f"العمليات: {c}"))

        self.after(0, lambda: self.status_label.configure(text="الحالة: انتهى صيد المكررات"))
        self.after(0, self.reset_ui)
        
        elapsed_time = round(time.time() - start_time, 1)
        
        if dupes_found > 0:
            ans = messagebox.askyesno("تحرير المساحة", f"اكتملت العملية في {elapsed_time} ثانية.\nتم العثور على {dupes_found} ملف مكرر.\nهل تريد حذفها نهائياً لتوفير المساحة؟")
            if ans:
                try:
                    shutil.rmtree(dupes_dir)
                    self.history = [(c, o) for c, o in self.history if not c.startswith(dupes_dir)]
                    self.save_history() # تحديث السجل بعد الحذف
                    self.log_insert("تم حذف الملفات المكررة وتوفير المساحة 🗑️")
                    threading.Thread(target=self.update_dashboard_thread, args=(target_dir,), daemon=True).start()
                except Exception as e:
                    messagebox.showerror("خطأ", "تعذر الحذف لبعض الملفات")
        else:
            messagebox.showinfo("النتيجة", f"اكتملت العملية في {elapsed_time} ثانية.\nلا توجد ملفات مكررة")

    def organize_engine(self, target_dir):
        start_time = time.time()
        file_types = self.load_config()
        
        self.after(0, lambda: self.status_label.configure(text="الحالة: جاري إحصاء الملفات..."))
        
        total_files = 0
        for r, d, f in os.walk(target_dir):
            d[:] = [dr for dr in d if dr not in IGNORED_FOLDERS and not dr.startswith('.')]
            total_files += len([fl for fl in f if not fl.startswith('.') and fl.lower() not in IGNORED_FILES])
        if total_files == 0: total_files = 1

        self.after(0, lambda: self.status_label.configure(text="الحالة: جاري التنظيم"))
        
        files_moved = 0
        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS and not d.startswith('.')]
            dirs[:] = [d for d in dirs if d not in file_types.keys() and d != "Duplicates_Found"]

            for filename in files:
                if filename.startswith('.') or filename.lower() in IGNORED_FILES:
                    continue

                while self.is_paused and not self.stop_requested: time.sleep(0.5)
                if self.stop_requested: break

                filepath = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()

                for cat, exts in file_types.items():
                    if ext in exts:
                        try:
                            mtime = os.path.getmtime(filepath)
                            date = datetime.fromtimestamp(mtime)
                            cat_path = os.path.join(target_dir, cat, str(date.year), date.strftime("%B"))
                            
                            if not os.path.exists(cat_path): os.makedirs(cat_path)
                            
                            new_path = os.path.join(cat_path, filename)
                            if os.path.exists(new_path):
                                new_path = os.path.join(cat_path, f"{int(time.time())}_{filename}")

                            shutil.move(filepath, new_path)
                            self.history.append((new_path, filepath))
                            self.save_history() # حفظ كل عملية لضمان التراجع
                            files_moved += 1
                            self.file_count += 1
                            
                            self.after(0, lambda c=self.file_count, t=total_files: self.progress_bar.set(c / t))
                            self.after(0, lambda c=self.file_count: self.counter_label.configure(text=f"العمليات: {c}"))
                            self.after(0, lambda f=filename: self.log_insert(f"{f} :نقل تم 📁"))
                        except Exception as e: 
                            self.after(0, lambda f=filename: self.log_insert(f"تعذر النقل لأن الملف قيد الاستخدام: {f} ❌"))
                        continue # Move to next file after processing
        
        self.after(0, lambda: self.status_label.configure(text="الحالة: انتهى التنظيم"))
        self.after(0, self.reset_ui)
        
        elapsed_time = round(time.time() - start_time, 1)
        messagebox.showinfo("نجاح", f"اكتمل التنظيم بنجاح!\nالوقت المستغرق: {elapsed_time} ثانية\nالملفات المنظمة: {files_moved}")

    def handle_emergency_undo(self):
        if not self.history: return
        if messagebox.askyesno("تأكيد", "استعادة الملفات لأماكنها القديمة؟"):
            self.log_insert("جاري الاستعادة 🔄")
            failed_count = 0
            for current, original in reversed(self.history):
                try: 
                    shutil.move(current, original)
                except: 
                    failed_count += 1
                    self.log_insert(f"تعذر استرجاع: {current} ❌")
            
            self.history = []
            self.save_history() # مسح السجل بعد الاسترجاع
            
            if failed_count == 0:
                messagebox.showinfo("تم", "عادت جميع الملفات بنجاح ✅")
                self.log_insert("تمت الاستعادة بنجاح ✅")
            else:
                messagebox.showwarning("تنبيه", f"تمت الاستعادة مع فشل استرجاع {failed_count} ملف.")
            
            self.btn_undo.configure(state="disabled")

    def reset_ui(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_duplicates.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="إيقاف مؤقت ⏳")
        self.btn_stop.configure(state="disabled")
        if self.history:
            self.btn_undo.configure(state="normal")

if __name__ == "__main__":
    app = App()
    app.mainloop()