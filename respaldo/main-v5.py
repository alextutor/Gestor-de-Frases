import customtkinter as ctk
import sqlite3
import re
import time
import keyboard
import pygetwindow as gw
import ctypes
from tkinter import messagebox

# --- CONFIGURACIÓN DE BAJO NIVEL ---
def forzar_foco_ventana(lista_objetivos):
    """
    Busca cualquier ventana que coincida con la lista de apps
    y la trae al frente de verdad.
    """
    try:
        todas_las_ventanas = gw.getAllTitles()
        
        for titulo_ventana in todas_las_ventanas:
            for objetivo in lista_objetivos:
                if objetivo.lower() in titulo_ventana.lower():
                    # Si coincide, obtenemos la ventana
                    win = gw.getWindowsWithTitle(titulo_ventana)[0]
                    if win.isMinimized:
                        win.restore()
                    
                    # El "truco" de PhraseVault: Forzar foco por HWND
                    hwnd = win._hWnd
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    return True
    except Exception as e:
        print(f"Error al buscar ventana: {e}")
    return False

# --- CLASE PRINCIPAL ---
class PromptVaultUniversal(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PromptVault Universal v4.0")
        self.geometry("500x650")
        self.attributes("-topmost", True)
        self.configure(fg_color="#121212")

        # LISTA DE APLICACIONES COMPATIBLES
        # Puedes añadir aquí cualquier nombre de app que uses
        self.apps_compatibles = [
            "Google Gemini", "Claude", "ChatGPT", "Notepad", 
            "Bloc de notas", "Word", "Discord", "WhatsApp"
        ]

        ctk.CTkLabel(self, text="PROMPT VAULT UNIVERSAL", font=("Segoe UI", 20, "bold")).pack(pady=20)
        
        self.scroll_lista = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_lista.pack(pady=10, padx=20, fill="both", expand=True)

        self.cargar_prompts()

    def cargar_prompts(self):
        # Limpiar lista previa
        for widget in self.scroll_lista.winfo_children():
            widget.destroy()
            
        conn = sqlite3.connect('prompts.sqlite')
        cursor = conn.cursor()
        # Aseguramos que la tabla exista (basado en main.py)
        cursor.execute("SELECT titulo, contenido FROM prompts ORDER BY titulo ASC")
        
        for row in cursor.fetchall():
            f = ctk.CTkFrame(self.scroll_lista, fg_color="#1e1e1e", corner_radius=10)
            f.pack(fill="x", pady=5, padx=5)
            
            btn = ctk.CTkButton(f, text=row[0], anchor="w", fg_color="transparent",
                               hover_color="#2a2a2a",
                               command=lambda c=row[1]: self.auto_escribir_universal(c))
            btn.pack(fill="x", padx=10, pady=5)
        conn.close()

    def auto_escribir_universal(self, texto):
        """Técnica de inyección avanzada para múltiples aplicaciones."""
        self.iconify() # Ocultar nuestro gestor
        time.sleep(0.5)

        # Intentar enfocar alguna app de la lista
        if forzar_foco_ventana(self.apps_compatibles):
            time.sleep(0.6) # Pausa para que la app reciba el foco
            
            try:
                # Limpiamos estados de teclas por seguridad
                keyboard.release('ctrl')
                keyboard.release('shift')
                
                # ESCRIBIR (Usamos delay para evitar bloqueos en WebViews)
                # El delay de 0.01 es el balance ideal entre velocidad y seguridad
                keyboard.write(texto, delay=0.01)
                
            except Exception as e:
                print(f"Error de escritura: {e}")
        else:
            # Si no hay ninguna app abierta, escribe donde esté el cursor por defecto
            keyboard.write(texto, delay=0.01)

if __name__ == "__main__":
    app = PromptVaultUniversal()
    app.mainloop()