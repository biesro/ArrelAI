"""
Self-Reflection System — Arrel AI
==================================
Sistema que fa que el model reflexioni sobre els seus propis resultats
en lloc d'usar regles hard-coded.

Principi: Ensenyar el model a pensar críticament, no dir-li què està bé/malament.
"""

import numpy as np
import pandas as pd
import re


def extract_numerical_results(stdout: str) -> dict:
    """
    Extreu resultats numèrics del stdout per poder-los presentar al model.
    Això NO valida res, només extreu.
    """
    results = {}
    
    # Busca patrons numèrics comuns
    lines = stdout.strip().split('\n')
    
    for line in lines:
        # Format: "Variable: 123.45" o "Variable = 123.45"
        match = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_\s]*)[:\s=]+([0-9.eE+-]+)', line)
        if match:
            key = match.group(1).strip().lower().replace(' ', '_')
            try:
                value = float(match.group(2))
                results[key] = value
            except ValueError:
                pass
    
    return results


def get_data_summary(sandbox_env: dict) -> str:
    """
    Resumeix les dades d'entrada originals per poder comparar
    amb els resultats calculats.
    """
    summary_lines = []
    
    for var_name, var_value in sandbox_env.items():
        if var_name.startswith('_') or var_name in ('plt', 'np', 'pd', 'animation', 'FuncAnimation', 'display'):
            continue
        
        # Arrays: estadístiques bàsiques
        if isinstance(var_value, np.ndarray) and var_value.size > 0:
            info = f"  • {var_name}: {var_value.shape}"
            
            if var_value.ndim == 1:
                # Detecta si té estructura periòdica (per comparació)
                if len(var_value) > 10:
                    # Calcula autocorrelació simple
                    mean_val = np.mean(var_value)
                    std_val = np.std(var_value)
                    min_val = np.min(var_value)
                    max_val = np.max(var_value)
                    
                    info += f" | range=[{min_val:.4f}, {max_val:.4f}], mean={mean_val:.4f}, std={std_val:.4f}"
                    
                    # Si hi ha pocs valors únics, podria ser categòric
                    unique_count = len(np.unique(var_value))
                    if unique_count < 20:
                        info += f", {unique_count} valors únics"
            
            summary_lines.append(info)
        
        # DataFrames
        elif isinstance(var_value, pd.DataFrame):
            info = f"  • {var_name}: {var_value.shape} | cols={list(var_value.columns[:5])}"
            summary_lines.append(info)
    
    if not summary_lines:
        return "Cap dada d'entrada disponible per comparar."
    
    return "DADES D'ENTRADA:\n" + "\n".join(summary_lines)


def build_scale_analysis(numerical_results: dict, sandbox_env: dict) -> str:
    """
    Raonament dimensional: "Si el valor calculat és X, què esperaries veure?"
    
    Això és matemàtica pura, no específica de cap domini.
    """
    analyses = []
    
    # Informació sobre les dades totals
    total_points = 0
    data_arrays = []
    
    for var_name, var_value in sandbox_env.items():
        if var_name.startswith('_') or var_name in ('plt', 'np', 'pd', 'animation', 'FuncAnimation', 'display'):
            continue
        
        if isinstance(var_value, np.ndarray) and var_value.ndim == 1:
            total_points = max(total_points, len(var_value))
            data_arrays.append((var_name, var_value))
    
    if total_points == 0:
        return ""
    
    # Anàlisi dimensional per diferents tipus de resultats
    
    # 1. Si hi ha un "period", "cycle", "frequency", "interval"
    for key in ['period', 'cycle', 'frequency', 'interval', 'spacing']:
        if key in numerical_results:
            value = numerical_results[key]
            if value > 0:
                expected_events = total_points / value
                analyses.append(
                    f"\n📏 ANÀLISI DIMENSIONAL ({key}):\n"
                    f"   Dataset total: {total_points} punts\n"
                    f"   {key.capitalize()} calculat: {value:.2f}\n"
                    f"   → Això implica ~{expected_events:.1f} esdeveniments/cicles complets\n"
                    f"   → Les dades mostren realment aquesta quantitat d'esdeveniments?"
                )
    
    # 2. Si hi ha percentatges
    for key in ['percentage', 'percent', 'ratio', 'fraction']:
        if key in numerical_results:
            value = numerical_results[key]
            if 0 <= value <= 1:
                value_pct = value * 100
            else:
                value_pct = value
            
            analyses.append(
                f"\n📏 ANÀLISI DIMENSIONAL ({key}):\n"
                f"   Percentatge calculat: {value_pct:.1f}%\n"
                f"   → D'un total de {total_points} elements\n"
                f"   → Això són ~{total_points * value / 100:.0f} elements\n"
                f"   → El recompte coincideix?"
            )
    
    # 3. Si hi ha mitjanes/std comparades amb el rang real de dades
    if 'mean' in numerical_results or 'average' in numerical_results:
        mean_val = numerical_results.get('mean') or numerical_results.get('average')
        std_val = numerical_results.get('std') or numerical_results.get('stdev')
        
        # Compara amb les dades reals
        for var_name, var_value in data_arrays:
            if len(var_value) > 0:
                actual_min = np.min(var_value)
                actual_max = np.max(var_value)
                actual_range = actual_max - actual_min
                
                analysis = f"\n📏 ANÀLISI DIMENSIONAL (estadístiques):\n"
                analysis += f"   Mean calculada: {mean_val:.4f}\n"
                
                if std_val:
                    expected_range = std_val * 6  # ~99.7% dins ±3σ
                    analysis += f"   Std calculada: {std_val:.4f}\n"
                    analysis += f"   → Rang esperat (~6σ): {expected_range:.4f}\n"
                    analysis += f"   → Rang real de '{var_name}': {actual_range:.4f}\n"
                    
                    if actual_range > expected_range * 2:
                        analysis += f"   ⚠️ Rang real és molt més gran que l'esperat (possibles outliers?)\n"
                    elif actual_range < expected_range * 0.5:
                        analysis += f"   ⚠️ Rang real és molt més petit que l'esperat (std massa gran?)\n"
                
                analyses.append(analysis)
                break  # Només primer array
    
    # 4. Si hi ha comptes/recomptes
    for key in ['count', 'total', 'sum', 'n_events', 'num']:
        if key in numerical_results:
            value = numerical_results[key]
            if value > total_points:
                analyses.append(
                    f"\n📏 ANÀLISI DIMENSIONAL ({key}):\n"
                    f"   {key.capitalize()} calculat: {value:.0f}\n"
                    f"   Dataset total: {total_points} punts\n"
                    f"   ⚠️ El recompte supera el total de dades (impossible!)\n"
                )
            elif value > 0:
                percentage = (value / total_points) * 100
                analyses.append(
                    f"\n📏 ANÀLISI DIMENSIONAL ({key}):\n"
                    f"   {key.capitalize()} calculat: {value:.0f}\n"
                    f"   Dataset total: {total_points} punts\n"
                    f"   → Això és el {percentage:.1f}% de les dades\n"
                    f"   → Aquesta proporció té sentit?"
                )
    
    return "".join(analyses) if analyses else ""


def build_reflection_prompt(stdout: str, sandbox_env: dict, step_num: int) -> str:
    """
    Construeix un prompt que fa que el model reflexioni sobre els seus resultats.
    
    NO hi ha regles hard-coded.
    El model aprèn a detectar incoherències per si mateix.
    """
    
    # Extreu resultats numèrics (si n'hi ha)
    numerical_results = extract_numerical_results(stdout)
    
    # Resumeix les dades d'entrada
    data_summary = get_data_summary(sandbox_env)
    
    # Anàlisi dimensional (raonament de scaling)
    scale_analysis = build_scale_analysis(numerical_results, sandbox_env)
    
    # Construeix el prompt de reflexió
    prompt = f"""
📊 REFLEXIÓ CRÍTICA — Pas {step_num}

RESULTATS QUE HAS GENERAT:
{stdout if stdout.strip() else "(cap sortida de text)"}
"""
    
    if numerical_results:
        prompt += "\nVALORS NUMÈRICS EXTRETS:\n"
        for key, value in numerical_results.items():
            prompt += f"  • {key}: {value}\n"
    
    prompt += f"""
{data_summary}
{scale_analysis}

AUTOAVALUACIÓ:
Analitza críticament els teus propis resultats. Pregunta't:

1️⃣ COHERÈNCIA AMB LES DADES:
   - Els resultats calculats són coherents amb les dades d'entrada?
   - Els ordres de magnitud tenen sentit?
   - Si les dades tenen N punts, els resultats reflecteixen això?

2️⃣ CONSISTÈNCIA INTERNA:
   - Si has calculat múltiples valors, són consistents entre ells?
   - Hi ha contradiccions òbvies?

3️⃣ SANITAT BÀSICA:
   - Els valors són finits (no NaN, no Inf)?
   - Els percentatges estan entre 0 i 100?
   - Les ràtios tenen sentit (no negatives si són magnituds)?

4️⃣ METODOLOGIA:
   - L'algorisme usat és apropiat per al problema?
   - Hi ha passos que podrien millorar-se?

Si detectes QUALSEVOL incoherència o dubte, explica què cal revisar.
Si tot sembla correcte i robust, confirma-ho breument i continua.

NO assumeixis que està bé només perquè s'ha executat sense errors.
Pensa críticament.
"""
    
    return prompt


def detect_quality_issues(sandbox_env: dict) -> list:
    """
    Detecta problemes GENERALS de qualitat de dades.
    Això SÍ és general: NaN, Inf, arrays buits, variància zero.
    
    NO inclou regles específiques de domini.
    """
    issues = []
    
    for var_name, var_value in sandbox_env.items():
        if var_name.startswith('_') or var_name in ('plt', 'np', 'pd', 'animation', 'FuncAnimation', 'display'):
            continue
        
        # Arrays
        if isinstance(var_value, np.ndarray):
            # NaN
            if np.any(np.isnan(var_value)):
                nan_count = np.sum(np.isnan(var_value))
                issues.append(f"⚠️ '{var_name}' té {nan_count} valors NaN")
            
            # Inf
            if np.any(np.isinf(var_value)):
                inf_count = np.sum(np.isinf(var_value))
                issues.append(f"⚠️ '{var_name}' té {inf_count} valors Inf")
            
            # Array buit
            if var_value.size == 0:
                issues.append(f"⚠️ '{var_name}' és un array buit")
            
            # Variància zero (constant)
            if var_value.size > 1 and np.std(var_value) == 0:
                issues.append(f"⚠️ '{var_name}' té variància zero (tots els valors són {var_value.flat[0]})")
        
        # DataFrames
        elif isinstance(var_value, pd.DataFrame):
            for col in var_value.columns:
                if pd.api.types.is_numeric_dtype(var_value[col]):
                    # NaN
                    nan_count = var_value[col].isna().sum()
                    if nan_count > 0:
                        issues.append(f"⚠️ '{var_name}[{col}]' té {nan_count} NaN")
                    
                    # Inf
                    inf_count = np.isinf(var_value[col]).sum()
                    if inf_count > 0:
                        issues.append(f"⚠️ '{var_name}[{col}]' té {inf_count} Inf")
    
    return issues


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    # Test 1: Reflexió sobre resultats
    stdout_test = """
    Detected centers: [10, 13, 16, 19, 22]
    Estimated period: 3.2
    Average depth: 0.012
    """
    
    test_env = {
        "time": np.arange(500),
        "flux": np.ones(500) * 0.998
    }
    
    prompt = build_reflection_prompt(stdout_test, test_env, step_num=3)
    print("Test 1 - Self-reflection prompt:")
    print(prompt)
    print("\n" + "="*80 + "\n")
    
    # Test 2: Detecció de problemes generals
    bad_env = {
        "data": np.array([1.0, 2.0, np.nan, 4.0, np.inf]),
        "constant": np.ones(100) * 5.0
    }
    
    issues = detect_quality_issues(bad_env)
    print("Test 2 - Quality issues detectats:")
    for issue in issues:
        print(f"  {issue}")