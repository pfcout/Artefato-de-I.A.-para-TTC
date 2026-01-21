# tools/scan_usage.py
from __future__ import annotations
import re
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]  # ajusta se necessário
PY_FILES = [p for p in ROOT.rglob("*.py") if ".venv" not in str(p) and "site-packages" not in str(p)]

IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z0-9_\.]+)", re.M)
PATH_HINT_RE = re.compile(
    r"""["']([^"']*(?:/|\\)?(?:scripts_base|saida_excel|saida_avaliacao|arquivos_transcritos|_painel_uploads|_painel_backup|models|data|datasets)[^"']*)["']"""
)

imports = Counter()
path_hints = Counter()
files_to_hints = defaultdict(list)

for f in PY_FILES:
    text = f.read_text(encoding="utf-8", errors="ignore")
    for m in IMPORT_RE.findall(text):
        imports[m.split(".")[0]] += 1
    for m in PATH_HINT_RE.findall(text):
        path_hints[m] += 1
        files_to_hints[f.relative_to(ROOT)].append(m)

print("\n=== TOP IMPORTS (bibliotecas usadas no código) ===")
for name, n in imports.most_common(40):
    print(f"{name:25} {n}")

print("\n=== PATH HINTS (pastas/arquivos citados no código) ===")
for p, n in path_hints.most_common(60):
    print(f"{p:60} {n}")

print("\n=== POR ARQUIVO (o que cada .py cita de paths) ===")
for f, hints in sorted(files_to_hints.items(), key=lambda x: str(x[0])):
    print(f"\n# {f}")
    for h in sorted(set(hints)):
        print(f"  - {h}")
