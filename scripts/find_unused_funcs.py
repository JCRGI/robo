from __future__ import annotations

import ast
import sys
import tokenize
from pathlib import Path
from typing import Dict, Iterable, List, Tuple  # REMOVIDO: Set

ROOT = Path(__file__).resolve().parents[1]

EXCLUDE_DIRS = {
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "assets",
    "templates",
}
EXCLUDE_FILES_SUFFIX = {".pyc", ".pyo"}
EXCLUDE_GLOBS = set()

# Ignorar dunders e nomes comumente invocados indiretamente por frameworks
IGNORE_FUNC_NAMES = {
    "__init__",
    "__enter__",
    "__exit__",
    "__repr__",
    "__str__",
    "__call__",
    "main",
}


def iter_py_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.py"):
        rel = p.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if any(str(rel).endswith(suf) for suf in EXCLUDE_FILES_SUFFIX):
            continue
        skip = False
        for g in EXCLUDE_GLOBS:
            if rel.match(g):
                skip = True
                break
        if not skip:
            yield p


class DefInfo:
    def __init__(self, file: Path, name: str, lineno: int, is_method: bool, decorators: List[str]):
        self.file = file
        self.name = name
        self.lineno = lineno
        self.is_method = is_method
        self.decorators = decorators


def decorator_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> List[str]:
    names = []
    for d in node.decorator_list:
        try:
            if isinstance(d, ast.Name):
                names.append(d.id)
            elif isinstance(d, ast.Attribute):
                names.append(d.attr)
            elif isinstance(d, ast.Call):
                if isinstance(d.func, ast.Name):
                    names.append(d.func.id)
                elif isinstance(d.func, ast.Attribute):
                    names.append(d.func.attr)
        except Exception:
            pass
    return names


def collect_defs(pyfile: Path) -> List[DefInfo]:
    try:
        src = pyfile.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        src = pyfile.read_text(encoding="latin1")
    tree = ast.parse(src, filename=str(pyfile))
    defs: List[DefInfo] = []
    parent_stack: List[ast.AST] = []

    def visit(node: ast.AST):
        parent_stack.append(node)
        try:
            for child in ast.iter_child_nodes(node):
                # Track parent for is_method
                parent_stack.append(child)
                try:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        is_method = any(isinstance(p, ast.ClassDef) for p in parent_stack)
                        decs = decorator_names(child)
                        defs.append(DefInfo(pyfile, child.name, child.lineno, is_method, decs))
                    elif isinstance(child, ast.ClassDef):
                        pass
                    visit(child)
                finally:
                    parent_stack.pop()
        finally:
            parent_stack.pop()

    visit(tree)
    return defs


def index_tokens(pyfile: Path) -> List[Tuple[str, int]]:
    names: List[Tuple[str, int]] = []
    try:
        with tokenize.open(pyfile) as f:
            tokens = tokenize.generate_tokens(f.readline)
            for tok in tokens:
                if tok.type == tokenize.NAME:
                    names.append((tok.string, tok.start[0]))  # (name, line)
    except Exception:
        pass
    return names


def main():
    root = ROOT
    files = list(iter_py_files(root))
    token_index: Dict[Path, List[Tuple[str, int]]] = {p: index_tokens(p) for p in files}
    all_defs: List[DefInfo] = []
    for f in files:
        all_defs.extend(collect_defs(f))

    # Heurísticas para ignorar falsos positivos:
    # - funções com decorator 'route' (Flask): app.route / bp_*.route
    # - dunders e nomes comuns em frameworks
    def should_ignore(d: DefInfo) -> bool:
        if d.name in IGNORE_FUNC_NAMES:
            return True
        if "route" in d.decorators:
            return True
        return False

    candidates = []
    for d in all_defs:
        if should_ignore(d):
            continue
        # Procura qualquer ocorrência do nome fora da própria linha de definição
        found = False
        for f, toks in token_index.items():
            for name, line in toks:
                if name != d.name:
                    continue
                if f == d.file and line == d.lineno:
                    continue
                found = True
                break
            if found:
                break
        if not found:
            kind = "method" if d.is_method else "function"
            candidates.append((d.file.relative_to(root), d.lineno, kind, d.name))

    # Ordena por arquivo e linha
    candidates.sort(key=lambda x: (str(x[0]), x[1]))
    if not candidates:
        print("Nenhum candidato a função/método não usado encontrado.")
        return
    print("Prováveis funções/métodos não usados (heurístico):")
    for rel, line, kind, name in candidates:
        print(f"{rel}:{line}: {kind} '{name}'")


if __name__ == "__main__":
    sys.exit(main())
