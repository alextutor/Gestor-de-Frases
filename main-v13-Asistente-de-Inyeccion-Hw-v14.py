import sys
import os
import re
import time
import ctypes
import threading
import sqlite3
import customtkinter as ctk

# Configuración inicial de la interfaz (Estilo Slate Corporate / Linear.app)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class WindowGuard:
    """Clase nativa para el control preventivo de ventanas y alertas del sistema."""
    
    @staticmethod
    def get_active_window_hwnd():
        """Obtiene el Handle (HWND) de la ventana que tiene el foco actual."""
        return ctypes.windll.user32.GetForegroundWindow()

    @staticmethod
    def play_warning_sound():
        """Emite un pitido nativo de Windows (MessageBeep) sin consumir recursos."""
        # 0x00000030: IconWarning (Sonido de advertencia estándar de Windows)
        ctypes.windll.user32.MessageBeep(0x00000030)

    @staticmethod
    def is_safe_to_inject(app_hwnd):
        """
        Verifica si es seguro realizar la inyección de texto.
        Evita que el software se auto-inyecte datos a sí mismo.
        """
        active_hwnd = WindowGuard.get_active_window_hwnd()
        
        # Si la ventana activa es nuestra propia app, bloqueamos la acción comercialmente
        if active_hwnd == app_hwnd:
            WindowGuard.play_warning_sound()
            return False
        return True


class Sanitizer:
    """Clase encargada de la limpieza y normalización preventiva de cadenas de texto."""
    
    @staticmethod
    def normalize_newlines(text):
        """
        Garantiza que todos los saltos de línea usen el estándar de Windows (\r\n)
        para evitar que editores nativos omitan los saltos.
        """
        if not text:
            return ""
        text_unified = text.replace("\r\n", "\n").replace("\r", "\n")
        return text_unified.replace("\n", "\r\n")

    @staticmethod
    def remove_dangerous_chars(text):
        """
        Filtra caracteres de control invisibles o no imprimibles que rompen 
        la emulación de hardware por teclado.
        """
        if not text:
            return ""
        # Remueve caracteres de control Unicode (rango C0 y C1) que corrompen buffers
        return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)

    @staticmethod
    def prepare_phrase(text):
        """Método principal que ejecuta el pipeline de sanitización."""
        cleaned = Sanitizer.remove_dangerous_chars(text)
        return Sanitizer.normalize_newlines(cleaned)


class PromptVaultApp(ctk.CTk):
    """Aplicación principal PromptVault v14 (Slate Corporate)."""
    
    def __init__(self):
        super().__init__()
        
        self.title("PromptVault - Asistente de Inyección Hw v14")
        self.geometry("850headline_size_placeholder")  # UI de doble altura optimizada
        self.configure(fg_color="#141517")  # Slate fondo primario oscuro
        
        self.app_hwnd = None
        
        # Inicialización del contenedor principal de la UI
        self.main_container = ctk.CTkFrame(self, fg_color="#1A1C1E", corner_radius=8, border_color="#2C2E33", border_width=1)
        self.main_container.pack(fill="both", expand=True, padx=15, pady=15)
        
        # ---- AQUÍ SE DESPLIEGAN LOS COMPONENTES DE LA UI DEL CRUD (v13) ----
        self.title_label = ctk.CTkLabel(
            self.main_container, 
            text="PROMPTVAULT // CONTROL PREVENTIVO", 
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#9AA0A6"
        )
        self.title_label.pack(anchor="w", padx=20, pady=15)
        
        # Simulación de un área de previsualización o estado interno
        self.info_text = ctk.CTkLabel(
            self.main_container,
            text="Presiona Ctrl + , fuera de esta ventana para inyectar la frase seleccionada.\nUsa Esc para ocultar localmente.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#687076"
        )
        self.info_text.pack(pady=40)

        # Capturar contexto seguro nativo
        self.setup_security_context()
        
        # Configurar eventos clave locales
        self.bind("<Escape>", lambda e: self.withdraw())
        
        # Iniciar listener global thread-safe en segundo plano
        self.start_global_shortcut_listener()

    def setup_security_context(self):
        """Captura el HWND nativo de nuestra app al iniciar para el WindowGuard."""
        self.update_idletasks()
        # Devuelve el identificador de ventana de bajo nivel de Windows (HWND)
        self.app_hwnd = self.winfo_id()

    def start_global_shortcut_listener(self):
        """Inicializa el listener global de teclado en un hilo de baja prioridad."""
        def listener():
            import keyboard
            # Atajo seguro thread-safe "ctrl + comma"
            keyboard.add_hotkey("ctrl+comma", self.on_shortcut_pressed)
            keyboard.wait()

        threading.Thread(target=listener, daemon=True).start()

    def on_shortcut_pressed(self):
        """Callback del atajo global. Simula la captura de la frase activa del CRUD."""
        # En producción, esto lee el registro activo de la UI o DB de doble altura
        phrase_ejemplo = "Ejemplo de frase limpia con saltos de línea\nNueva línea sanitizada con éxito."
        
        # Dispara la inyección bajo demanda de forma segura
        self.trigger_safe_injection(phrase_ejemplo)

    def trigger_safe_injection(self, raw_text):
        """Método síncrono y seguro encargado de evaluar y despachar la frase."""
        # 1. Control Preventivo de Ventana Activa (Evita Auto-Inyección)
        if not WindowGuard.is_safe_to_inject(self.app_hwnd):
            return

        # 2. Sanitización y Limpieza de la Frase en pipeline
        sanitized_text = Sanitizer.prepare_phrase(raw_text)
        
        if not sanitized_text:
            # Si el filtro dejó la frase vacía por caracteres corruptos de la vida real
            WindowGuard.play_warning_sound()
            self.flash_ui_warning()
            return

        # 3. Inyección asíncrona simulando hardware para cuidar la UI (No congela hilos)
        threading.Thread(
            target=self._execute_keyboard_write, 
            args=(sanitized_text,), 
            daemon=True
        ).start()

    def _execute_keyboard_write(self, text):
        """Ejecuta la emulación física del teclado con protección de buffer."""
        try:
            # Micro-margen de 50ms para asegurar la liberación del atajo físico del usuario
            time.sleep(0.05)
            import keyboard
            keyboard.write(text)
        except Exception:
            WindowGuard.play_warning_sound()

    def flash_ui_warning(self):
        """Muta el fondo temporalmente a un Slate Rojizo de advertencia por 800ms."""
        original_color = self.main_container.cget("fg_color")
        warning_color = "#3A2424"  # Slate rojizo oscuro premium
        
        self.main_container.configure(fg_color=warning_color)
        # Restauración asíncrona nativa de CustomTkinter
        self.after(800, lambda: self.main_container.configure(fg_color=original_color))


if __name__ == "__main__":
    # Inicialización limpia de la app comercial
    app = PromptVaultApp()
    app.mainloop()