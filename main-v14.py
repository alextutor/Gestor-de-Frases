import sqlite3
import threading
import time
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import keyboard
import ctypes

# =====================================================================
# REGÍON 1: CONFIGURACIÓN Y BASE DE DATOS (SQLite3 + Tags Indexados)
# =====================================================================

DB_NAME = "promptvault.db"

def init_db():
    """Inicializa la base de datos con el esquema de la v13."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabla principal de frases
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            description TEXT
        )
    """)
    
    # Tabla de etiquetas (Tags)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    
    # Tabla intermedia (Muchos a Muchos) con índice para optimizar búsquedas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompt_tags (
            prompt_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (prompt_id, tag_id),
            FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    """)
    
    # Índice para acelerar el filtrado por tags en la UI de doble altura
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prompt_tags_tag ON prompt_tags(tag_id)")
    
    conn.commit()
    conn.close()

# =====================================================================
# REGIÓN 2: MOTOR DE ESCUCHA SEGURO (Listener v14 para ctrl+comma)
# =====================================================================

class HotkeyManager:
    def __init__(self, trigger_callback):
        self.trigger_callback = trigger_callback
        self.listener_thread = None
        self.running = False

    def _safe_hotkey_handler(self, event):
        """
        Handler del hook de bajo nivel. Filtra por código de tecla (scan code)
        o nombre seguro para evitar el crash ValueError de la coma nativa.
        """
        if keyboard.is_pressed('ctrl') and (event.name == 'comma' or event.scan_code == 51):
            if event.event_type == keyboard.KEY_DOWN:
                self.trigger_callback()

    def _run_listener(self):
        """Hilo secundario que ejecuta el hook de forma aislada."""
        keyboard.hook(self._safe_hotkey_handler)
        while self.running:
            time.sleep(0.1)
        keyboard.unhook(self._safe_hotkey_handler)

    def start(self):
        """Inicia el listener en un hilo dedicado para no congelar la UI."""
        if not self.running:
            self.running = True
            self.listener_thread = threading.Thread(target=self._run_listener, daemon=True)
            self.listener_thread.start()

    def stop(self):
        """Detiene el listener limpiamente."""
        self.running = False

# =====================================================================
# REGIÓN 3: LÓGICA DE INYECCIÓN POR HARDWARE (ctypes / Emulación Nativa)
# =====================================================================

SHORT = ctypes.c_short
WORD = ctypes.c_ushort
DWORD = ctypes.c_ulong
ULONG_PTR = ctypes.c_ulong

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", WORD),
        ("wScan", WORD),
        ("dwFlags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", ULONG_PTR)
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", DWORD),
        ("u", INPUT_UNION)
    ]

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

def SendUnicodeChar(ch):
    """Inyecta un carácter Unicode simulando pulsación de hardware nativa."""
    inputs = (INPUT * 2)()
    
    inputs[0].type = INPUT_KEYBOARD
    inputs[0].u.ki.wVk = 0
    inputs[0].u.ki.wScan = ord(ch)
    inputs[0].u.ki.dwFlags = KEYEVENTF_UNICODE
    
    inputs[1].type = INPUT_KEYBOARD
    inputs[1].u.ki.wVk = 0
    inputs[1].u.ki.wScan = ord(ch)
    inputs[1].u.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    
    ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))

def inject_text(text):
    """Recorre la cadena e inyecta carácter por carácter de forma veloz."""
    for char in text:
        SendUnicodeChar(char)
        time.sleep(0.005)

# =====================================================================
# REGIÓN 4: INTERFAZ GRÁFICA COMPLETA (CustomTkinter Slate Corporate)
# =====================================================================

class PromptVaultApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración de Ventana
        self.title("PromptVault - Asistente de Inyección HW v14")
        self.geometry("900x600")
        self.minsize(800, 500)
        
        # Tema Slate Corporate
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Inicializar Base de Datos y Listener
        init_db()
        self.hotkey_manager = HotkeyManager(self.on_hotkey_triggered)
        self.hotkey_manager.start()

        # Variable de control para edición en el CRUD
        self.selected_prompt_id = None

        # Layout Split View
        self.grid_columnconfigure(0, weight=4, minsize=450)
        self.grid_columnconfigure(1, weight=3, minsize=350)
        self.grid_rowconfigure(0, weight=1)

        # Atajo rápido local para ocultar con Esc
        self.bind("<Escape>", lambda e: self.withdraw())

        # Construir contenedores estructurados
        self.setup_layout_skeletons()

    def setup_layout_skeletons(self):
        """Prepara e inicializa los paneles izquierdo y derecho."""
        self.left_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        
        self.right_frame = ctk.CTkFrame(self, corner_radius=8, fg_color=("#ebebeb", "#212121"))
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 15), pady=15)

        # Construir componentes internos de inmediato
        self.setup_left_panel()

    # =====================================================================
    # REGÍON 4.1: COMPONENTE PANEL IZQUIERDO (Buscador, Tags y Doble Altura)
    # =====================================================================

    def setup_left_panel(self):
        """Construye el motor de búsqueda, etiquetas y lista de doble altura."""
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_prompt_list())
        
        self.search_entry = ctk.CTkEntry(
            self.left_frame, 
            placeholder_text="🔍 Buscar por título o contenido (Esc para ocultar)...",
            textvariable=self.search_var,
            height=35
        )
        self.search_entry.pack(fill="x", padx=5, pady=(0, 10))

        self.tags_container = ctk.CTkFrame(self.left_frame, height=40, fg_color="transparent")
        self.tags_container.pack(fill="x", padx=5, pady=(0, 10))
        self.selected_tag_filter = None 

        self.list_canvas_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.list_canvas_frame.pack(fill="both", expand=True, padx=5)

        self.canvas = tk.Canvas(self.list_canvas_frame, bg="#1a1a1a", highlightthickness=0)
        self.scrollbar = ctk.CTkScrollbar(self.list_canvas_frame, orientation="vertical", command=self.canvas.yview)
        
        self.scrollable_frame = ctk.CTkFrame(self.canvas, fg_color="transparent")
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.refresh_tags_bar()
        self.refresh_prompt_list()

    def refresh_tags_bar(self):
        """Trae los tags únicos de la DB y los pinta como píldoras de filtro."""
        for widget in self.tags_container.winfo_children():
            widget.destroy()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM tags ORDER BY name ASC")
        all_tags = cursor.fetchall()
        conn.close()

        btn_all_color = "#1f6aa5" if not self.selected_tag_filter else "#3a3a3a"
        btn_all = ctk.CTkButton(
            self.tags_container, text="Todos", width=60, height=26, corner_radius=12,
            fg_color=btn_all_color, command=lambda: self.filter_by_tag(None)
        )
        btn_all.pack(side="left", padx=(0, 5))

        for tag_id, tag_name in all_tags:
            is_active = (self.selected_tag_filter == tag_id)
            btn_color = "#1f6aa5" if is_active else "#2b2b2b"
            
            btn_tag = ctk.CTkButton(
                self.tags_container, text=f"#{tag_name}", height=26, corner_radius=12,
                fg_color=btn_color, hover_color="#1f6aa5",
                command=lambda t_id=tag_id: self.filter_by_tag(t_id)
            )
            btn_tag.pack(side="left", padx=3)

    def filter_by_tag(self, tag_id):
        self.selected_tag_filter = tag_id
        self.refresh_tags_bar()
        self.refresh_prompt_list()

    def refresh_prompt_list(self):
        """Pinta los registros de doble altura aplicando búsqueda y filtros."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        search_query = self.search_var.get().strip()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        query = """
            SELECT DISTINCT p.id, p.title, p.content, p.description 
            FROM prompts p
            LEFT JOIN prompt_tags pt ON p.id = pt.prompt_id
        """
        params = []
        conditions = []

        if self.selected_tag_filter:
            conditions.append("pt.tag_id = ?")
            params.append(self.selected_tag_filter)

        if search_query:
            conditions.append("(p.title LIKE ? OR p.content LIKE ? OR p.description LIKE ?)")
            term = f"%{search_query}%"
            params.extend([term, term, term])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY p.id DESC"
        cursor.execute(query, params)
        prompts = cursor.fetchall()
        conn.close()

        for p_id, title, content, desc in prompts:
            row_frame = ctk.CTkFrame(self.scrollable_frame, corner_radius=6, fg_color="#2a2a2a")
            row_frame.pack(fill="x", pady=4, padx=2)

            text_container = ctk.CTkFrame(row_frame, fg_color="transparent")
            # CORREGIDO: Se cambió 'py=8' por 'pady=8'
            text_container.pack(side="left", fill="both", expand=True, padx=10, pady=8)
            
            lbl_title = ctk.CTkLabel(text_container, text=title, font=("Arial", 14, "bold"), anchor="w")
            lbl_title.pack(fill="x")
            
            preview = desc if desc else content
            if len(preview) > 55:
                preview = preview[:52] + "..."
            
            lbl_sub = ctk.CTkLabel(text_container, text=preview, font=("Arial", 11), text_color="#aaaaaa", anchor="w")
            lbl_sub.pack(fill="x")

            btn_inject = ctk.CTkButton(
                row_frame, text="⚡", width=35, height=35, fg_color="#1f6aa5",
                command=lambda txt=content: self.trigger_injection(txt)
            )
            btn_inject.pack(side="right", padx=(5, 10), pady=8)

            btn_edit = ctk.CTkButton(
                row_frame, text="✏️", width=35, height=35, fg_color="#3a3a3a", hover_color="#4a4a4a",
                command=lambda id_p=p_id: self.load_prompt_to_form(id_p)
            )
            btn_edit.pack(side="right", padx=2, pady=8)

            row_frame.bind("<Double-Button-1>", lambda e, txt=content: self.trigger_injection(txt))

    def trigger_injection(self, text):
        self.withdraw()
        time.sleep(0.1)
        inject_text(text)

    def on_hotkey_triggered(self):
        """Despierta la app de manera segura delegando el control mediante after."""
        self.after(0, self._show_and_focus)

    def _show_and_focus(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        self.search_entry.focus()

    # =====================================================================
    # REGÍON 4.2: COMPONENTE PANEL DERECHO (Formulario CRUD Completo)
    # =====================================================================

    def setup_right_panel(self):
        """Construye los campos de texto y botones de acción del CRUD."""
        self.form_title = ctk.CTkLabel(self.right_frame, text="Gestión de Frase", font=("Arial", 16, "bold"))
        self.form_title.pack(pady=(15, 15), padx=15, anchor="w")

        ctk.CTkLabel(self.right_frame, text="Título:", font=("Arial", 12, "bold")).pack(padx=15, anchor="w")
        self.ent_title = ctk.CTkEntry(self.right_frame, placeholder_text="Ej: Saludo Formal")
        self.ent_title.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(self.right_frame, text="Descripción Corta:", font=("Arial", 12, "bold")).pack(padx=15, anchor="w")
        self.ent_desc = ctk.CTkEntry(self.right_frame, placeholder_text="Ej: Atajo para correos institucionales")
        self.ent_desc.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(self.right_frame, text="Tags (separados por coma):", font=("Arial", 12, "bold")).pack(padx=15, anchor="w")
        self.ent_tags = ctk.CTkEntry(self.right_frame, placeholder_text="Ej: correo, trabajo, urgente")
        self.ent_tags.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(self.right_frame, text="Contenido a Inyectar:", font=("Arial", 12, "bold")).pack(padx=15, anchor="w")
        self.txt_content = ctk.CTkTextbox(self.right_frame, height=150)
        self.txt_content.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.btn_container = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.btn_container.pack(fill="x", padx=15, pady=(0, 15))

        self.btn_save = ctk.CTkButton(self.btn_container, text="Guardar", fg_color="#1f6aa5", command=self.save_prompt)
        self.btn_save.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_clear = ctk.CTkButton(self.btn_container, text="Limpiar", fg_color="#3a3a3a", hover_color="#4a4a4a", command=self.clear_form)
        self.btn_clear.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_delete = ctk.CTkButton(self.btn_container, text="Eliminar", fg_color="#721c24", hover_color="#a71d2a", command=self.delete_prompt)
        self.btn_delete.pack_forget()

    def load_prompt_to_form(self, prompt_id):
        self.clear_form()
        self.selected_prompt_id = prompt_id

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT title, description, content FROM prompts WHERE id = ?", (prompt_id,))
        prompt = cursor.fetchone()
        
        if prompt:
            title, desc, content = prompt
            self.ent_title.insert(0, title)
            self.ent_desc.insert(0, desc if desc else "")
            self.txt_content.insert("1.0", content)
            
            cursor.execute("""
                SELECT t.name FROM tags t
                JOIN prompt_tags pt ON t.id = pt.tag_id
                WHERE pt.prompt_id = ?
            """, (prompt_id,))
            tags = [row[0] for row in cursor.fetchall()]
            self.ent_tags.insert(0, ", ".join(tags))
            
            self.form_title.configure(text="Editando Frase ✏️")
            self.btn_delete.pack(side="left", fill="x", expand=True, padx=(5, 0))
            
        conn.close()

    def save_prompt(self):
        title = self.ent_title.get().strip()
        desc = self.ent_desc.get().strip()
        content = self.txt_content.get("1.0", "end-1c").strip()
        tags_raw = self.ent_tags.get().strip()

        if not title or not content:
            messagebox.showwarning("Campos vacíos", "El título y el contenido son obligatorios.")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        if self.selected_prompt_id:
            cursor.execute("""
                UPDATE prompts SET title = ?, description = ?, content = ? WHERE id = ?
            """, (title, desc, content, self.selected_prompt_id))
            prompt_id = self.selected_prompt_id
            cursor.execute("DELETE FROM prompt_tags WHERE prompt_id = ?", (prompt_id,))
        else:
            cursor.execute("""
                INSERT INTO prompts (title, description, content) VALUES (?, ?, ?)
            """, (title, desc, content))
            prompt_id = cursor.lastrowid

        if tags_raw:
            tags_list = list(set([t.strip().lower() for t in tags_raw.split(",") if t.strip()]))
            for tag_name in tags_list:
                cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
                cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                tag_id = cursor.fetchone()[0]
                cursor.execute("INSERT OR IGNORE INTO prompt_tags (prompt_id, tag_id) VALUES (?, ?)", (prompt_id, tag_id))

        conn.commit()
        conn.close()

        self.cleanup_orphaned_tags()
        self.clear_form()
        self.refresh_tags_bar()
        self.refresh_prompt_list()

    def delete_prompt(self):
        if self.selected_prompt_id:
            if messagebox.askyesno("Confirmar", "¿Seguro que deseas eliminar esta frase de forma permanente?"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM prompts WHERE id = ?", (self.selected_prompt_id,))
                conn.commit()
                conn.close()
                
                self.cleanup_orphaned_tags()
                self.clear_form()
                self.refresh_tags_bar()
                self.refresh_prompt_list()

    def cleanup_orphaned_tags(self):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tags WHERE id NOT IN (SELECT DISTINCT tag_id FROM prompt_tags)")
        conn.commit()
        conn.close()

    def clear_form(self):
        self.selected_prompt_id = None
        self.ent_title.delete(0, "end")
        self.ent_desc.delete(0, "end")
        self.ent_tags.delete(0, "end")
        self.txt_content.delete("1.0", "end")
        
        self.form_title.configure(text="Gestión de Frase")
        self.btn_delete.pack_forget()

    def on_closing(self):
        self.hotkey_manager.stop()
        self.destroy()

# =====================================================================
# PUNTO DE ENTRADA PRINCIPAL DE LA APLICACIÓN
# =====================================================================
if __name__ == "__main__":
    app = PromptVaultApp()
    app.setup_right_panel()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()