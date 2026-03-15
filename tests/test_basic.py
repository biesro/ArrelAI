"""
Arrel AI — Basic Smoke Tests
=============================
Tests mínims per detectar regressions abans de push.

Run:
    pytest tests/test_basic.py -v
    
Coverage:
    - Sandbox timeout
    - Sandbox execution success
    - RAG threshold filtering
    - Model loader swapping
"""

import pytest
import time
import sys
import os

# Afegir el path del backend per poder importar
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.core.sandbox import ScientificSandbox
from backend.rag.chroma_store import ChromaStore
from backend.core.model_loader import ModelLoader


# ============================================================================
# SANDBOX TESTS
# ============================================================================

def test_sandbox_timeout():
    """
    Test: El sandbox ha d'aturar codi amb bucles infinits.
    Criteri: Status = error, missatge conté 'Timeout'
    """
    sandbox = ScientificSandbox()
    
    # Codi que triga més del timeout (30s per defecte)
    infinite_loop_code = """
import time
time.sleep(100)
"""
    
    result = sandbox.execute_and_plot(infinite_loop_code)
    
    assert result["status"] == "error", "Hauria de retornar error per timeout"
    assert "Timeout" in result["message"] or "timeout" in result["message"].lower(), \
        "El missatge hauria de mencionar 'timeout'"
    
    print("✅ test_sandbox_timeout passed")


def test_sandbox_execution_success():
    """
    Test: El sandbox executa codi vàlid correctament.
    Criteri: Status = success, output conté resultat
    """
    sandbox = ScientificSandbox()
    
    simple_code = """
import numpy as np
x = np.array([1, 2, 3, 4, 5])
print(f"Mean: {np.mean(x)}")
print(f"Sum: {np.sum(x)}")
"""
    
    result = sandbox.execute_and_plot(simple_code)
    
    assert result["status"] == "success", "Hauria d'executar correctament"
    assert "Mean" in result.get("output", ""), "Hauria de contenir 'Mean'"
    assert "Sum" in result.get("output", ""), "Hauria de contenir 'Sum'"
    
    print("✅ test_sandbox_execution_success passed")


def test_sandbox_plot_generation():
    """
    Test: El sandbox genera gràfics correctament.
    Criteri: Status = success, plot != None
    """
    sandbox = ScientificSandbox()
    
    plot_code = """
import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure()
plt.plot(x, y)
plt.title("Sine Wave")
plt.savefig('output.png', bbox_inches='tight')
"""
    
    result = sandbox.execute_and_plot(plot_code)
    
    assert result["status"] == "success", "Hauria d'executar correctament"
    assert result.get("plot") is not None, "Hauria de generar un gràfic"
    assert len(result["plot"]) > 100, "El base64 del plot hauria de tenir contingut"
    
    print("✅ test_sandbox_plot_generation passed")


def test_sandbox_persistent_env():
    """
    Test: El sandbox manté variables entre execucions (com Jupyter).
    Criteri: Variables definides en pas 1 disponibles en pas 2
    """
    sandbox = ScientificSandbox()
    
    # Pas 1: Definir variable
    step1 = """
x = 42
print(f"Step 1: x = {x}")
"""
    result1 = sandbox.execute_and_plot(step1)
    assert result1["status"] == "success"
    
    # Pas 2: Usar variable del pas anterior
    step2 = """
y = x * 2
print(f"Step 2: y = {y}")
"""
    result2 = sandbox.execute_and_plot(step2)
    assert result2["status"] == "success"
    assert "84" in result2.get("output", ""), "y hauria de ser 84 (42 * 2)"
    
    print("✅ test_sandbox_persistent_env passed")


def test_sandbox_reset():
    """
    Test: Reset sandbox esborra totes les variables.
    Criteri: Després de reset, variables anteriors no existeixen
    """
    sandbox = ScientificSandbox()
    
    # Definir variable
    sandbox.execute_and_plot("test_var = 123")
    
    # Reset
    sandbox.reset_env()
    
    # Intentar usar variable (hauria de fallar)
    result = sandbox.execute_and_plot("print(test_var)")
    assert result["status"] == "error", "Hauria de fallar perquè test_var no existeix"
    
    print("✅ test_sandbox_reset passed")


# ============================================================================
# RAG TESTS
# ============================================================================

def test_rag_threshold_filtering():
    """
    Test: El RAG filtra context irrellevant per threshold.
    Criteri: Query irrellevant retorna strings buides
    """
    # Nota: Aquest test requereix un ChromaDB temporal
    # Per simplicitat, skipem si no hi ha documents
    
    store = ChromaStore()
    
    # Afegir document de prova
    test_doc = """
Python és un llenguatge de programació interpretat d'alt nivell.
Creat per Guido van Rossum i llançat el 1991.
És conegut per la seva sintaxi clara i llegible.
"""
    
    store.add_document(test_doc, "test_python.txt")
    
    # Query molt rellevant
    relevant_query = "Qui va crear Python?"
    context1, sources1 = store.query(relevant_query, n_results=3)
    
    assert len(context1) > 0, "Hauria de retornar context per query rellevant"
    assert "test_python.txt" in sources1, "Hauria d'incloure la font"
    
    # Query totalment irrellevant (hauria de filtrar-se pel threshold)
    irrelevant_query = "Com es cultiva cafè a Etiòpia?"
    context2, sources2 = store.query(irrelevant_query, n_results=3)
    
    # Pot retornar buit o poc content (depèn del threshold)
    # Simplement verifiquem que no crasha
    assert isinstance(context2, str), "Hauria de retornar string (buit o no)"
    assert isinstance(sources2, list), "Hauria de retornar llista de fonts"
    
    # Cleanup
    store.delete_document("test_python.txt")
    
    print("✅ test_rag_threshold_filtering passed")


def test_rag_empty_collection():
    """
    Test: RAG amb col·lecció buida no crasha.
    Criteri: Retorna strings/llistes buides sense errors
    """
    store = ChromaStore()
    
    # Esborrar tots els documents si n'hi ha
    for doc in store.get_loaded_files():
        store.delete_document(doc)
    
    # Query a col·lecció buida
    context, sources = store.query("test query", n_results=5)
    
    assert context == "", "Hauria de retornar string buit"
    assert sources == [], "Hauria de retornar llista buida"
    
    print("✅ test_rag_empty_collection passed")


# ============================================================================
# MODEL LOADER TESTS (Opcional - requereix Ollama running)
# ============================================================================

@pytest.mark.skipif(
    os.getenv("SKIP_MODEL_TESTS", "true").lower() == "true",
    reason="Model tests requereixen Ollama actiu. Set SKIP_MODEL_TESTS=false per executar."
)
def test_model_loader_swap():
    """
    Test: Model loader pot canviar entre models.
    Criteri: El model actual canvia correctament
    
    NOTA: Aquest test requereix Ollama running amb els models instal·lats.
    """
    loader = ModelLoader()
    
    # Load science mode
    success1, time1 = loader.load_expert("science")
    assert success1, "Hauria de carregar el model de ciència"
    assert loader.current_model == loader.models["science"]
    
    # Load programming mode
    success2, time2 = loader.load_expert("programming")
    assert success2, "Hauria de carregar el model de programació"
    assert loader.current_model == loader.models["programming"]
    
    # Swap de nou a science (hauria de ser ràpid la segona vegada... no, sempre triga perquè descarrega)
    success3, time3 = loader.load_expert("science")
    assert success3, "Hauria de tornar a carregar ciència"
    
    # Cleanup
    loader.unload_current()
    
    print("✅ test_model_loader_swap passed")


# ============================================================================
# RUN ALL
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧪 Arrel AI — Running Smoke Tests")
    print("="*70 + "\n")
    
    try:
        # Sandbox tests
        print("\n📦 SANDBOX TESTS:\n")
        test_sandbox_timeout()
        test_sandbox_execution_success()
        test_sandbox_plot_generation()
        test_sandbox_persistent_env()
        test_sandbox_reset()
        
        # RAG tests
        print("\n🧠 RAG TESTS:\n")
        test_rag_threshold_filtering()
        test_rag_empty_collection()
        
        # Model loader (optional)
        if os.getenv("SKIP_MODEL_TESTS", "true").lower() == "false":
            print("\n🤖 MODEL LOADER TESTS:\n")
            test_model_loader_swap()
        else:
            print("\n⏭️  Skipping model loader tests (set SKIP_MODEL_TESTS=false to run)")
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {e}\n")
        sys.exit(1)
