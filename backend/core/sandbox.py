import io
import base64
import threading
from io import StringIO
import contextlib
import traceback

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import pandas as pd

from ..config import SANDBOX_TIMEOUT


class ScientificSandbox:
    def __init__(self):
        # Entorn persistent entre execucions — com un kernel de Jupyter
        self._base_env = {
            "plt": plt,
            "np": np,
            "pd": pd,
            "animation": animation,
            "FuncAnimation": animation.FuncAnimation,
            "display": lambda x: None,
        }
        self.persistent_env = dict(self._base_env)

    def execute_and_plot(self, code: str):
        """
        Executa codi Python en un entorn controlat amb:
        - Timeout per evitar bucles infinits
        - Entorn persistent (les variables es mantenen entre crides)
        - Fix del quadrat blanc: només retorna imatge si hi ha gràfic real
        - Captura de stdout (prints)
        - Detecció automàtica de DataFrames
        """
        plt.clf()
        plt.close('all')

        output_capture = StringIO()
        result = {
            "status": "error",
            "message": f"⏱️ Timeout: el codi ha superat els {SANDBOX_TIMEOUT} segons. Comprova si hi ha bucles infinits."
        }

        def _run():
            nonlocal result
            try:
                clean_code = code.replace("plt.show()", "").strip()

                with contextlib.redirect_stdout(output_capture):
                    exec(clean_code, self.persistent_env, self.persistent_env)  # noqa: S102

                stdout_text = output_capture.getvalue()

                # ✅ FIX QUADRAT BLANC: Només guardem imatge si hi ha eixos amb contingut
                fig = plt.gcf()
                img_base64 = None

                if fig.get_axes() and any(ax.has_data() for ax in fig.get_axes()):
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
                    buf.seek(0)
                    img_base64 = base64.b64encode(buf.read()).decode('utf-8')

                # Detecció del primer DataFrame de l'entorn (per mostrar taula)
                table_data = None
                for key, value in self.persistent_env.items():
                    if isinstance(value, pd.DataFrame) and not key.startswith('_'):
                        safe_df = value.replace({np.nan: None, np.inf: None, -np.inf: None})
                        table_data = safe_df.head(500).to_dict(orient='records')
                        break

                result = {
                    "status": "success",
                    "plot": img_base64,        # None si no hi ha gràfic
                    "output": stdout_text,
                    "table": table_data
                }

            except Exception:
                result = {
                    "status": "error",
                    "message": f"Traceback de l'error:\n{traceback.format_exc()}"
                }

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=SANDBOX_TIMEOUT)

        if thread.is_alive():
            return {
                "status": "error",
                "message": f"⏱️ Timeout: execució aturada als {SANDBOX_TIMEOUT}s."
            }

        return result

    def reset_env(self):
        """Reinicia l'entorn persistent (equivalent a reiniciar el kernel de Jupyter)."""
        plt.clf()
        plt.close('all')
        self.persistent_env = dict(self._base_env)
        print("🔄 Entorn del sandbox reiniciat.")
    
    def get_state_summary(self) -> str:
        """
        Retorna un resum de l'estat actual del sandbox per passar al model.
        
        Això permet que el model "vegi" quines variables existeixen,
        els seus tipus, shapes, i estadístiques bàsiques.
        
        Returns:
            String formatat amb l'estat del sandbox
        """
        summary_lines = []
        
        for var_name, var_value in self.persistent_env.items():
            # Skip variables internes i imports
            if var_name.startswith('_'):
                continue
            if var_name in ('plt', 'np', 'pd', 'animation', 'FuncAnimation', 'display'):
                continue
            
            # NumPy arrays
            if isinstance(var_value, np.ndarray):
                info = f"  • {var_name}: ndarray {var_value.shape}"
                if var_value.size > 0:
                    info += f" | mean={np.mean(var_value):.4f}, std={np.std(var_value):.4f}"
                    if var_value.ndim == 1:
                        info += f", range=[{np.min(var_value):.4f}, {np.max(var_value):.4f}]"
                summary_lines.append(info)
            
            # Pandas DataFrames
            elif isinstance(var_value, pd.DataFrame):
                info = f"  • {var_name}: DataFrame {var_value.shape} | columns={list(var_value.columns)}"
                summary_lines.append(info)
            
            # Scalars (int, float)
            elif isinstance(var_value, (int, float, np.integer, np.floating)):
                info = f"  • {var_name}: {type(var_value).__name__} = {var_value}"
                summary_lines.append(info)
            
            # Llistes
            elif isinstance(var_value, list):
                info = f"  • {var_name}: list[{len(var_value)}]"
                if len(var_value) > 0 and all(isinstance(x, (int, float)) for x in var_value[:5]):
                    preview = str(var_value[:3])[:-1] + ", ...]" if len(var_value) > 3 else str(var_value)
                    info += f" = {preview}"
                summary_lines.append(info)
            
            # Altres tipus (dict, etc.)
            elif isinstance(var_value, dict):
                info = f"  • {var_name}: dict amb {len(var_value)} claus"
                summary_lines.append(info)
        
        if not summary_lines:
            return "🔍 Sandbox buit — cap variable definida encara."
        
        header = "🔍 ESTAT ACTUAL DEL SANDBOX:\n"
        return header + "\n".join(summary_lines)