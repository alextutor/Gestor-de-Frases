import customtkinter as ctk
import tkinter as tk
import keyboard
import time
import threading
import sqlite3
import ctypes
from datetime import datetime

# ==========================================
# GESTIÓN DE PALETAS COMERCIALES PREMIUM (v12)
# ==========================================
PALETAS = {
    "Slate Corporate": {"mode": "dark", "color": "blue"},
    "Emerald Obsidian": {"mode": "dark", "color": "green"},
    "Steel Amber": {"mode": "dark", "color": "dark-blue"},
    "Classic Light": {"mode": "light", "color": "blue"}
}

# ==========================================
# ESTADO GLOBAL DE LA APLICACIÓN
# ==========================================
id_prompt_actual = None
CONFIG_MODO_DETECCION = "teclado"
TEMA_ACTUAL = "Slate Corporate"
frame_lista_global = None  
PROMPTS_CACHE = []         

DESCRIPCIONES = {
    "teclado": (
        "MÉTODO RECOMENDADO (Bajo Consumo - 100% Preciso)\n\n"
        "Usa atajos del teclado para controlar el envío:\n"
        "• Ctrl + , -> Inyección estándar (Modo Documento).\n"
        "• Ctrl + Shift + , -> Inyección segura para Chat (Shift+Enter).\n\n"
        "Ventajas: Consume 0% CPU, es instantáneo y libre de errores."
    ),
    "automatico": (
        "MÉTODO AUTOMÁTICO (Consumo Medio)\n\n"
        "El sistema analiza la ventana de Windows en primer plano.\n"
        "Si detecta aplicaciones de mensajería (WhatsApp, Slack, Telegram),\n"
        "conmuta de forma inteligente a Modo Chat.\n\n"
        "Nota: Consume un poco más de recursos y puede fallar en entornos web."
    )
}

# ==========================================
# CAPA DE DATOS E INFRAESTRUCTURA (SQLite3)
# ==========================================
def inicializar_db_y_config():
    DB_NAME = "prompts.sqlite"
    conexion = None
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        
        # Tabla de Prompts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                contenido TEXT NOT NULL,
                eliminado_en TEXT DEFAULT NULL
            )
        ''')
        
        # Tabla de Configuración Global Persistente
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        ''')
        
        # Valores por defecto de fábrica
        cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tema', 'Slate Corporate')")
        cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('modo_deteccion', 'teclado')")
        conexion.commit()
    except sqlite3.Error as e:
        print(f"[Error DB Inicialización] {e}")
    finally:
        if conexion:
            conexion.close()

def cargar_configuracion_global():
    global TEMA_ACTUAL, CONFIG_MODO_DETECCION
    DB_NAME = "prompts.sqlite"
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT clave, valor FROM configuracion")
        for clave, valor in cursor.fetchall():
            if clave == "tema": 
                if valor in PALETAS:
                    TEMA_ACTUAL = valor
                else:
                    TEMA_ACTUAL = "Slate Corporate"
                    cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('tema', 'Slate Corporate')")
                    conn.commit()
            if clave == "modo_deteccion": 
                CONFIG_MODO_DETECCION = valor
        conn.close()
    except Exception:
        pass

def guardar_config_db(clave, valor):
    DB_NAME = "prompts.sqlite"
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (clave, valor))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Error guardando config] {e}")

def obtener_texto_prompt(prompt_id):
    DB_NAME = "prompts.sqlite" 
    texto_recuperado = ""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT contenido FROM prompts WHERE id = ?", (prompt_id,))
        res = cursor.fetchone()
        if res: texto_recuperado = res[0]
        conn.close()
    except Exception: pass
    return texto_recuperado

def actualizar_cache_prompts():
    global PROMPTS_CACHE
    DB_NAME = "prompts.sqlite"
    PROMPTS_CACHE = []
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, titulo FROM prompts WHERE eliminado_en IS NULL ORDER BY id ASC")
        for fila in cursor.fetchall():
            PROMPTS_CACHE.append({"id": fila[0], "etiqueta": fila[1]})
        conn.close()
    except Exception: pass

def guardar_nuevo_prompt(titulo, contenido):
    DB_NAME = "prompts.sqlite"
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO prompts (titulo, contenido) VALUES (?, ?)", (titulo, contenido))
        conn.commit()
        conn.close()
    except Exception: pass

def actualizar_prompt(prompt_id, titulo, contenido):
    DB_NAME = "prompts.sqlite"
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE prompts SET titulo = ?, contenido = ? WHERE id = ?", (titulo, contenido, prompt_id))
        conn.commit()
        conn.close()
    except Exception: pass

def ejecutar_borrado_logico_db(prompt_id):
    DB_NAME = "prompts.sqlite"
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE prompts SET eliminado_en = ? WHERE id = ?", (fecha_actual, prompt_id))
        conn.commit()
        conn.close()
    except Exception: pass

# ==========================================
# MOTOR NATIVO DE INYECCIÓN POR HARDWARE
# ==========================================
def obtener_titulo_ventana_activa():
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value.lower()
    except Exception: return ""

def ejecutar_inyeccion_inteligente(texto, forzar_modo_chat=False):
    palabras_clave_chat = ["whatsapp", "slack", "telegram", "teams", "discord"]
    es_entorno_chat = forzar_modo_chat

    if CONFIG_MODO_DETECCION == "automatico" and not es_entorno_chat:
        titulo_ventana = obtener_titulo_ventana_activa()
        if any(app in titulo_ventana for app in palabras_clave_chat):
            es_entorno_chat = True

    if es_entorno_chat:
        lineas = texto.split('\n')
        for i, linea in enumerate(lineas):
            if linea: keyboard.write(linea, delay=0.005)
            if i < len(lineas) - 1:
                keyboard.press_and_release('shift+enter')
                time.sleep(0.01)
    else:
        keyboard.write(texto, delay=0.005)

def ejecutar_disparo_dinamico(prompt_id, ocultar_ventana=True, forzar_modo_chat=False):
    def hilo_proceso():
        texto_raw = obtener_texto_prompt(prompt_id)
        if not texto_raw or not texto_raw.strip(): return
        if ocultar_ventana: root.withdraw()
        time.sleep(0.4)
        try:
            ejecutar_inyeccion_inteligente(texto_raw, forzar_modo_chat)
        except Exception: pass
        finally:
            if ocultar_ventana:
                time.sleep(0.1)
                root.deiconify()
    threading.Thread(target=hilo_proceso, daemon=True).start()

# ==========================================
# FORMULARIO MODAL (CREAR / EDITAR)
# ==========================================
class VentanaFormulario(ctk.CTkToplevel):
    def __init__(self, master, prompt_id=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.prompt_id = prompt_id
        self.title("Nuevo Prompt" if not prompt_id else "Editar Prompt")
        self.geometry("400x450")
        self.transient(master)
        self.grab_set()
        
        ctk.CTkLabel(self, text="Título del Prompt:", font=("Arial", 12, "bold")).pack(pady=(15, 2), padx=20, anchor="w")
        self.txt_titulo = ctk.CTkEntry(self, width=360)
        self.txt_titulo.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkLabel(self, text="Contenido:", font=("Arial", 12, "bold")).pack(pady=(10, 2), padx=20, anchor="w")
        self.txt_contenido = ctk.CTkTextbox(self, width=360, height=220)
        self.txt_contenido.pack(pady=5, padx=20, fill="both", expand=True)
        
        ctk.CTkButton(self, text="Guardar Cambios", command=self.procesar_datos).pack(pady=20)
        
        if self.prompt_id:
            self.cargar_datos_existentes()

    def cargar_datos_existentes(self):
        titulo_actual = next((r["etiqueta"] for r in PROMPTS_CACHE if r["id"] == self.prompt_id), "")
        contenido_actual = obtener_texto_prompt(self.prompt_id)
        self.txt_titulo.insert(0, titulo_actual)
        self.txt_contenido.insert("1.0", contenido_actual)

    def procesar_datos(self):
        titulo = self.txt_titulo.get().strip()
        contenido = self.txt_contenido.get("1.0", ctk.END).strip()
        
        if not titulo or not contenido: return
            
        if self.prompt_id:
            actualizar_prompt(self.prompt_id, titulo, contenido)
        else:
            guardar_nuevo_prompt(titulo, contenido)
            
        actualizar_cache_prompts()  
        filtrar_prompts_ui()         
        self.destroy()

# ==========================================
# INTERFAZ MODAL DE CONFIRMACIÓN SEGURA
# ==========================================
class ModalConfirmarEliminacion(ctk.CTkToplevel):
    def __init__(self, master, prompt_id, titulo_prompt, callback_exito, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.prompt_id = prompt_id
        self.callback_exito = callback_exito
        
        self.title("Confirmar Eliminación")
        self.geometry("420x170")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        x = master.winfo_x() + (master.winfo_width() // 2) - 210
        y = master.winfo_y() + (master.winfo_height() // 2) - 85
        self.geometry(f"+{x}+{y}")
        
        lbl_msg = ctk.CTkLabel(self, text=f"¿Estás seguro de enviar a la papelera el prompt?\n\n\"{titulo_prompt}\"", wraplength=380, justify="center")
        lbl_msg.pack(pady=20, padx=20)
        
        frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones.pack(pady=10)
        
        btn_cancelar = ctk.CTkButton(frame_botones, text="Cancelar", fg_color="#555555", hover_color="#444444", command=self.destroy)
        btn_cancelar.pack(side="left", padx=10)
        btn_cancelar.focus_set()
        
        btn_confirmar = ctk.CTkButton(frame_botones, text="Eliminar", fg_color="#D32F2F", hover_color="#B71C1C", command=self.confirmar)
        btn_confirmar.pack(side="left", padx=10)

    def confirmar(self):
        ejecutar_borrado_logico_db(self.prompt_id)
        self.callback_exito(self.prompt_id)
        self.destroy()

# ==========================================
# VENTANA FLOTANTE: CONTROL PREVENTIVO DE CHATS
# ==========================================
class VentanaControlPreventivo(ctk.CTkToplevel):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.title("Configuración Detección de Chats")
        self.geometry("380x300")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        x = master.winfo_x() + (master.winfo_width() // 2) - 190
        y = master.winfo_y() + (master.winfo_height() // 2) - 150
        self.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(self, text="Mecanismo de Control Preventivo", font=("Arial", 14, "bold")).pack(pady=10)
        
        self.txt_desc = ctk.CTkTextbox(self, height=120, width=340, wrap="word")
        self.txt_desc.pack(pady=5, padx=15)
        self.txt_desc.insert("1.0", DESCRIPCIONES[CONFIG_MODO_DETECCION])
        self.txt_desc.configure(state="disabled")
        
        self.var_modo = ctk.StringVar(value=CONFIG_MODO_DETECCION)
        
        ctk.CTkRadioButton(self, text="Tecla Modificadora (Recomendado)", variable=self.var_modo, value="teclado",
                           command=self.actualizar_modo).pack(anchor="w", padx=25, pady=5)
        ctk.CTkRadioButton(self, text="Detección Automática de Ventanas", variable=self.var_modo, value="automatico",
                           command=self.actualizar_modo).pack(anchor="w", padx=25, pady=5)
                           
    def actualizar_modo(self):
        nuevo_modo = self.var_modo.get()
        guardar_config_db("modo_deteccion", nuevo_modo)
        global CONFIG_MODO_DETECCION
        CONFIG_MODO_DETECCION = nuevo_modo
        
        self.txt_desc.configure(state="normal")
        self.txt_desc.delete("1.0", ctk.END)
        self.txt_desc.insert("1.0", DESCRIPCIONES[nuevo_modo])
        self.txt_desc.configure(state="disabled")

# ==========================================
# INTERFAZ Y LOGICA COMPLEMENTARIA (FILTRADO UI)
# ==========================================
def seleccionar_prompt(id_seleccionado, boton_asociado, frame_contenedor):
    global id_prompt_actual
    id_prompt_actual = id_seleccionado
    for child in frame_contenedor.winfo_children():
        if isinstance(child, ctk.CTkFrame):
            for sub_child in child.winfo_children():
                if isinstance(sub_child, ctk.CTkButton) and sub_child.cget("anchor") == "w":
                    sub_child.configure(fg_color="transparent")
    boton_asociado.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])

def al_eliminar_exitoso(prompt_id):
    global id_prompt_actual
    if id_prompt_actual == prompt_id:
        id_prompt_actual = None
    actualizar_cache_prompts()
    filtrar_prompts_ui()

def abrir_editor_directo(prompt_id):
    VentanaFormulario(root, prompt_id=prompt_id)

def abrir_confirmacion_directa(prompt_id, titulo_prompt):
    ModalConfirmarEliminacion(root, prompt_id, titulo_prompt, al_eliminar_exitoso)

def filtrar_prompts_ui(event=None):
    global frame_lista_global, txt_buscar
    for widget in frame_lista_global.winfo_children(): widget.destroy()
    texto_busqueda = txt_buscar.get().strip().lower()
    resultados = [p for p in PROMPTS_CACHE if texto_busqueda in p["etiqueta"].lower()]
    
    if not resultados:
        ctk.CTkLabel(frame_lista_global, text="Sin coincidencias", text_color="gray", font=("Arial", 12, "italic")).pack(pady=20)
        return

    for reg in resultados:
        reg_id = reg["id"]
        reg_titulo = reg["etiqueta"]
        
        # Fila horizontal inline
        fila_frame = ctk.CTkFrame(frame_lista_global, fg_color="transparent")
        fila_frame.pack(fill="x", pady=2, padx=5)
        
        btn_sel = ctk.CTkButton(fila_frame, text=reg_titulo, anchor="w", fg_color="transparent")
        if id_prompt_actual == reg_id:
            btn_sel.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
            
        btn_sel.configure(command=lambda r_id=reg_id, b=btn_sel: seleccionar_prompt(r_id, b, frame_lista_global))
        btn_sel.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        # Botón Inline: [✎] Editar
        btn_edit = ctk.CTkButton(fila_frame, text="✎", width=32, height=28, fg_color="#2b2b2b", hover_color="#3e3e3e",
                                 command=lambda r_id=reg_id: abrir_editor_directo(r_id))
        btn_edit.pack(side="left", padx=2)
        
        # Botón Inline: [✕] Eliminar
        btn_del = ctk.CTkButton(fila_frame, text="✕", width=32, height=28, fg_color="#D32F2F", hover_color="#B71C1C",
                                command=lambda r_id=reg_id, t=reg_titulo: abrir_confirmacion_directa(r_id, t))
        btn_del.pack(side="left", padx=(2, 0))

def cambiar_tema_aplicacion(nombre_tema):
    if nombre_tema in PALETAS:
        guardar_config_db("tema", nombre_tema)
        ctk.set_appearance_mode(PALETAS[nombre_tema]["mode"])
        ctk.set_default_color_theme(PALETAS[nombre_tema]["color"])

def alternar_visibilidad_ventana(event=None):
    try:
        if root.state() == "iconic" or not root.focus_displayof():
            root.deiconify()
            root.state("normal")
            root.attributes("-topmost", True)
            root.attributes("-topmost", False)
            txt_buscar.focus_set()
        else:
            root.iconify()
    except Exception: pass

def ocultar_por_escape(event=None):
    root.iconify()

def abrir_creador():
    VentanaFormulario(root, prompt_id=None)

def puente_de_disparo():
    if id_prompt_actual is not None:
        ejecutar_disparo_dinamico(id_prompt_actual, ocultar_ventana=True)

# ==========================================
# ENSAMBLAJE FINAL CON BARRA DE MENÚ TRADICIONAL
# ==========================================
def iniciar_aplicacion():
    global root, frame_lista_global, txt_buscar
    
    inicializar_db_y_config()
    cargar_configuracion_global()
    
    ctk.set_appearance_mode(PALETAS[TEMA_ACTUAL]["mode"])
    ctk.set_default_color_theme(PALETAS[TEMA_ACTUAL]["color"])
    
    root = ctk.CTk()
    root.title("PromptVault v23")
    root.geometry("450x540")
    
    actualizar_cache_prompts()
    
    # Barra de Menú Tradicional
    menu_barra = tk.Menu(root)
    
    menu_archivo = tk.Menu(menu_barra, tearoff=0)
    menu_archivo.add_command(label="Salir de la App", command=root.quit)
    menu_barra.add_cascade(label="Archivo", menu=menu_archivo)
    
    menu_config = tk.Menu(menu_barra, tearoff=0)
    submenu_temas = tk.Menu(menu_config, tearoff=0)
    for tema in PALETAS.keys():
        submenu_temas.add_command(label=tema, command=lambda t=tema: cambiar_tema_aplicacion(t))
    
    menu_config.add_cascade(label="Temas Comerciales", menu=submenu_temas)
    menu_config.add_separator()
    menu_config.add_command(label="Control Preventivo de Chats...", command=lambda: VentanaControlPreventivo(root))
    
    menu_barra.add_cascade(label="Configuración", menu=menu_config)
    root.config(menu=menu_barra)
    
    # Layout Principal
    frame_izq = ctk.CTkFrame(root)
    frame_izq.pack(fill="both", expand=True, padx=15, pady=15)
    
    frame_header = ctk.CTkFrame(frame_izq, fg_color="transparent")
    frame_header.pack(fill="x", pady=(10, 5), padx=10)
    ctk.CTkLabel(frame_header, text="Mis Frases Guardadas", font=("Arial", 14, "bold")).pack(side="left")
    
    txt_buscar = ctk.CTkEntry(frame_izq, placeholder_text="Buscar por título...")
    txt_buscar.pack(fill="x", padx=10, pady=5)
    txt_buscar.bind("<KeyRelease>", filtrar_prompts_ui)
    
    frame_lista_global = ctk.CTkScrollableFrame(frame_izq, fg_color="transparent")
    frame_lista_global.pack(fill="both", expand=True, padx=5, pady=5)
    
    filtrar_prompts_ui()
    
    # --- PANEL INFERIOR DE ACCIONES ---
    frame_acciones = ctk.CTkFrame(frame_izq, fg_color="transparent")
    frame_acciones.pack(fill="x", pady=(10, 15), padx=10)
    
    # Botón Nuevo en parte inferior izquierda
    btn_nuevo = ctk.CTkButton(frame_acciones, text="[+] Nuevo Prompt", fg_color="#2b2b2b", hover_color="#3e3e3e", width=140, command=abrir_creador)
    btn_nuevo.pack(side="left")
    
    # Botón de Inyección Manual ocupando el resto
    btn_inyectar = ctk.CTkButton(frame_acciones, text="Inyectar Selección Manual", command=puente_de_disparo)
    btn_inyectar.pack(side="right", fill="x", expand=True, padx=(10, 0))
    
    # Mapeos de Teclado Global/Local
    keyboard.add_hotkey('ctrl+comma', lambda: alternar_visibilidad_ventana())
    root.bind("<Escape>", ocultar_por_escape)
    
    root.mainloop()

if __name__ == "__main__":
    iniciar_aplicacion()