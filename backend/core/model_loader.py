import ollama
import time

class ModelLoader:
    def __init__(self):
        # Definim els models exactes de la teva Fase 1
        self.models = {
            "general": "qwen3:8b",
            "science": "qwen3:8b",
            "programming": "qwen2.5-coder:7b",
            "vision": "qwen3-vl:4b"
        }
        self.current_model = None

    def load_expert(self, mode: str):
        """
        Gestiona el swapping de models a la GPU respectant els 6GB de VRAM.
        """
        target_model = self.models.get(mode)
        
        if not target_model:
            return False, f"Mode '{mode}' no reconegut."

        # Si el model necessari ja és a la memòria, el canvi és instantani (0 segons)
        if self.current_model == target_model:
            print(f"⚡ Canvi a mode '{mode}' instantani. {target_model} ja està actiu.")
            return True, 0.0

        # 1. Buidar la VRAM: Expulsar el model antic
        if self.current_model:
            print(f"🧹 Alliberant VRAM: Descarregant {self.current_model}...")
            # keep_alive=0 força Ollama a treure el model de la memòria de vídeo
            ollama.generate(model=self.current_model, keep_alive=0)

        # 2. Carregar el nou expert a la VRAM
        print(f"🚀 Pujant {target_model} a la targeta gràfica...")
        start_time = time.time()
        
        # Fem una petició buida amb keep_alive per forçar la càrrega del model
        ollama.generate(model=target_model, keep_alive="1h")
        
        elapsed_time = round(time.time() - start_time, 2)
        self.current_model = target_model
        
        print(f"✅ {target_model} preparat en {elapsed_time} segons.")
        return True, elapsed_time

    def unload_current(self):
        """
        Força la descàrrega del model actiu per alliberar la VRAM completament.
        """
        if self.current_model:
            print(f"🧹 Neteja final: Buidant {self.current_model} de la VRAM...")
            ollama.generate(model=self.current_model, keep_alive=0)
            self.current_model = None
            print("✅ GPU totalment alliberada i neta.")
        else:
            print("ℹ️ No hi ha cap model carregat a la VRAM.")

# --- Bloc de prova ---
# Això només s'executarà si rodem aquest fitxer directament des de la terminal
if __name__ == "__main__":
    print("Iniciant test d'estrès del Model Loader...")
    loader = ModelLoader()
    
    # Simulem un usuari que fa diverses consultes
    print("\n--- Usuari: Hola, com estàs? (Mode General) ---")
    loader.load_expert("general")
    
    print("\n--- Usuari: Escriu un script en Python (Mode Programació) ---")
    loader.load_expert("programming")
    
    print("\n--- Usuari: Explica'm la mètrica de Schwarzschild (Mode Ciència) ---")
    loader.load_expert("science")
    
    print("\n--- Tancant l'aplicació ---")
    loader.unload_current()