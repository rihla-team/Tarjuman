import customtkinter as ctk
from tkinter import filedialog, messagebox
from deep_translator import GoogleTranslator
import xml.etree.ElementTree as ET
from bidi.algorithm import get_display
import arabic_reshaper
import threading
import queue
import re
import os
import sys
import json
import logging
from datetime import datetime
from PIL import Image, ImageTk

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class SmartArabicTranslator(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # إعداد التسجيل
        self.setup_logging()
        
        # إعداد النافذة الرئيسية
        self.title("المترجم الذكي المتقدم")
        self.geometry("900x700")
        self.minsize(800, 600)

        # تهيئة المتغيرات
        self.processing = False
        self.files_processed = 0
        self.filepath = None
        self.settings_path = resource_path('settings.json')
        self.icon_path = resource_path('icon.png')
        self.progress_queue = queue.Queue()
        
        # تهيئة ذاكرة الترجمة والمصطلحات
        self.init_translation_memory()
        
        # تحميل الإعدادات
        self.load_settings()

        # تعيين الألوان والمظهر
        ctk.set_appearance_mode(self.settings.get("theme", "dark"))
        ctk.set_default_color_theme(self.settings.get("color_theme", "blue"))

        # تحميل الخط والأيقونات
        self.load_fonts()
        self.load_icons()
        
        # إنشاء واجهة المستخدم
        self.create_menu()
        self.create_main_interface()
        self.create_status_bar()
        
        # بدء مراقبة التقدم
        self.monitor_progress()

    def setup_logging(self):
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def init_translation_memory(self):
        """تهيئة ذاكرة الترجمة والمصطلحات"""
        try:
            if not os.path.exists('translation_memory.json'):
                with open('translation_memory.json', 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=4)
            
            if not os.path.exists('terms.json'):
                with open('terms.json', 'w', encoding='utf-8') as f:
                    json.dump({
                        "file": "ملف",
                        "edit": "تحرير",
                        "view": "عرض",
                        "help": "مساعدة",
                        "settings": "إعدادات",
                        "save": "حفظ",
                        "open": "فتح",
                        "close": "إغلاق",
                        "new": "جديد",
                        "delete": "حذف",
                        "update": "تحديث",
                        "create": "إنشاء"
                    }, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"Error initializing files: {str(e)}")

    def load_settings(self):
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
        except:
            self.settings = {
                "theme": "dark",
                "color_theme": "blue",
                "target_language": "ar",
                "create_backup": True,
                "reverse_arabic": True,
                "use_terms": True,
                "spellcheck": True,
                "save_to_memory": True
            }
            self.save_settings()

    def save_settings(self):
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Error saving settings: {str(e)}")
            messagebox.showerror("خطأ", f"فشل حفظ الإعدادات: {str(e)}")

    def load_fonts(self):
        try:
            self.arabic_font_large = ctk.CTkFont(family="Segoe UI", size=24, weight="bold")
            self.arabic_font_medium = ctk.CTkFont(family="Segoe UI", size=16)
            self.arabic_font_small = ctk.CTkFont(family="Segoe UI", size=12)
        except Exception as e:
            logging.error(f"Error loading fonts: {str(e)}")
            self.arabic_font_large = ctk.CTkFont(size=24, weight="bold")
            self.arabic_font_medium = ctk.CTkFont(size=16)
            self.arabic_font_small = ctk.CTkFont(size=12)

    def load_icons(self):
        try:
            if os.path.exists(self.icon_path):
                self.app_icon = ImageTk.PhotoImage(Image.open(self.icon_path))
                self.iconphoto(True, self.app_icon)
        except Exception as e:
            logging.error(f"Error loading icons: {str(e)}")

    def create_menu(self):
        self.menu_frame = ctk.CTkFrame(self)
        self.menu_frame.pack(fill="x", padx=10, pady=5)

        buttons = [
            ("الرئيسية", self.show_main),
            ("المصطلحات", self.show_terms_manager),
            ("ذاكرة الترجمة", self.show_translation_memory),
            ("الإعدادات", self.show_settings),
            ("حول", self.show_about),
            ("مساعدة", self.show_help)
        ]

        for text, command in buttons:
            btn = ctk.CTkButton(
                self.menu_frame,
                text=text,
                command=command,
                width=100,
                height=32,
                font=self.arabic_font_medium
            )
            btn.pack(side="right", padx=5)

    def create_main_interface(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # العنوان
        title = ctk.CTkLabel(
            self.main_frame,
            text="المترجم الذكي المتقدم",
            font=self.arabic_font_large
        )
        title.pack(pady=20)

        # إطار اختيار نوع الملف
        file_type_frame = ctk.CTkFrame(self.main_frame)
        file_type_frame.pack(fill="x", padx=20, pady=5)
        
        self.file_type = ctk.StringVar(value="yml")
        
        yml_radio = ctk.CTkRadioButton(
            file_type_frame,
            text="YML",
            variable=self.file_type,
            value="yml",
            font=self.arabic_font_medium
        )
        yml_radio.pack(side="left", padx=20)
        
        xml_radio = ctk.CTkRadioButton(
            file_type_frame,
            text="XML",
            variable=self.file_type,
            value="xml",
            font=self.arabic_font_medium
        )
        xml_radio.pack(side="left", padx=20)

        # إطار أدوات التعريب
        self.create_arabization_tools()

        # إطار اختيار الملف
        file_frame = ctk.CTkFrame(self.main_frame)
        file_frame.pack(fill="x", padx=20, pady=10)

        self.file_entry = ctk.CTkEntry(
            file_frame,
            placeholder_text="اختر ملف للترجمة...",
            width=500,
            font=self.arabic_font_medium
        )
        self.file_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)

        browse_btn = ctk.CTkButton(
            file_frame,
            text="استعراض",
            command=self.select_file,
            width=120,
            font=self.arabic_font_medium
        )
        browse_btn.pack(side="right")

        # زر الترجمة
        self.translate_button = ctk.CTkButton(
            self.main_frame,
            text="ترجمة وحفظ",
            command=self.start_translation,
            width=200,
            height=40,
            font=self.arabic_font_medium,
            state="disabled"
        )
        self.translate_button.pack(pady=20)

        # شريط التقدم
        self.progress_bar = ctk.CTkProgressBar(self.main_frame)
        self.progress_bar.pack(fill="x", padx=20, pady=10)
        self.progress_bar.set(0)

        # مربع النتائج
        self.results_text = ctk.CTkTextbox(
            self.main_frame,
            height=150,
            font=self.arabic_font_small
        )
        self.results_text.pack(fill="both", padx=20, pady=10, expand=True)

    def create_arabization_tools(self):
        """إضافة أدوات التعريب"""
        tools_frame = ctk.CTkFrame(self.main_frame)
        tools_frame.pack(fill="x", padx=20, pady=5)

        # خيارات التعريب
        options_label = ctk.CTkLabel(
            tools_frame,
            text="خيارات التعريب:",
            font=self.arabic_font_medium
        )
        options_label.pack(side="left", padx=10)

        # استخدام المصطلحات
        self.use_terms_var = ctk.BooleanVar(value=self.settings.get("use_terms", True))
        terms_check = ctk.CTkCheckBox(
            tools_frame,
            text="استخدام المصطلحات",
            variable=self.use_terms_var,
            font=self.arabic_font_medium
        )
        terms_check.pack(side="left", padx=10)

        # التدقيق اللغوي
        self.spellcheck_var = ctk.BooleanVar(value=self.settings.get("spellcheck", True))
        spellcheck_check = ctk.CTkCheckBox(
            tools_frame,
            text="التدقيق اللغوي",
            variable=self.spellcheck_var,
            font=self.arabic_font_medium
        )
        spellcheck_check.pack(side="left", padx=10)

        # عكس النصوص العربية
        self.reverse_var = ctk.BooleanVar(value=self.settings.get("reverse_arabic", True))
        reverse_check = ctk.CTkCheckBox(
            tools_frame,
            text="عكس النصوص العربية",
            variable=self.reverse_var,
            font=self.arabic_font_medium
        )
        reverse_check.pack(side="left", padx=10)

        # نسخة احتياطية
        self.backup_var = ctk.BooleanVar(value=self.settings.get("create_backup", True))
        backup_check = ctk.CTkCheckBox(
            tools_frame,
            text="نسخة احتياطية",
            variable=self.backup_var,
            font=self.arabic_font_medium
        )
        backup_check.pack(side="left", padx=10)

    def create_status_bar(self):
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.pack(fill="x", side="bottom")

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="جاهز للترجمة",
            font=self.arabic_font_small
        )
        self.status_label.pack(side="left", padx=10)

        self.files_label = ctk.CTkLabel(
            self.status_frame,
            text="الملفات المعالجة: 0",
            font=self.arabic_font_small
        )
        self.files_label.pack(side="right", padx=10)

    def select_file(self):
        file_type = self.file_type.get()
        filetypes = [
            ("All supported files", "*.yml;*.xml"),
            ("YML files", "*.yml"),
            ("XML files", "*.xml")
        ]
        
        self.filepath = filedialog.askopenfilename(
            filetypes=filetypes,
            title=f"اختر ملف {file_type.upper()}"
        )
        if self.filepath:
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, self.filepath)
            self.translate_button.configure(state="normal")

    def start_translation(self):
        if self.processing:
            return

        if not self.filepath:
            messagebox.showerror("خطأ", "الرجاء اختيار ملف أولاً")
            return

        self.processing = True
        self.translate_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.results_text.delete("1.0", "end")
        self.status_label.configure(text="جاري الترجمة...")
        
        # بدء المعالجة في thread منفصل
        thread = threading.Thread(target=self.process_translation)
        thread.daemon = True
        thread.start()

    def process_translation(self):
        try:
            file_type = self.file_type.get()
            
            # إنشاء مسارات الملفات
            file_root, file_ext = os.path.splitext(self.filepath)
            translated_file = f"{file_root}_translated{file_ext}"
            reversed_file = f"{file_root}_translated_reversed{file_ext}"
            
            # عمل نسخة احتياطية إذا تم تحديد الخيار
            if self.backup_var.get():
                backup_file = f"{file_root}_backup{file_ext}"
                import shutil
                shutil.copy2(self.filepath, backup_file)
                self.update_results(f"تم إنشاء نسخة احتياطية: {backup_file}")

            # معالجة الملف حسب نوعه
            if file_type == "yml":
                self.translate_yml(translated_file, reversed_file)
            else:
                self.translate_xml(translated_file, reversed_file)

            self.files_processed += 1
            self.update_status("اكتملت الترجمة")
            messagebox.showinfo("نجاح", "تمت الترجمة وحفظ الملفات بنجاح")

        except Exception as e:
            logging.error(f"Translation error: {str(e)}")
            self.update_status("حدث خطأ")
            messagebox.showerror("خطأ", str(e))
        finally:
            self.processing = False
            self.translate_button.configure(state="normal")
            self.progress_bar.set(1)

    def translate_yml(self, translated_file, reversed_file):
        try:
            with open(self.filepath, 'r', encoding='utf-8-sig') as file:
                lines = file.readlines()

            total_lines = len(lines)
            translated_lines = []
            reversed_lines = []
            
            for i, line in enumerate(lines):
                # تحديث التقدم
                progress = (i + 1) / total_lines
                self.progress_queue.put(progress)
                
                if ':' not in line:
                    translated_lines.append(line)
                    reversed_lines.append(line)
                    continue

                key_part, value_part = line.split(':', 1)
                
                # ترجمة النص
                translated_value = self.smart_translate(value_part)
                translated_lines.append(f"{key_part}:{translated_value}")
                
                # عكس النص العربي إذا تم تحديد الخيار
                if self.reverse_var.get():
                    reversed_value = self.reverse_arabic_text(translated_value)
                    reversed_lines.append(f"{key_part}:{reversed_value}")
                else:
                    reversed_lines.append(f"{key_part}:{translated_value}")

            # حفظ الملفات
            with open(translated_file, 'w', encoding='utf-8-sig') as f:
                f.writelines(translated_lines)
            
            if self.reverse_var.get():
                with open(reversed_file, 'w', encoding='utf-8-sig') as f:
                    f.writelines(reversed_lines)

            self.update_results(f"تم حفظ الملف المترجم: {translated_file}")
            if self.reverse_var.get():
                self.update_results(f"تم حفظ الملف المترجم مع العكس: {reversed_file}")

        except Exception as e:
            raise Exception(f"خطأ في ترجمة ملف YML: {str(e)}")

    def translate_xml(self, translated_file, reversed_file):
        try:
            tree = ET.parse(self.filepath)
            root = tree.getroot()
            
            # نسخة للملف المترجم فقط
            translated_tree = ET.ElementTree(root)
            
            # نسخة للملف المترجم مع العكس
            reversed_root = ET.fromstring(ET.tostring(root, encoding='unicode'))
            reversed_tree = ET.ElementTree(reversed_root)
            
            total_elements = len(root.findall('.//*')) + 1
            processed = 0

            def process_element(elem, reverse=False):
                nonlocal processed
                processed += 1
                progress = processed / (total_elements * (2 if self.reverse_var.get() else 1))
                self.progress_queue.put(progress)

                # معالجة النص داخل العنصر
                if elem.text and elem.text.strip():
                    elem.text = self.smart_translate(elem.text)
                    if reverse:
                        elem.text = self.reverse_arabic_text(elem.text)

                # معالجة السمات
                for attr_name, attr_value in elem.attrib.items():
                    if attr_name != 'id':  # تجاهل معرفات ID
                        translated_attr = self.smart_translate(attr_value)
                        if reverse:
                            translated_attr = self.reverse_arabic_text(translated_attr)
                        elem.attrib[attr_name] = translated_attr

                # معالجة العناصر الفرعية
                for child in elem:
                    process_element(child, reverse)

            # معالجة الملف المترجم
            process_element(root, False)
            translated_tree.write(translated_file, encoding='utf-8', xml_declaration=True)
            
            # معالجة الملف المترجم مع العكس إذا تم تحديد الخيار
            if self.reverse_var.get():
                process_element(reversed_root, True)
                reversed_tree.write(reversed_file, encoding='utf-8', xml_declaration=True)

            self.update_results(f"تم حفظ الملف المترجم: {translated_file}")
            if self.reverse_var.get():
                self.update_results(f"تم حفظ الملف المترجم مع العكس: {reversed_file}")

        except Exception as e:
            raise Exception(f"خطأ في ترجمة ملف XML: {str(e)}")

    def smart_translate(self, text):
        """الترجمة الذكية مع استخدام المصطلحات وذاكرة الترجمة"""
        if not text or text.strip() == "":
            return text

        # تجاهل النصوص التي تبدأ برموز خاصة
        if text.strip().startswith(('$', '@', '#', '[', '(', '{', '|', 'GetTrait', 'GetFaith', 'GetReligion')):
            return text

        try:
            # البحث في ذاكرة الترجمة
            from_memory = self.get_from_memory(text)
            if from_memory:
                return from_memory

            # تقسيم النص إلى أجزاء مع الحفاظ على الأكواد الخاصة
            pattern = r'(\$.*?\$|\[.*?\]|@.*?!|#.*?#!|\|.*?\||GetTrait\(.*?\)|GetFaith\(.*?\)|GetReligion\(.*?\)|\(.*?\)|{.*?})'
            parts = re.split(pattern, text)
            
            translated_parts = []
            for part in parts:
                if not part:
                    continue
                    
                if re.match(pattern, part):
                    translated_parts.append(part)
                else:
                    # استخدام المصطلحات إذا كان الخيار مفعل
                    if self.use_terms_var.get():
                        part = self.apply_terms(part)
                    
                    # ترجمة النص
                    translated = GoogleTranslator(source='auto', target=self.settings.get("target_language", "ar")).translate(part.strip())
                    
                    # التدقيق اللغوي
                    if self.spellcheck_var.get():
                        translated = self.spell_check_arabic(translated)
                    
                    translated_parts.append(translated if translated else part)
            
            final_text = ''.join(translated_parts)
            
            # حفظ في ذاكرة الترجمة
            if final_text != text:
                self.save_to_memory(text, final_text)
            
            return final_text
            
        except Exception as e:
            logging.error(f"Translation error: {str(e)}")
            return text

    def apply_terms(self, text):
        """تطبيق المصطلحات على النص"""
        try:
            with open('terms.json', 'r', encoding='utf-8') as f:
                terms = json.load(f)
            
            for eng, ar in terms.items():
                text = re.sub(
                    rf'\b{re.escape(eng)}\b',
                    ar,
                    text,
                    flags=re.IGNORECASE
                )
            
            return text
        except Exception as e:
            logging.error(f"Error applying terms: {str(e)}")
            return text

    def spell_check_arabic(self, text):
        """التدقيق اللغوي للنص العربي"""
        try:
            common_mistakes = {
                'إنشاء': 'إنشاء',
                'انشاء': 'إنشاء',
                'الذى': 'الذي',
                'هذه': 'هذه',
                'فى': 'في',
                'الى': 'إلى',
                'علي': 'على'
            }

            for wrong, correct in common_mistakes.items():
                text = re.sub(
                    rf'\b{wrong}\b',
                    correct,
                    text
                )

            return text
        except Exception as e:
            logging.error(f"Spell check error: {str(e)}")
            return text

    def reverse_arabic_text(self, text):
        """عكس النص العربي مع الحفاظ على الأكواد الخاصة"""
        if not isinstance(text, str):
            return text

        if any('\u0600' <= c <= '\u06FF' for c in text):
            try:
                pattern = r'(\$.*?\$|\[.*?\]|@.*?!|#.*?#!|\|.*?\||GetTrait\(.*?\)|GetFaith\(.*?\)|GetReligion\(.*?\)|\(.*?\)|{.*?})'
                parts = re.split(pattern, text)
                
                processed_parts = []
                for part in parts:
                    if not part:
                        continue
                        
                    if re.match(pattern, part):
                        processed_parts.append(part)
                    else:
                        reshaped = arabic_reshaper.reshape(part)
                        processed_parts.append(get_display(reshaped))
                        
                return ''.join(processed_parts)
            except Exception as e:
                logging.error(f"Error reversing Arabic text: {str(e)}")
                return text
        
        return text

    def save_to_memory(self, source_text, translated_text):
        """حفظ في ذاكرة الترجمة"""
        try:
            with open('translation_memory.json', 'r+', encoding='utf-8') as f:
                memory = json.load(f)
                memory[source_text.strip()] = translated_text.strip()
                f.seek(0)
                json.dump(memory, f, ensure_ascii=False, indent=4)
                f.truncate()
        except Exception as e:
            logging.error(f"Error saving to translation memory: {str(e)}")

    def get_from_memory(self, text):
        """البحث في ذاكرة الترجمة"""
        try:
            with open('translation_memory.json', 'r', encoding='utf-8') as f:
                memory = json.load(f)
                return memory.get(text.strip())
        except Exception as e:
            logging.error(f"Error reading from translation memory: {str(e)}")
            return None

    def show_terms_manager(self):
        """نافذة إدارة المصطلحات"""
        terms_window = ctk.CTkToplevel(self)
        terms_window.title("إدارة المصطلحات")
        terms_window.geometry("600x500")

        terms_frame = ctk.CTkFrame(terms_window)
        terms_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # حقول إضافة مصطلح جديد
        add_frame = ctk.CTkFrame(terms_frame)
        add_frame.pack(fill="x", pady=10)

        eng_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="المصطلح بالإنجليزية",
            font=self.arabic_font_medium
        )
        eng_entry.pack(side="left", padx=5, fill="x", expand=True)

        ar_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="المصطلح بالعربية",
            font=self.arabic_font_medium
        )
        ar_entry.pack(side="left", padx=5, fill="x", expand=True)

        def add_term():
            eng = eng_entry.get().strip()
            ar = ar_entry.get().strip()
            if eng and ar:
                try:
                    with open('terms.json', 'r+', encoding='utf-8') as f:
                        terms = json.load(f)
                        terms[eng] = ar
                        f.seek(0)
                        json.dump(terms, f, ensure_ascii=False, indent=4)
                        f.truncate()
                    
                    eng_entry.delete(0, "end")
                    ar_entry.delete(0, "end")
                    load_terms()
                except Exception as e:
                    messagebox.showerror("خطأ", f"فشل إضافة المصطلح: {str(e)}")

        add_btn = ctk.CTkButton(
            add_frame,
            text="إضافة",
            command=add_term,
            font=self.arabic_font_medium
        )
        add_btn.pack(side="left", padx=5)

        # عرض المصطلحات
        terms_text = ctk.CTkTextbox(
            terms_frame,
            font=self.arabic_font_small
        )
        terms_text.pack(fill="both", expand=True, pady=10)

        def load_terms():
            terms_text.delete("1.0", "end")
            try:
                with open('terms.json', 'r', encoding='utf-8') as f:
                    terms = json.load(f)
                    for eng, ar in terms.items():
                        terms_text.insert("end", f"{eng} => {ar}\n")
            except Exception as e:
                messagebox.showerror("خطأ", f"فشل تحميل المصطلحات: {str(e)}")

        load_terms()

    def show_translation_memory(self):
        """نافذة ذاكرة الترجمة"""
        memory_window = ctk.CTkToplevel(self)
        memory_window.title("ذاكرة الترجمة")
        memory_window.geometry("800x600")

        memory_frame = ctk.CTkFrame(memory_window)
        memory_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # إطار البحث
        search_frame = ctk.CTkFrame(memory_frame)
        search_frame.pack(fill="x", pady=10)

        search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="بحث في ذاكرة الترجمة...",
            font=self.arabic_font_medium
        )
        search_entry.pack(side="left", padx=5, fill="x", expand=True)

        def search_memory():
            search_text = search_entry.get().strip()
            memory_text.delete("1.0", "end")
            try:
                with open('translation_memory.json', 'r', encoding='utf-8') as f:
                    memory = json.load(f)
                    for source, target in memory.items():
                        if search_text.lower() in source.lower() or search_text.lower() in target.lower():
                            memory_text.insert("end", f"الأصل: {source}\nالترجمة: {target}\n{'='*50}\n")
            except Exception as e:
                messagebox.showerror("خطأ", f"فشل البحث: {str(e)}")

        search_btn = ctk.CTkButton(
            search_frame,
            text="بحث",
            command=search_memory,
            font=self.arabic_font_medium
        )
        search_btn.pack(side="left", padx=5)

        clear_btn = ctk.CTkButton(
            search_frame,
            text="مسح الكل",
            command=lambda: self.clear_translation_memory(memory_text),
            font=self.arabic_font_medium
        )
        clear_btn.pack(side="left", padx=5)

        # عرض الذاكرة
        memory_text = ctk.CTkTextbox(
            memory_frame,
            font=self.arabic_font_small
        )
        memory_text.pack(fill="both", expand=True, pady=10)

        def load_memory():
            memory_text.delete("1.0", "end")
            try:
                with open('translation_memory.json', 'r', encoding='utf-8') as f:
                    memory = json.load(f)
                    for source, target in memory.items():
                        memory_text.insert("end", f"الأصل: {source}\nالترجمة: {target}\n{'='*50}\n")
            except Exception as e:
                messagebox.showerror("خطأ", f"فشل تحميل الذاكرة: {str(e)}")

        load_memory()

    def clear_translation_memory(self, text_widget=None):
        """مسح ذاكرة الترجمة"""
        if messagebox.askyesno("تأكيد", "هل أنت متأكد من مسح ذاكرة الترجمة؟"):
            try:
                with open('translation_memory.json', 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=4)
                if text_widget:
                    text_widget.delete("1.0", "end")
                messagebox.showinfo("نجاح", "تم مسح ذاكرة الترجمة")
            except Exception as e:
                messagebox.showerror("خطأ", f"فشل مسح الذاكرة: {str(e)}")

    def show_settings(self):
        """نافذة الإعدادات"""
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("الإعدادات")
        settings_window.geometry("400x500")
        settings_window.resizable(False, False)

        settings_frame = ctk.CTkFrame(settings_window)
        settings_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # إعدادات المظهر
        appearance_label = ctk.CTkLabel(
            settings_frame,
            text="المظهر:",
            font=self.arabic_font_medium
        )
        appearance_label.pack(pady=(0, 5), anchor="w")

        theme_var = ctk.StringVar(value=self.settings.get("theme", "dark"))
        theme_menu = ctk.CTkOptionMenu(
            settings_frame,
            values=["light", "dark", "system"],
            variable=theme_var,
            command=lambda x: self.change_theme(x),
            font=self.arabic_font_medium
        )
        theme_menu.pack(fill="x", pady=(0, 10))

        # إعدادات اللغة
        language_label = ctk.CTkLabel(
            settings_frame,
            text="لغة الترجمة:",
            font=self.arabic_font_medium
        )
        language_label.pack(pady=(10, 5), anchor="w")

        languages = {
            "العربية": "ar",
            "English": "en",
            "Français": "fr",
            "Español": "es",
            "Deutsch": "de",
            "中文": "zh",
            "日本語": "ja",
            "한국어": "ko",
            "Русский": "ru"
        }

        language_var = ctk.StringVar(value=[k for k, v in languages.items() if v == self.settings.get("target_language", "ar")][0])
        language_menu = ctk.CTkOptionMenu(
            settings_frame,
            values=list(languages.keys()),
            variable=language_var,
            font=self.arabic_font_medium
        )
        language_menu.pack(fill="x", pady=(0, 10))

        # الإعدادات الافتراضية
        defaults_label = ctk.CTkLabel(
            settings_frame,
            text="الإعدادات الافتراضية:",
            font=self.arabic_font_medium
        )
        defaults_label.pack(pady=(10, 5), anchor="w")

        default_options = [
            ("استخدام المصطلحات", "use_terms"),
            ("التدقيق اللغوي", "spellcheck"),
            ("عكس النصوص العربية", "reverse_arabic"),
            ("نسخة احتياطية", "create_backup")
        ]

        default_vars = {}
        for text, key in default_options:
            var = ctk.BooleanVar(value=self.settings.get(key, True))
            default_vars[key] = var
            check = ctk.CTkCheckBox(
                settings_frame,
                text=text,
                variable=var,
                font=self.arabic_font_medium
            )
            check.pack(pady=5, anchor="w")

        def save_settings():
            self.settings["theme"] = theme_var.get()
            self.settings["target_language"] = languages[language_var.get()]
            for key, var in default_vars.items():
                self.settings[key] = var.get()
            self.save_settings()
            settings_window.destroy()
            messagebox.showinfo("نجاح", "تم حفظ الإعدادات")

        save_btn = ctk.CTkButton(
            settings_frame,
            text="حفظ الإعدادات",
            command=save_settings,
            font=self.arabic_font_medium
        )
        save_btn.pack(pady=20)

    def show_about(self):
        """نافذة حول البرنامج"""
        about_window = ctk.CTkToplevel(self)
        about_window.title("حول البرنامج")
        about_window.geometry("400x450")
        about_window.resizable(False, False)

        info_frame = ctk.CTkFrame(about_window)
        info_frame.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(
            info_frame,
            text="المترجم الذكي المتقدم",
            font=self.arabic_font_large
        ).pack(pady=10)

        ctk.CTkLabel(
            info_frame,
            text="الإصدار 2.0",
            font=self.arabic_font_medium
        ).pack()

        info_text = """
        برنامج متقدم لترجمة ومعالجة ملفات YML و XML
        مع دعم كامل للغة العربية وعكس النصوص.

        المميزات:
        • ترجمة ذكية مع تجاهل الأكواد الخاصة
        • دعم عكس النصوص العربية
        • حفظ نسخ متعددة من الملفات
        • واجهة مستخدم متقدمة وسهلة الاستخدام
        • دعم للغات متعددة
        • قاموس مصطلحات قابل للتخصيص
        • ذاكرة ترجمة للنصوص المتكررة
        • تدقيق لغوي للنصوص العربية
        """
        
        ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=self.arabic_font_small,
            justify="center"
        ).pack(pady=10)

    def show_help(self):
        """نافذة المساعدة"""
        help_text = """
        كيفية الاستخدام:
        1. اختر نوع الملف (YML أو XML)
        2. حدد خيارات المعالجة:
           • استخدام المصطلحات: للترجمة المتناسقة
           • التدقيق اللغوي: لتصحيح الأخطاء الشائعة
           • عكس النصوص: لدعم الكتابة من اليمين لليسار
           • نسخة احتياطية: للحفاظ على الملف الأصلي
        3. اختر الملف المراد ترجمته
        4. اضغط على زر 'ترجمة وحفظ'
        5. انتظر حتى اكتمال المعالجة

        مميزات إضافية:
        • إدارة المصطلحات: لإضافة وتعديل المصطلحات التقنية
        • ذاكرة الترجمة: لحفظ واسترجاع الترجمات السابقة
        • تصدير القواميس: لمشاركة قواعد البيانات

        ملاحظات مهمة:
        • يتم تجاهل الأكواد الخاصة مثل $, @, #, [, (, {
        • يمكن تغيير لغة الترجمة من الإعدادات
        • يتم إنشاء ملفين عند تفعيل خيار عكس النصوص
        • يمكن استعادة الملف الأصلي من النسخة الاحتياطية
        """
        messagebox.showinfo("المساعدة", help_text)

    def show_main(self):
        """العودة للواجهة الرئيسية"""
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkToplevel):
                widget.destroy()

    def change_theme(self, theme):
        """تغيير مظهر البرنامج"""
        ctk.set_appearance_mode(theme)
        self.settings["theme"] = theme
        self.save_settings()

    def monitor_progress(self):
        """مراقبة تقدم المعالجة"""
        try:
            while not self.progress_queue.empty():
                progress = self.progress_queue.get_nowait()
                self.progress_bar.set(progress)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.monitor_progress)

    def update_results(self, text):
        """تحديث مربع النتائج"""
        self.results_text.insert("end", text + "\n")
        self.results_text.see("end")

    def update_status(self, text):
        """تحديث شريط الحالة"""
        self.status_label.configure(text=text)
        self.files_label.configure(text=f"الملفات المعالجة: {self.files_processed}")

if __name__ == "__main__":
    try:
        app = SmartArabicTranslator()
        app.mainloop()
    except Exception as e:
        logging.critical(f"Critical error: {str(e)}")
        messagebox.showerror("خطأ", f"حدث خطأ غير متوقع: {str(e)}")