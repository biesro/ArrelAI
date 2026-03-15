"""
Configuració de pytest per Arrel AI.
Afegeix el directori arrel al PYTHONPATH per poder importar 'backend'.
"""
import sys
import os

# Afegir l'arrel del projecte al path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"✅ PYTHONPATH configurat: {project_root}")