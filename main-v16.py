import customtkinter as ctk
import keyboard
import time
import threading
import sqlite3

# ==========================================
# ESTADO GLOBAL (MEMORIA LIGERA DE LA APP)
# ==========================================
id_prompt_actual = None

# ==========================================
# CAPA DE DATOS (LISTA PARA ESCALAR A REMOTO)
# ==========================================
def obtener_texto_prompt(prompt_id):
    """
    Recupera el texto (contenido) de un prompt por su ID desde SQLite3.
    """
    DB_NAME = "prompts.sqlite" 
    texto_recuperado = ""
    conexion = None
    
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        cursor.execute("SELECT contenido FROM prompts WHERE id = ?", (prompt_id,))
        resultado = cursor.fetchone()
        
        if resultado:
            texto_recuperado = resultado[0]
            
    except sqlite3.Error as e:
        print(f"[Error DB Local] No se pudo recuperar el prompt: {e}")
    finally:
        if conexion:
            conexion.close()
            
    return texto_recuperado

def obtener_lista_prompts():
    """
    Recupera la lista completa de IDs y títulos para renderizar la UI.
    """
    DB_NAME = "prompts.sqlite"
    registros = []
    conexion = None
    
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        cursor.execute("SELECT id, titulo FROM prompts ORDER BY id ASC")
        resultados = cursor.fetchall()
        
        for fila in resultados:
            # fila[0] es el id, fila[1] es el titulo
            registros.append({"id": fila[0], "etiqueta": fila[1]})
            
    except sqlite3.Error as e:
        print(f"[Error DB Local] No se pudo recuperar la lista de prompts: {e}")
    finally:
        if conexion:
            conexion.close()
            
    return registros

# ==========================================
# MOTOR DE INYECCIÓN THREAD-SAFE
# ==========================================
def ejecutar_disparo_dinamico(prompt_id, ocultar_ventana=True):
    """
    Consulta la BD en segundo plano e inyecta el texto simulando el teclado.
    """
    def hilo_proceso():
        texto_a_inyectar = obtener_texto_prompt(prompt_id)
        
        if not texto_a_inyectar:
            print(f"[Advertencia] El prompt con ID {prompt_id} está vacío o no existe.")
            return

        if ocultar_ventana:
            root.withdraw()
        
        time.sleep(0.4) 
        
        try:
            keyboard.write(texto_a_inyectar)
        except Exception as e:
            print(f"[Error Inyección] Fallo al simular teclado: {e}")
        finally:
            if ocultar_ventana:
                time.sleep(0.1)
                root.deiconify()

    threading.Thread(target=hilo_proceso, daemon=True).start()

# ==========================================
# GESTIÓN DE ESTADO Y UI
# ==========================================
def seleccionar_prompt(id_seleccionado):
    """Actualiza qué registro está activo al hacer clic en la UI."""
    global id_prompt_actual
    id_prompt_actual = id_seleccionado
    print(f"[Estado UI] Registro activo actualizado a ID: {id_prompt_actual}")

def puente_de_disparo(ocultar_ventana=True):
    """Validador de seguridad vinculado al botón y al atajo global."""
    global id_prompt_actual
    
    if id_prompt_actual is None:
        print("[Aviso] Operación cancelada: No hay ningún prompt seleccionado.")
        return
        
    print(f"[Motor] Orden de inyección recibida para ID: {id_prompt_actual}")
    ejecutar_disparo_dinamico(id_prompt_actual, ocultar_ventana)

def renderizar_lista_prompts(frame_contenedor):
    """Renderiza la lista conectada directamente a la base de datos real."""
    registros_bd = obtener_lista_prompts()
    
    # Manejo de estado vacío si la base de datos no tiene registros aún
    if not registros_bd:
        lbl_vacio = ctk.CTkLabel(
            frame_contenedor, 
            text="No hay prompts registrados aún.", 
            text_color="gray"
        )
        lbl_vacio.pack(pady=20)
        return

    # Generación dinámica de botones basados en la BD
    for registro in registros_bd:
        fila_btn = ctk.CTkButton(
            frame_contenedor, 
            text=registro["etiqueta"], 
            anchor="w", 
            command=lambda id_reg=registro["id"]: seleccionar_prompt(id_reg)
        )
        fila_btn.pack(pady=2, padx=10, fill="x")

# ==========================================
# ENSAMBLAJE FINAL Y BUCLE DE APLICACIÓN
# ==========================================
def iniciar_aplicacion():
    global root
    
    root = ctk.CTk()
    root.title("PromptVault v16 - Integración de Datos Reales")
    root.geometry("450x350")
    
    # Aplicar el tema (ajuste visual opcional si se requiere más adelante)
    # ctk.set_appearance_mode("dark")
    
    frame_principal = ctk.CTkFrame(root)
    frame_principal.pack(pady=20, padx=20, fill="both", expand=True)
    
    # 1. Renderizar lista interactiva desde SQLite
    renderizar_lista_prompts(frame_principal)
    
    # 2. Botón manual
    btn_inyectar = ctk.CTkButton(
        root, 
        text="Inyectar (Manual)", 
        command=lambda: puente_de_disparo(ocultar_ventana=True)
    )
    btn_inyectar.pack(pady=10)
    
    # 3. Escuchador de hardware en segundo plano
    keyboard.add_hotkey('ctrl+comma', lambda: puente_de_disparo(ocultar_ventana=True))
    
    print("[Sistema] PromptVault v16 iniciado. Escuchando 'Ctrl+,' en segundo plano.")
    
    root.mainloop()

if __name__ == "__main__":
    iniciar_aplicacion()