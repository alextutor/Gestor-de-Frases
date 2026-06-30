import customtkinter as ctk
import sqlite3
import re
import time
import keyboard
import pygetwindow as gw
import ctypes

# =====================================================================
# 1. GESTIÓN DE PALETAS COMERCIALES PREMIUM
# =====================================================================
PALETAS = {
    "Slate Corporate": {
        "bg_main": "#0B0F19",
        "bg_surface": "#111827",
        "bg_input": "#1F2937",
        "border": "#374151",
        "accent": "#2563EB",
        "text_primary": "#F9FAFB",
        "text_muted": "#9CA3AF"
    },
    "Emerald Obsidian": {
        "bg_main": "#0A0A0A",
        "bg_surface": "#171717",
        "bg_input": "#262626",
        "border": "#404040",
        "accent": "#10B981",
        "text_primary": "#FAFAFA",
        "text_muted": "#A3A3A3"
    },
    "Steel Amber": {
        "bg_main": "#1E2022",
        "bg_surface": "#2B2D30",
        "bg_input": "#3F4245",
        "border": "#4E5154",
        "accent": "#F59E0B",
        "text_primary": "#F3F4F6",
        "text_muted": "#9CA3AF"
    },
    "Azul Ejecutivo": {
        "bg_main": "#0F172A",
        "bg_surface": "#1E293B",
        "bg_input": "#334155",
        "border": "#475569",
        "accent": "#3B82F6",
        "text_primary": "#F8FAFC",
        "text_muted": "#94A3B8"
    },
    "Verde Tecnológico": {
        "bg_main": "#051614",
        "bg_surface": "#0A2623",
        "bg_input": "#103A35",
        "border": "#1A5C54",
        "accent": "#14B8A6",
        "text_primary": "#E6F4F1",
        "text_muted": "#71AFA6"
    }
}

FONT_NAME = "Segoe UI"
HOTKEY_GLOBAL = "ctrl+comma"  # Atajo ergonómico global (Estilo PhraseVault)
TEMA_ACTIVO = "Slate Corporate"
COLOR_CONFIG = PALETAS[TEMA_ACTIVO]

def centrar_ventana(ventana, ancho, alto):
    ventana.update_idletasks()
    pantalla_ancho = ventana.winfo_screenwidth()
    pantalla_alto = ventana.winfo_screenheight()
    x = (pantalla_ancho // 2) - (ancho // 2)
    y = (pantalla_alto // 2) - (alto // 2)
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

# =====================================================================
# 2. COMPONENTE: MENSAJES MODALES OSCUROS PERSONALIZADOS
# =====================================================================
class VentanaMensaje(ctk.CTkToplevel):
    def __init__(self, master, titulo, mensaje, tipo="info"):
        super().__init__(master)
        self.master = master
        self.title(titulo)
        self.configure(fg_color=COLOR_CONFIG["bg_main"])
        self.resizable(False, False)
        
        self.resultado = None
        
        container = ctk.CTkFrame(self, fg_color=COLOR_CONFIG["bg_surface"], border_width=1, border_color=COLOR_CONFIG["border"], corner_radius=8)
        container.pack(fill="both", expand=True, padx=15, pady=15)
        
        lbl_msg = ctk.CTkLabel(
            container, text=mensaje, font=(FONT_NAME, 12), 
            text_color=COLOR_CONFIG["text_primary"], wraplength=340, justify="center"
        )
        lbl_msg.pack(fill="both", expand=True, padx=20, pady=(25, 15))
        
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", padx=20, pady=(0, 15))
        
        if tipo == "confirmar":
            btn_no = ctk.CTkButton(
                btn_frame, text="No", fg_color="transparent", border_width=1,
                border_color=COLOR_CONFIG["border"], hover_color=COLOR_CONFIG["bg_input"],
                text_color=COLOR_CONFIG["text_primary"], corner_radius=6, font=(FONT_NAME, 11, "bold"),
                height=32, command=self.accion_no
            )
            btn_no.pack(side="left", expand=True, fill="x", padx=(0, 6))
            
            btn_si = ctk.CTkButton(
                btn_frame, text="Sí", fg_color=COLOR_CONFIG["accent"], 
                hover_color=COLOR_CONFIG["accent"], text_color="#FFFFFF", corner_radius=6, 
                font=(FONT_NAME, 11, "bold"), height=32, command=self.accion_si
            )
            btn_si.pack(side="right", expand=True, fill="x", padx=(6, 0))
        else:
            btn_ok = ctk.CTkButton(
                btn_frame, text="Entendido", fg_color=COLOR_CONFIG["accent"],
                hover_color=COLOR_CONFIG["accent"], text_color="#FFFFFF", corner_radius=6,
                font=(FONT_NAME, 11, "bold"), height=32, command=self.accion_si
            )
            btn_ok.pack(fill="x")
            
        centrar_ventana(self, 380, 160)
        self.grab_set()
        self.master.wait_window(self)
        
    def accion_si(self):
        self.resultado = True
        self.destroy()
        
    def accion_no(self):
        self.resultado = False
        self.destroy()

    @staticmethod
    def mostrar_error(master, titulo, mensaje):
        VentanaMensaje(master, titulo, mensaje, tipo="info")

    @staticmethod
    def pedir_confirmacion(master, titulo, mensaje):
        dialogo = VentanaMensaje(master, titulo, mensaje, tipo="confirmar")
        return dialogo.resultado

# =====================================================================
# 3. MOTOR DE ENFOQUE DE BAJO NIVEL (APIs NATIVAS)
# =====================================================================
def forzar_foco_ventana(lista_objetivos):
    try:
        todas_las_ventanas = gw.getAllTitles()
        for titulo_ventana in todas_las_ventanas:
            for objetivo in lista_objetivos:
                if objetivo.lower() in titulo_ventana.lower():
                    win = gw.getWindowsWithTitle(titulo_ventana)[0]
                    if win.isMinimized:
                        win.restore()
                    hwnd = win._hWnd
                    ctypes.windll.user32.ShowWindow(hwnd, 9)
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    return True
        return False
    except Exception:
        return False

# =====================================================================
# 4. COMPONENTE: FORMULARIO DINÁMICO / EDICIÓN (CRUD)
# =====================================================================
class VentanaVariables(ctk.CTkToplevel):
    def __init__(self, master, row=None, callback_actualizar=None):
        super().__init__(master)
        self.master = master
        self.callback_actualizar = callback_actualizar
        self.row = row
        
        self.id_prompt = row[0] if row else None
        self.titulo_inicial = row[1] if row else ""
        self.contenido_inicial = row[2] if row else ""
        self.tags_iniciales = row[3] if row and len(row) > 3 else ""
        
        self.variables = re.findall(r"\{\{(.*?)\}\}", self.contenido_inicial)
        
        if self.id_prompt and not self.variables:
            self.title("Editar Prompt")
        elif self.variables:
            self.title("Rellenar Parámetros")
        else:
            self.title("Nuevo Prompt")
            
        self.configure(fg_color=COLOR_CONFIG["bg_main"])
        self.resizable(False, False)
        
        self.bind("<Escape>", self.solicitar_cierre_seguro)
        
        self.entradas_dinamicas = {}
        self.inicializar_ui()
        centrar_ventana(self, 460, 520)
        self.grab_set()

    def inicializar_ui(self):
        self.scroll_container = ctk.CTkScrollableFrame(
            self, fg_color=COLOR_CONFIG["bg_main"], scrollbar_button_color=COLOR_CONFIG["border"]
        )
        self.scroll_container.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        if not self.variables or (self.id_prompt and len(self.variables) > 0):
            lbl_t = ctk.CTkLabel(self.scroll_container, text="TÍTULO", font=(FONT_NAME, 10, "bold"), text_color=COLOR_CONFIG["text_muted"])
            lbl_t.pack(anchor="w", pady=(0, 4))
            self.txt_titulo = ctk.CTkEntry(
                self.scroll_container, fg_color=COLOR_CONFIG["bg_input"], border_color=COLOR_CONFIG["border"], 
                text_color=COLOR_CONFIG["text_primary"], corner_radius=6, font=(FONT_NAME, 13)
            )
            self.txt_titulo.insert(0, self.titulo_inicial)
            self.txt_titulo.pack(fill="x", pady=(0, 15))

            lbl_c = ctk.CTkLabel(self.scroll_container, text="CONTENIDO DE LA FRASE", font=(FONT_NAME, 10, "bold"), text_color=COLOR_CONFIG["text_muted"])
            lbl_c.pack(anchor="w", pady=(0, 4))
            self.txt_contenido = ctk.CTkTextbox(
                self.scroll_container, fg_color=COLOR_CONFIG["bg_input"], border_color=COLOR_CONFIG["border"], 
                text_color=COLOR_CONFIG["text_primary"], corner_radius=6, font=(FONT_NAME, 13), height=120
            )
            self.txt_contenido.insert("1.0", self.contenido_inicial)
            self.txt_contenido.pack(fill="x", pady=(0, 15))

            lbl_tags = ctk.CTkLabel(self.scroll_container, text="ETIQUETAS (TAGS) - Separadas por comas", font=(FONT_NAME, 10, "bold"), text_color=COLOR_CONFIG["text_muted"])
            lbl_tags.pack(anchor="w", pady=(5, 4))
            self.txt_tags = ctk.CTkEntry(
                self.scroll_container, fg_color=COLOR_CONFIG["bg_input"], border_color=COLOR_CONFIG["border"], 
                text_color=COLOR_CONFIG["text_primary"], corner_radius=6, font=(FONT_NAME, 13),
                placeholder_text="Ej: #desarrollo, #php, #web"
            )
            self.txt_tags.insert(0, self.tags_iniciales)
            self.txt_tags.pack(fill="x", pady=(0, 15))

        if self.variables:
            lbl_vars = ctk.CTkLabel(self.scroll_container, text="VARIABLES DETECTADAS", font=(FONT_NAME, 11, "bold"), text_color=COLOR_CONFIG["accent"])
            lbl_vars.pack(anchor="w", pady=(10, 8))
            
            for var in list(set(self.variables)):
                lbl_v = ctk.CTkLabel(self.scroll_container, text=f"• {var.upper()}", font=(FONT_NAME, 11), text_color=COLOR_CONFIG["text_primary"])
                lbl_v.pack(anchor="w", pady=(4, 2))
                entry = ctk.CTkEntry(
                    self.scroll_container, fg_color=COLOR_CONFIG["bg_input"], border_color=COLOR_CONFIG["border"], 
                    text_color=COLOR_CONFIG["text_primary"], corner_radius=6, placeholder_text=f"Ingresa valor para {var}..."
                )
                entry.pack(fill="x", pady=(0, 10))
                self.entradas_dinamicas[var] = entry

        btn_frame = ctk.CTkFrame(self, fg_color=COLOR_CONFIG["bg_main"])
        btn_frame.pack(fill="x", side="bottom", padx=20, pady=15)

        self.btn_cancelar = ctk.CTkButton(
            btn_frame, text="Cancelar", fg_color="transparent", border_width=1, 
            border_color=COLOR_CONFIG["border"], hover_color=COLOR_CONFIG["bg_input"], text_color=COLOR_CONFIG["text_primary"],
            corner_radius=6, font=(FONT_NAME, 12, "bold"), height=36, command=self.close_cancelling
        )
        self.btn_cancelar.pack(side="left", expand=True, fill="x", padx=(0, 8))

        texto_accion = "Inyectar Frase" if self.variables else "Guardar Cambios"
        self.btn_guardar = ctk.CTkButton(
            btn_frame, text=texto_accion, fg_color=COLOR_CONFIG["accent"], hover_color=COLOR_CONFIG["accent"],
            text_color="#FFFFFF", corner_radius=6, font=(FONT_NAME, 12, "bold"), height=36, command=self.ejecutar_accion_principal
        )
        self.btn_guardar.pack(side="right", expand=True, fill="x", padx=(8, 0))

    def solicitar_cierre_seguro(self, event=None):
        if VentanaMensaje.pedir_confirmacion(self, "Confirmación", "¿Estás seguro de cerrar? Se perderán los datos no guardados."):
            self.destroy()

    def close_cancelling(self):
        self.solicitar_cierre_seguro()

    def ejecutar_accion_principal(self):
        if self.variables:
            resultado = self.contenido_inicial
            campos_vacios = False
            
            for var, entry in self.entradas_dinamicas.items():
                valor = entry.get().strip()
                if not valor:
                    campos_vacios = True
                resultado = resultado.replace(f"{{{{{var}}}}}", valor)
            
            if campos_vacios:
                if not VentanaMensaje.pedir_confirmacion(self, "Campos Vacíos", "Has dejado variables vacías. ¿Inyectar de todos modos?"):
                    return
                    
            self.master.auto_escribir(resultado)
            self.destroy()
        else:
            titulo = self.txt_titulo.get().strip()
            contenido = self.txt_contenido.get("1.0", "end-1c").strip()
            tags = self.txt_tags.get().strip()

            if not titulo or not contenido:
                VentanaMensaje.mostrar_error(self, "Error de Validación", "El título y el contenido son obligatorios.")
                return

            conn = sqlite3.connect("prompts.sqlite")
            cursor = conn.cursor()
            if self.id_prompt:
                cursor.execute("UPDATE prompts SET titulo = ?, contenido = ?, tags = ? WHERE id = ?", (titulo, contenido, tags, self.id_prompt))
            else:
                cursor.execute("INSERT INTO prompts (titulo, contenido, tags) VALUES (?, ?, ?)", (titulo, contenido, tags))
            conn.commit()
            conn.close()

            if self.callback_actualizar:
                self.callback_actualizar()
            self.destroy()

# =====================================================================
# 5. APLICACIÓN PRINCIPAL: PROMPTVAULT
# =====================================================================
class PromptVaultApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PromptVault")
        
        self.apps_compatibles = ["gemini", "chatgpt", "claude", "notepad", "sublime", "chrome"]
        
        self.inicializar_base_datos()
        self.crear_componentes_ui()
        self.filtrar_prompts()
        centrar_ventana(self, 520, 600)
        
        self.entry_busqueda.focus_set()
        
        # -----------------------------------------------------------------
        # REGISTRO SEGURO DE ATAJOS DE TECLADO (THREAD-SAFE)
        # -----------------------------------------------------------------
        self.bind("<<InvocacionGlobal>>", self.alternar_visibilidad_ventana)
        self.bind("<Escape>", self.ocultar_por_escape)
        
        keyboard.add_hotkey(HOTKEY_GLOBAL, lambda: self.event_generate("<<InvocacionGlobal>>"))
        self.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion_limpia)

    def inicializar_base_datos(self):
        global TEMA_ACTIVO, COLOR_CONFIG
        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                contenido TEXT NOT NULL
            )
        """)
        
        cursor.execute("PRAGMA table_info(prompts)")
        columnas = [columna[1] for columna in cursor.fetchall()]
        if "tags" not in columnas:
            cursor.execute("ALTER TABLE prompts ADD COLUMN tags TEXT DEFAULT ''")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        """)
        
        cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tema', 'Slate Corporate')")
        conn.commit()
        
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'tema'")
        res = cursor.fetchone()
        if res and res[0] in PALETAS:
            TEMA_ACTIVO = res[0]
            COLOR_CONFIG = PALETAS[TEMA_ACTIVO]
            
        conn.close()

    def crear_componentes_ui(self):
        self.geometry("520x600")
        
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=25, pady=(25, 12))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.filtrar_prompts)

        self.entry_busqueda = ctk.CTkEntry(
            self.top_frame, textvariable=self.search_var, placeholder_text="Buscar frases o #etiquetas...",
            fg_color=COLOR_CONFIG["bg_surface"], border_color=COLOR_CONFIG["border"], text_color=COLOR_CONFIG["text_primary"],
            placeholder_text_color=COLOR_CONFIG["text_muted"], corner_radius=6, font=(FONT_NAME, 13), height=38
        )
        self.entry_busqueda.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.menu_config = ctk.CTkOptionMenu(
            self.top_frame, values=list(PALETAS.keys()), command=self.cambiar_tema_evento,
            width=140, height=38, corner_radius=6, font=(FONT_NAME, 11, "bold"),
            fg_color=COLOR_CONFIG["bg_surface"], button_color=COLOR_CONFIG["accent"],
            button_hover_color=COLOR_CONFIG["accent"], text_color=COLOR_CONFIG["text_primary"],
            dropdown_fg_color=COLOR_CONFIG["bg_surface"], dropdown_text_color=COLOR_CONFIG["text_primary"],
            dropdown_hover_color=COLOR_CONFIG["bg_input"]
        )
        self.menu_config.set(TEMA_ACTIVO)
        self.menu_config.pack(side="right", padx=(0, 8))

        self.btn_nuevo = ctk.CTkButton(
            self.top_frame, text="+ Nueva", fg_color=COLOR_CONFIG["accent"], hover_color=COLOR_CONFIG["accent"],
            text_color="#FFFFFF", corner_radius=6, font=(FONT_NAME, 11, "bold"), height=38, width=70,
            command=lambda: VentanaVariables(self, callback_actualizar=self.filtrar_prompts)
        )
        self.btn_nuevo.pack(side="right")

        self.scroll_lista = ctk.CTkScrollableFrame(
            self, fg_color=COLOR_CONFIG["bg_main"], border_width=1, border_color=COLOR_CONFIG["border"],
            scrollbar_button_color=COLOR_CONFIG["border"], corner_radius=8
        )
        self.scroll_lista.pack(fill="both", expand=True, padx=25, pady=(0, 25))

    def aplicar_tema_interfaz(self):
        global COLOR_CONFIG
        COLOR_CONFIG = PALETAS[TEMA_ACTIVO]
        
        self.configure(fg_color=COLOR_CONFIG["bg_main"])
        
        if hasattr(self, 'top_frame'):
            self.top_frame.configure(fg_color="transparent")
        if hasattr(self, 'entry_busqueda'):
            self.entry_busqueda.configure(
                fg_color=COLOR_CONFIG["bg_surface"],
                border_color=COLOR_CONFIG["border"],
                text_color=COLOR_CONFIG["text_primary"],
                placeholder_text_color=COLOR_CONFIG["text_muted"]
            )
        if hasattr(self, 'btn_nuevo'):
            self.btn_nuevo.configure(
                fg_color=COLOR_CONFIG["accent"],
                hover_color=COLOR_CONFIG["accent"]
            )
        if hasattr(self, 'menu_config'):
            self.menu_config.configure(
                fg_color=COLOR_CONFIG["bg_surface"],
                button_color=COLOR_CONFIG["accent"],
                button_hover_color=COLOR_CONFIG["accent"],
                text_color=COLOR_CONFIG["text_primary"],
                dropdown_fg_color=COLOR_CONFIG["bg_surface"],
                dropdown_text_color=COLOR_CONFIG["text_primary"],
                dropdown_hover_color=COLOR_CONFIG["bg_input"]
            )
        if hasattr(self, 'scroll_lista'):
            self.scroll_lista.configure(
                fg_color=COLOR_CONFIG["bg_main"],
                border_color=COLOR_CONFIG["border"],
                scrollbar_button_color=COLOR_CONFIG["border"]
            )
            
        self.filtrar_prompts()

    def cambiar_tema_evento(self, nuevo_tema):
        global TEMA_ACTIVO
        if nuevo_tema in PALETAS:
            TEMA_ACTIVO = nuevo_tema
            
            conn = sqlite3.connect("prompts.sqlite")
            cursor = conn.cursor()
            cursor.execute("UPDATE configuracion SET valor = ? WHERE clave = 'tema'", (nuevo_tema,))
            conn.commit()
            conn.close()
            
            self.aplicar_tema_interfaz()

    def filtrar_prompts(self, *args):
        termino = self.search_var.get().strip()
        
        for widget in self.scroll_lista.winfo_children():
            widget.destroy()

        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        
        query = "SELECT id, titulo, contenido, tags FROM prompts WHERE titulo LIKE ? OR tags LIKE ? ORDER BY titulo ASC"
        cursor.execute(query, (f"%{termino}%", f"%{termino}%"))
        rows = cursor.fetchall()

        if not rows:
            lbl_vacio = ctk.CTkLabel(
                self.scroll_lista, text="No se encontraron frases almacenadas",
                font=(FONT_NAME, 12, "italic"), text_color=COLOR_CONFIG["text_muted"]
            )
            lbl_vacio.pack(pady=40)
            conn.close()
            return

        for row in rows:
            id_p, titulo, contenido, tags = row
            
            fila_frame = ctk.CTkFrame(self.scroll_lista, fg_color=COLOR_CONFIG["bg_surface"], height=54, corner_radius=6)
            fila_frame.pack(fill="x", pady=4, padx=2)
            fila_frame.pack_propagate(False)

            tiene_variables = bool(re.search(r"\{\{(.*?)\}\}", contenido))
            
            if tiene_variables:
                cmd_accion = lambda r=row: VentanaVariables(self, r, self.filtrar_prompts)
                indicador_tipo = " ✎"
            else:
                cmd_accion = lambda c=contenido: self.auto_escribir(c)
                indicador_tipo = ""

            texto_container = ctk.CTkFrame(fila_frame, fg_color="transparent")
            texto_container.pack(side="left", fill="both", expand=True, padx=10, pady=4)

            lbl_titulo = ctk.CTkLabel(
                texto_container, text=f"{titulo}{indicador_tipo}", anchor="w",
                text_color=COLOR_CONFIG["text_primary"], font=(FONT_NAME, 13, "bold")
            )
            lbl_titulo.pack(fill="x", anchor="w")

            texto_tags = tags.strip() if tags else "Sin etiquetas"
            lbl_tags = ctk.CTkLabel(
                texto_container, text=texto_tags, anchor="w",
                text_color=COLOR_CONFIG["text_muted"], font=(FONT_NAME, 11, "italic")
            )
            lbl_tags.pack(fill="x", anchor="w", pady=(0, 2))

            lbl_titulo.bind("<Button-1>", lambda event, cmd=cmd_accion: cmd())
            lbl_tags.bind("<Button-1>", lambda event, cmd=cmd_accion: cmd())
            texto_container.bind("<Button-1>", lambda event, cmd=cmd_accion: cmd())

            btn_editar = ctk.CTkButton(
                fila_frame, text="⚙", width=34, height=34, fg_color="transparent",
                hover_color=COLOR_CONFIG["bg_input"], text_color=COLOR_CONFIG["text_muted"], font=(FONT_NAME, 14),
                command=lambda r=row: self.abrir_menu_gestion_crud(r)
            )
            btn_editar.pack(side="right", padx=8, pady=10)

        conn.close()

    def abrir_menu_gestion_crud(self, row):
        menu = ctk.CTkToplevel(self)
        menu.title("Gestionar")
        menu.geometry("280x140")
        menu.configure(fg_color=COLOR_CONFIG["bg_main"])
        menu.resizable(False, False)
        centrar_ventana(menu, 280, 140)
        menu.grab_set()

        lbl = ctk.CTkLabel(menu, text=f"Frase: {row[1]}", font=(FONT_NAME, 12, "bold"), text_color=COLOR_CONFIG["text_primary"])
        lbl.pack(pady=(15, 10))

        btn_edit = ctk.CTkButton(
            menu, text="Editar Estructura", fg_color=COLOR_CONFIG["accent"], 
            hover_color=COLOR_CONFIG["accent"], command=lambda: [menu.destroy(), VentanaVariables(self, row, self.filtrar_prompts)]
        )
        btn_edit.pack(fill="x", padx=20, pady=4)

        def confirmar_eliminacion():
            if VentanaMensaje.pedir_confirmacion(menu, "Eliminar", f"¿Seguro que deseas eliminar permanentemente '{row[1]}'?"):
                conn = sqlite3.connect("prompts.sqlite")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM prompts WHERE id = ?", (row[0],))
                conn.commit()
                conn.close()
                self.filtrar_prompts()
                menu.destroy()

        btn_del = ctk.CTkButton(menu, text="Eliminar Registro", fg_color="#DC2626", hover_color="#B91C1C", command=confirmar_eliminacion)
        btn_del.pack(fill="x", padx=20, pady=4)

    def auto_escribir(self, texto):
        self.iconify()
        time.sleep(0.4)

        if forzar_foco_ventana(self.apps_compatibles):
            time.sleep(0.4)
            try:
                keyboard.release('ctrl')
                keyboard.release('shift')
                keyboard.write(texto, delay=0.008)
            except Exception as e:
                print(f"Error durante la inyección por hardware: {e}")
        else:
            VentanaMensaje.mostrar_error(self, "Foco no Encontrado", "Abra su ventana de Inteligencia Artificial (Gemini, ChatGPT) e intente de nuevo.")

    # -----------------------------------------------------------------
    # CONTROL INTERACTIVO DE VENTANA Y TECLADO GLOBAL
    # -----------------------------------------------------------------
    def alternar_visibilidad_ventana(self, event=None):
        try:
            if self.state() == "iconic" or not self.focus_displayof():
                self.deiconify()
                self.state("normal")
                self.attributes("-topmost", True)
                self.attributes("-topmost", False)
                
                self.search_var.set("")
                self.entry_busqueda.focus_set()
            else:
                self.iconify()
        except Exception as e:
            print(f"Error en alternancia de ventana: {e}")

    def ocultar_por_escape(self, event=None):
        self.iconify()

    def cerrar_aplicacion_limpia(self):
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        self.quit()
        self.destroy()

if __name__ == "__main__":
    app = PromptVaultApp()
    app.mainloop()