import customtkinter as ctk
import sqlite3
import re
import time
import keyboard
import pygetwindow as gw
import ctypes
from tkinter import messagebox

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

# Estas variables se inicializarán dinámicamente según la base de datos
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
# Paso 2: Componente VentanaMensaje (Mensajes de Alerta y Confirmación Premium)
# 2. COMPONENTE: MENSAJES MODALES OSCUROS PERSONALIZADOS
# =====================================================================
class VentanaMensaje(ctk.CTkToplevel):
    def __init__(self, master, titulo, mensaje, tipo="info"):
        """
        tipo: "info" (Solo aceptar) o "confirmar" (Sí/No)
        """
        super().__init__(master)
        self.master = master
        self.title(titulo)
        self.configure(fg_color=COLOR_CONFIG["bg_main"])
        self.resizable(False, False)
        
        self.resultado = None # Almacenará True o False en confirmaciones
        
        # Diseño de la interfaz interna del mensaje
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
        self.grab_set() # Bloquea interacción con ventanas traseras
        self.master.wait_window(self) # Pausa la ejecución hasta interactuar
        
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
# 2. MOTOR DE ENFOQUE DE BAJO NIVEL (APIs NATIVAS)
# =====================================================================
def forzar_foco_ventana(lista_objetivos):
    """Busca y obliga a la ventana objetivo a estar al frente de forma nativa."""
    try:
        todas_las_ventanas = gw.getAllTitles()
        for titulo_ventana in todas_las_ventanas:
            for objetivo in lista_objetivos:
                if objetivo.lower() in titulo_ventana.lower():
                    win = gw.getWindowsWithTitle(titulo_ventana)[0]
                    if win.isMinimized:
                        win.restore()
                    hwnd = win._hWnd
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    return True
        return False
    except Exception:
        return False

# =====================================================================
# 3. COMPONENTE: FORMULARIO DINÁMICO / EDICIÓN (CRUD)
# =====================================================================
class VentanaVariables(ctk.CTkToplevel):
    def __init__(self, master, row=None, callback_actualizar=None):
        super().__init__(master)
        self.master = master
        self.callback_actualizar = callback_actualizar
        self.row = row  # Si viene row, estamos EDITANDO o RELLENANDO variables
        
        self.id_prompt = row[0] if row else None
        self.titulo_inicial = row[1] if row else ""
        self.contenido_inicial = row[2] if row else ""
        
        # Analizar si contiene variables dinámicas
        self.variables = re.findall(r"\{\{(.*?)\}\}", self.contenido_inicial)
        
        # Ajustar título según el contexto del CRUD
        if self.id_prompt and not self.variables:
            self.title("Editar Prompt")
        elif self.variables:
            self.title("Rellenar Parámetros")
        else:
            self.title("Nuevo Prompt")
            
        self.configure(fg_color=BG_MAIN)
        self.resizable(False, False)
        
        # Captura segura de la tecla Esc con confirmación de salida
        self.bind("<Escape>", self.solicitar_cierre_seguro)
        
        self.entradas_dinamicas = {}
        self.inicializar_ui()
        centrar_ventana(self, 460, 480)
        self.grab_set()  # Foco exclusivo modal

    def inicializar_ui(self):
        # Contenedor con scroll para evitar desbordes visuales
        self.scroll_container = ctk.CTkScrollableFrame(
            self, fg_color=BG_MAIN, scrollbar_button_color=BORDER_COLOR
        )
        self.scroll_container.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        # Sección de metadatos (Título y Cuerpo) - Solo editable si no es inyección directa
        if not self.variables or (self.id_prompt and len(self.variables) > 0):
            lbl_t = ctk.CTkLabel(self.scroll_container, text="TÍTULO", font=(FONT_NAME, 10, "bold"), text_color=TEXT_MUTED)
            lbl_t.pack(anchor="w", pady=(0, 4))
            self.txt_titulo = ctk.CTkEntry(self.scroll_container, fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, corner_radius=6, font=(FONT_NAME, 13))
            self.txt_titulo.insert(0, self.titulo_inicial)
            self.txt_titulo.pack(fill="x", pady=(0, 15))

            lbl_c = ctk.CTkLabel(self.scroll_container, text="CONTENIDO DE LA FRASE", font=(FONT_NAME, 10, "bold"), text_color=TEXT_MUTED)
            lbl_c.pack(anchor="w", pady=(0, 4))
            self.txt_contenido = ctk.CTkTextbox(self.scroll_container, fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, corner_radius=6, font=(FONT_NAME, 13), height=120)
            self.txt_contenido.insert("1.0", self.contenido_inicial)
            self.txt_contenido.pack(fill="x", pady=(0, 15))

        # Generación compacta de inputs si existen variables dinámicas
        if self.variables:
            lbl_vars = ctk.CTkLabel(self.scroll_container, text="VARIABLES DETECTADAS", font=(FONT_NAME, 11, "bold"), text_color=ACCENT_COLOR)
            lbl_vars.pack(anchor="w", pady=(10, 8))
            
            # Evitar campos duplicados visualmente
            for var in list(set(self.variables)):
                lbl_v = ctk.CTkLabel(self.scroll_container, text=f"• {var.upper()}", font=(FONT_NAME, 11), text_color=TEXT_PRIMARY)
                lbl_v.pack(anchor="w", pady=(4, 2))
                entry = ctk.CTkEntry(self.scroll_container, fg_color=BG_INPUT, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY, corner_radius=6, placeholder_text=f"Ingresa valor para {var}...")
                entry.pack(fill="x", pady=(0, 10))
                self.entradas_dinamicas[var] = entry

        # Barra de acciones inferior (Diseño horizontal limpio)
        btn_frame = ctk.CTkFrame(self, fg_color=BG_MAIN)
        btn_frame.pack(fill="x", side="bottom", padx=20, pady=15)

        self.btn_cancelar = ctk.CTkButton(
            btn_frame, text="Cancelar", fg_color="transparent", border_width=1, 
            border_color=BORDER_COLOR, hover_color="#252525", text_color=TEXT_PRIMARY,
            corner_radius=6, font=(FONT_NAME, 12, "bold"), height=36, command=self.close_cancelling
        )
        self.btn_cancelar.pack(side="left", expand=True, fill="x", padx=(0, 8))

        # Texto dinámico del botón de acción según el contexto
        texto_accion = "Inyectar Frase" if self.variables else "Guardar Cambios"
        self.btn_guardar = ctk.CTkButton(
            btn_frame, text=texto_accion, fg_color=ACCENT_COLOR, hover_color="#4338CA",
            text_color="#FFFFFF", corner_radius=6, font=(FONT_NAME, 12, "bold"), height=36, command=self.ejecutar_accion_principal
        )
        self.btn_guardar.pack(side="right", expand=True, fill="x", padx=(8, 0))

    def solicitar_cierre_seguro(self, event=None):
        """Verifica si el usuario desea cerrar la ventana activa perdiendo modificaciones."""
        confirmar = messagebox.askyesno(
            "Confirmación", 
            "¿Estás seguro de que deseas cerrar este formulario? Se perderán los datos no guardados.",
            parent=self
        )
        if confirmar:
            self.destroy()

    def close_cancelling(self):
        self.solicitar_cierre_seguro()

    def ejecutar_accion_principal(self):
        # Escenario A: Rellenar variables dinámicas e inyectar al sistema destino
        if self.variables:
            resultado = self.contenido_inicial
            campos_vacios = False
            
            for var, entry in self.entradas_dinamicas.items():
                valor = entry.get().strip()
                if not valor:
                    campos_vacios = True
                resultado = resultado.replace(f"{{{{{var}}}}}", valor)
            
            # Regala seguridad previniendo el envío de datos corruptos al portapapeles o teclado
            if campos_vacios:
                continuar = messagebox.askyesno(
                    "Campos Vacíos", 
                    "Has dejado una o más variables vacías. ¿Deseas inyectar la frase incompleta de todos modos?",
                    parent=self
                )
                if not continuar:
                    return
                    
            self.master.auto_escribir(resultado)
            self.destroy()
            
        # Escenario B: Guardar un nuevo prompt o actualizar uno existente (CRUD)
        else:
            titulo = self.txt_titulo.get().strip()
            contenido = self.txt_contenido.get("1.0", "end-1c").strip()

            if not titulo or not contenido:
                messagebox.showwarning("Error de Validación", "El título y el contenido son obligatorios.", parent=self)
                return

            conn = sqlite3.connect("prompts.sqlite")
            cursor = conn.cursor()
            if self.id_prompt:
                cursor.execute("UPDATE prompts SET titulo = ?, contenido = ? WHERE id = ?", (titulo, contenido, self.id_prompt))
            else:
                cursor.execute("INSERT INTO prompts (titulo, contenido) VALUES (?, ?)", (titulo, contenido))
            conn.commit()
            conn.close()

            if self.callback_actualizar:
                self.callback_actualizar()
            self.destroy()

# =====================================================================
# 4. APLICACIÓN PRINCIPAL: PROMPTVAULT
# =====================================================================
class PromptVaultApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PromptVault")
        self.geometry("520 Arena")
        self.configure(fg_color=BG_MAIN)
        self.resizable(False, False)
        
        self.apps_compatibles = ["gemini", "chatgpt", "claude", "notepad", "sublime", "chrome"]
        
        self.inicializar_base_datos()
        self.crear_componentes_ui()
        self.filtrar_prompts()
        centrar_ventana(self, 520, 600)
        
        # Foco inmediato en la barra de búsqueda al abrir (Como PhraseVault)
        self.entry_busqueda.focus_set()

    def inicializar_base_datos(self):
        global TEMA_ACTIVO, COLOR_CONFIG
        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        
        # Tabla de frases
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                contenido TEXT NOT NULL
            )
        """)
        
        # Nueva tabla para persistir la configuración visual del usuario
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        """)
        
        # Insertar tema inicial por defecto si no existe
        cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tema', 'Slate Corporate')")
        conn.commit()
        
        # Cargar el tema guardado por el usuario
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'tema'")
        res = cursor.fetchone()
        if res and res[0] in PALETAS:
            TEMA_ACTIVO = res[0]
            COLOR_CONFIG = PALETAS[TEMA_ACTIVO]
            
        conn.close()

    def crear_componentes_ui(self):
        # Cabecera de búsqueda superior elegante
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=25, pady=(25, 12))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.filtrar_prompts)

        self.entry_busqueda = ctk.CTkEntry(
            top_frame, textvariable=self.search_var, placeholder_text="Buscar frases (Presiona flechas para navegar)...",
            fg_color=BG_SURFACE, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED, corner_radius=6, font=(FONT_NAME, 13), height=38
        )
        self.entry_busqueda.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_nuevo = ctk.CTkButton(
            top_frame, text="+ Nueva Frase", fg_color=ACCENT_COLOR, hover_color="#4338CA",
            text_color="#FFFFFF", corner_radius=6, font=(FONT_NAME, 12, "bold"), height=38,
            command=lambda: VentanaVariables(self, callback_actualizar=self.filtrar_prompts)
        )
        self.btn_nuevo.pack(side="right")

        # Contenedor central de resultados
        self.scroll_lista = ctk.CTkScrollableFrame(
            self, fg_color=BG_MAIN, border_width=1, border_color=BORDER_COLOR,
            scrollbar_button_color=BORDER_COLOR, corner_radius=8
        )
        self.scroll_lista.pack(fill="both", expand=True, padx=25, pady=(0, 25))

  
    # =====================================================================
    # Paso 4: Adaptación del CRUD Dinámico y Renderizado Inmediato
    # 1. Actualización de la Lista Visual (filtrar_prompts)
    # =====================================================================

    def filtrar_prompts(self, *args):
        """Filtro dinámico y seguro usando consultas preparadas contra inyección SQL."""
        termino = self.search_var.get().strip()
        
        # Limpiar lista visual previa
        for widget in self.scroll_lista.winfo_children():
            widget.destroy()

        conn = sqlite3.connect("prompts.sqlite")
        cursor = conn.cursor()
        
        query = "SELECT id, titulo, contenido FROM prompts WHERE titulo LIKE ? ORDER BY titulo ASC"
        cursor.execute(query, (f"%{termino}%",))
        rows = cursor.fetchall()

        if not rows:
            lbl_vacio = ctk.CTkLabel(
                self.scroll_lista, text="No se encontraron frases almacenadas",
                font=(FONT_NAME, 12, "italic"), text_color=COLOR_CONFIG["text_muted"]
            )
            lbl_vacio.pack(pady=40)
            conn.close()
            return

        # Renderizado de filas compactas y premium adaptadas al tema activo
        for row in rows:
            id_p, titulo, contenido = row
            
            fila_frame = ctk.CTkFrame(self.scroll_lista, fg_color=COLOR_CONFIG["bg_surface"], height=46, corner_radius=6)
            fila_frame.pack(fill="x", pady=4, padx=2)
            fila_frame.pack_propagate(False)

            tiene_variables = bool(re.search(r"\{\{(.*?)\}\}", contenido))
            
            if tiene_variables:
                cmd_accion = lambda r=row: VentanaVariables(self, r, self.filtrar_prompts)
                indicador_tipo = " ✎"
            else:
                cmd_accion = lambda c=contenido: self.auto_escribir(c)
                indicador_tipo = ""

            # Botón Principal (Título de la frase)
            btn_titulo = ctk.CTkButton(
                fila_frame, text=f"{titulo}{indicador_tipo}", anchor="w", fg_color="transparent",
                hover_color=COLOR_CONFIG["bg_input"], text_color=COLOR_CONFIG["text_primary"], font=(FONT_NAME, 13, "bold"),
                command=cmd_accion
            )
            btn_titulo.pack(side="left", fill="both", expand=True, padx=8)

            # Botón secundario compacto de edición profunda
            btn_editar = ctk.CTkButton(
                fila_frame, text="⚙", width=32, height=32, fg_color="transparent",
                hover_color=COLOR_CONFIG["bg_input"], text_color=COLOR_CONFIG["text_muted"], font=(FONT_NAME, 14),
                command=lambda r=row: self.abrir_menu_gestion_crud(r)
            )
            btn_editar.pack(side="right", padx=6, pady=6)

        conn.close()
        

    def abrir_menu_gestion_crud(self, row):
        """Despliega una mini-ventana para editar el cuerpo o eliminar el registro (CRUD completo)."""
        menu = ctk.CTkToplevel(self)
        menu.title("Gestionar")
        menu.geometry("280x140")
        menu.configure(fg_color=BG_MAIN)
        menu.resizable(False, False)
        centrar_ventana(menu, 280, 140)
        menu.grab_set()

        lbl = ctk.CTkLabel(menu, text=f"Frase: {row[1]}", font=(FONT_NAME, 12, "bold"), text_color=TEXT_PRIMARY)
        lbl.pack(pady=(15, 10))

        btn_edit = ctk.CTkButton(menu, text="Editar Estructura", fg_color=ACCENT_COLOR, hover_color="#4338CA", command=lambda: [menu.destroy(), VentanaVariables(self, row, self.filtrar_prompts)])
        btn_edit.pack(fill="x", padx=20, pady=4)

        def confirmar_eliminacion():
            if messagebox.askyesno("Eliminar", f"¿Seguro que deseas eliminar permanentemente '{row[1]}'?", parent=menu):
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
        """Motor nativo heredado optimizado: minimiza, enfoca y escribe de forma fluida."""
        self.iconify()
        time.sleep(0.4)

        if forzar_foco_ventana(self.apps_compatibles):
            time.sleep(0.4)
            try:
                keyboard.release('ctrl')
                keyboard.release('shift')
                keyboard.write(texto, delay=0.008)  # Velocidad ajustada para evitar bloqueos del WebView
            except Exception as e:
                print(f"Error durante la inyección por hardware: {e}")
        else:
            messagebox.showwarning("Foco no Encontrado", "Abra su ventana de Inteligencia Artificial (Gemini, ChatGPT) e intente de nuevo.")


    # =====================================================================
    # Paso 3: Menú de Selección y Función de Repintado Dinámico
    #1. Función Centralizada de Repintado
    # =====================================================================

    def aplicar_tema_interfaz(self):
        """
        Recorre y actualiza dinámicamente el color de todos los widgets activos
        según el diccionario COLOR_CONFIG actual.
        """
        global COLOR_CONFIG
        COLOR_CONFIG = PALETAS[TEMA_ACTIVO]
        
        # 1. Ventana Principal
        self.configure(fg_color=COLOR_CONFIG["bg_main"])
        
        # 2. Contenedor de Búsqueda Superior
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

        # 3. Contenedor Central de Lista
        if hasattr(self, 'scroll_lista'):
            self.scroll_lista.configure(
                fg_color=COLOR_CONFIG["bg_main"],
                border_color=COLOR_CONFIG["border"],
                scrollbar_button_color=COLOR_CONFIG["border"]
            )
            
        # Re-renderizar la lista de prompts para que adopten los nuevos colores inmediatamente
        self.filtrar_prompts()

    # =====================================================================
    # Paso 3: Menú de Selección y Función de Repintado Dinámico
    # 2. Evento de Cambio de Tema (Persistencia)
    # =====================================================================

    def cambiar_tema_evento(self, nuevo_tema):
        global TEMA_ACTIVO
        if nuevo_tema in PALETAS:
            TEMA_ACTIVO = nuevo_tema
            
            # Guardar la preferencia de forma permanente en SQLite
            conn = sqlite3.connect("prompts.sqlite")
            cursor = conn.cursor()
            cursor.execute("UPDATE configuracion SET valor = ? WHERE clave = 'tema'", (nuevo_tema,))
            conn.commit()
            conn.close()
            
            # Repintar la interfaz con la nueva paleta comercial
            self.aplicar_tema_interfaz() 
    
    
    # =====================================================================
    # Paso 3: Menú de Selección y Función de Repintado Dinámico
    # 3. Actualización de crear_componentes_ui
    # =====================================================================
    
    def crear_componentes_ui(self):
        # Corregir error crítico de geometría del archivo v10 anterior
        self.geometry("520x600")
        
        # Cabecera de búsqueda superior elegante
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=25, pady=(25, 12))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.filtrar_prompts)

        self.entry_busqueda = ctk.CTkEntry(
            self.top_frame, textvariable=self.search_var, placeholder_text="Buscar frases...",
            fg_color=COLOR_CONFIG["bg_surface"], border_color=COLOR_CONFIG["border"], text_color=COLOR_CONFIG["text_primary"],
            placeholder_text_color=COLOR_CONFIG["text_muted"], corner_radius=6, font=(FONT_NAME, 13), height=38
        )
        self.entry_busqueda.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Selector de Paletas Comerciales Dinámico
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

        # Contenedor central de resultados
        self.scroll_lista = ctk.CTkScrollableFrame(
            self, fg_color=COLOR_CONFIG["bg_main"], border_width=1, border_color=COLOR_CONFIG["border"],
            scrollbar_button_color=COLOR_CONFIG["border"], corner_radius=8
        )
        self.scroll_lista.pack(fill="both", expand=True, padx=25, pady=(0, 25))
        

if __name__ == "__main__":
    app = PromptVaultApp()
    app.mainloop()