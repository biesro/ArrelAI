# 🤝 Guia de Contribució

Gràcies per considerar contribuir a **Arrel AI**! 🌳

## Com Contribuir

### 1. Reportar Bugs

Si trobes un bug, obre un **Issue** amb:
- **Títol descriptiu** del problema
- **Passos per reproduir-lo**
- **Comportament esperat vs. actual**
- **Informació del sistema** (OS, Python version, GPU)
- **Logs o screenshots** si és possible

### 2. Proposar Funcionalitats

Per proposar noves funcionalitats:
- Obre un **Issue** amb el tag `enhancement`
- Descriu **el problema** que resoldria
- Explica **la solució proposada**
- Discuteix alternatives considerades

### 3. Pull Requests

#### Workflow

```bash
# 1. Fork el repositori
# 2. Clona el teu fork
git clone https://github.com/el-teu-usuari/arrel-ai.git

# 3. Crea una branch
git checkout -b feature/nom-descriptiu

# 4. Fes els canvis i commits
git commit -m "Add: descripció clara del canvi"

# 5. Push a la teva branch
git push origin feature/nom-descriptiu

# 6. Obre un Pull Request a la branch main
```

#### Guia d'Estil de Commits

Usa commits clars i descriptius:
- `Add: nova funcionalitat X`
- `Fix: bug a l'execució del sandbox`
- `Update: millora del sistema RAG`
- `Docs: actualitza README amb instruccions`

#### Abans de Submit

- [ ] El codi segueix l'estil del projecte
- [ ] Has afegit **tests** per la nova funcionalitat
- [ ] Tots els tests passen: `pytest tests/ -v`
- [ ] Has actualitzat la **documentació** si cal
- [ ] El commit té un **missatge descriptiu**

### 4. Executar Tests

Abans de fer un PR, assegura't que tot funciona:

```bash
# Instal·la dependencies de test
pip install -r requirements_test.txt

# Executa tots els tests
pytest tests/ -v

# Amb cobertura
pytest tests/ --cov=backend --cov-report=html
```

### 5. Estil de Codi

- **Python**: Segueix [PEP 8](https://pep8.org/)
- **JavaScript/React**: Segueix [Airbnb Style Guide](https://github.com/airbnb/javascript)
- **Docstrings**: Usa format de Google per funcions complexes

#### Exemple de Docstring:

```python
def query(self, question: str, n_results: int = 15) -> tuple[str, list[str]]:
    """
    RAG amb pipeline de dos estadis: retrieval + reranking.
    
    Args:
        question: Query de l'usuari
        n_results: Nombre de candidats inicials
        
    Returns:
        tuple(context, sources_used)
    """
```

### 6. Àrees de Contribució

Aquestes són algunes àrees on pots ajudar:

**Backend:**
- Millores al sistema de self-reflection
- Optimitzacions del research loop
- Nous backends RAG (alternatius a ChromaDB)
- Suport per més formats de document

**Frontend:**
- Millores a la UI/UX
- Tema clar/fosc configurable
- Export de converses
- Visualitzacions de dades millorades

**Documentació:**
- Tutorials i exemples d'ús
- Traduccions del README
- Millores als comentaris del codi
- Screencasts o GIFs demostratius

**Testing:**
- Afegir més tests unitaris
- Tests d'integració
- Benchmark de rendiment

## Codi de Conducta

- Sigues respectuós i constructiu
- Accepta feedback amb mentalitat oberta
- Enfoca't en el que és millor pel projecte
- Mostra empatia cap altres contribuïdors

## Preguntes?

Si tens dubtes sobre com contribuir, obre un **Issue** amb el tag `question` i t'ajudarem! 💬

---

Gràcies per fer **Arrel AI** millor! 🙏
