# Arrel AI — Tests

Tests bàsics per detectar regressions abans de fer push al repositori.

## Setup

```bash
pip install -r tests/requirements-test.txt
```

## Executar tests

### Tots els tests (sense models):
```bash
pytest tests/ -v
```

### Incloent tests de model loader (requereix Ollama):
```bash
SKIP_MODEL_TESTS=false pytest tests/ -v
```

### Només tests ràpids:
```bash
pytest tests/test_basic.py::test_sandbox_execution_success -v
```

### Amb coverage:
```bash
pytest tests/ --cov=backend --cov-report=html
```

## Tests disponibles

### 🏃 Ràpids (< 5s):
- `test_sandbox_execution_success`: Execució bàsica de codi
- `test_rag_empty_collection`: RAG amb col·lecció buida
- `test_sandbox_reset`: Reset d'entorn persistent

### 🐢 Lents (> 5s):
- `test_sandbox_timeout`: Verificació de timeout (triga 30s)
- `test_rag_threshold_filtering`: Filtratge per similaritat

### 🤖 Opcionals (requereixen Ollama):
- `test_model_loader_swap`: Swapping entre models (triga ~10-20s)

## Quan executar-los

- **Abans de cada commit**: Executar tests ràpids
- **Abans de push**: Executar tots els tests (excepte model loader)
- **Abans de release**: Executar TOTS els tests incloent model loader

## CI/CD

GitHub Actions pot executar aquests tests automàticament:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt -r tests/requirements-test.txt
      - run: pytest tests/ -v
```

## Troubleshooting

**Error: ModuleNotFoundError: No module named 'backend'**
→ Executa des de l'arrel del projecte: `pytest tests/`

**Error: ChromaDB no trobat**
→ Assegura't que has executat el backend almenys una vegada per crear `chroma_db/`

**Tests de model loader fallen**
→ Verifica que Ollama està running: `ollama list`
