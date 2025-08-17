import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VULTURE_REPORT = ROOT / "vulture-report.txt"

# Não tocar em rotas Flask nem configs sensíveis
SKIP_FILES = {
    "app.py",
    str(ROOT / "core" / "image_processor.py"),
}
SKIP_PREFIXES = (str(ROOT / "interface"),)

SAFE_REMOVE_FUNCS = set()  # (Path, name)
SAFE_REMOVE_IMPORTS = {}  # file -> set(names)
SAFE_REMOVE_VARS = {}  # file -> set(names)


def parse_report():
    if not VULTURE_REPORT.exists():
        return
    for line in VULTURE_REPORT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        path, rest = line.split(":", 1)
        file = (ROOT / path).resolve()
        if any(str(file).startswith(p) for p in SKIP_PREFIXES):
            continue
        if file.name in SKIP_FILES or str(file) in SKIP_FILES:
            continue
        msg = rest.split("unused", 1)[-1].strip()
        if msg.startswith("import"):
            name = msg.split("'")[1]
            SAFE_REMOVE_IMPORTS.setdefault(file, set()).add(name)
        elif msg.startswith("function"):
            name = msg.split("'")[1]
            SAFE_REMOVE_FUNCS.add((file, name))
        elif msg.startswith("variable") or msg.startswith("attribute"):
            name = msg.split("'")[1]
            SAFE_REMOVE_VARS.setdefault(file, set()).add(name)


def has_route_decorator(node: ast.AST) -> bool:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    for d in node.decorator_list:
        try:
            # app.route / bp_x.route / algo.route(...)
            if isinstance(d, ast.Attribute) and d.attr == "route":
                return True
            if (
                isinstance(d, ast.Call)
                and isinstance(d.func, ast.Attribute)
                and d.func.attr == "route"
            ):
                return True
        except Exception:
            pass
    return False


def remove_functions(src: str, file: Path, funcs: set[str]) -> str:
    tree = ast.parse(src)
    new_lines = src.splitlines()
    for node in list(ast.walk(tree)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in funcs:
            if has_route_decorator(node):
                continue
            start = node.lineno - 1
            end = (getattr(node, "end_lineno", None) or node.lineno) - 1
            for i in range(start, end + 1):
                new_lines[i] = None  # type: ignore
    return "\n".join(l for l in new_lines if l is not None)


def remove_imports(src: str, names: set[str]) -> str:
    lines = src.splitlines()
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("import "):
            parts = [p.strip() for p in stripped[7:].split(",")]
            keep = [p for p in parts if p.split(" as ")[0] not in names]
            if not keep:
                continue
            if len(keep) != len(parts):
                indent = line[: len(line) - len(line.lstrip())]
                out.append(f"{indent}import {', '.join(keep)}")
            else:
                out.append(line)
        elif stripped.startswith("from ") and " import " in stripped:
            mod, rest = stripped[5:].split(" import ", 1)
            items = [p.strip() for p in rest.split(",")]
            keep = [p for p in items if p.split(" as ")[0] not in names]
            if not keep:
                continue
            if len(keep) != len(items):
                indent = line[: len(line) - len(line.lstrip())]
                out.append(f"{indent}from {mod} import {', '.join(keep)}")
            else:
                out.append(line)
        else:
            out.append(line)
    return "\n".join(out)


def remove_assigns(src: str, file: Path, names: set[str]) -> str:
    if not names:
        return src
    tree = ast.parse(src)
    lines = src.splitlines()
    to_blank = set()

    def mark_node(n):
        start = n.lineno - 1
        end = (getattr(n, "end_lineno", None) or n.lineno) - 1
        for i in range(start, end + 1):
            to_blank.add(i)

    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = []
            for t in node.targets:
                if isinstance(t, ast.Name):
                    targets.append(t.id)
                elif isinstance(t, (ast.Tuple, ast.List)):
                    for elt in t.elts:
                        if isinstance(elt, ast.Name):
                            targets.append(elt.id)
            if any(t in names for t in targets):
                mark_node(node)
        elif isinstance(node, ast.AnnAssign):
            target = node.target.id if isinstance(node.target, ast.Name) else None
            if target and target in names:
                mark_node(node)

    if not to_blank:
        return src
    new = []
    for i, l in enumerate(lines):
        if i in to_blank:
            continue
        new.append(l)
    return "\n".join(new)


def main():
    parse_report()

    # Forçar remoções conhecidas e seguras
    forced_funcs = {
        ("core/emulador_manager.py", "carregar_emuladores"),
        ("core/emulador_manager.py", "salvar_emuladores"),
        ("core/emulador_manager.py", "duplicar_avd"),
        ("core/emulador_manager.py", "buscar_e_clicar_purchase"),
        ("core/robo_sequencial.py", "_log"),
        ("core/robo_sequencial.py", "_connect_by_port"),
        ("core/robo_sequencial.py", "_tap"),
    }
    for rel, name in forced_funcs:
        SAFE_REMOVE_FUNCS.add((ROOT / rel, name))

    forced_vars = {
        (ROOT / "core" / "emulador_manager.py"): {"EMULADORES_PATH"},
        (ROOT / "core" / "storage.py"): {"EMULADORES_PATH"},
    }
    for file, names in forced_vars.items():
        SAFE_REMOVE_VARS.setdefault(file, set()).update(names)

    files = (
        {f for f, _ in SAFE_REMOVE_FUNCS}
        | set(SAFE_REMOVE_IMPORTS.keys())
        | set(SAFE_REMOVE_VARS.keys())
    )
    for file in files:
        if not file.exists():
            continue
        src = file.read_text(encoding="utf-8")
        # imports
        if file in SAFE_REMOVE_IMPORTS:
            src = remove_imports(src, SAFE_REMOVE_IMPORTS[file])
        # functions
        funcs = {name for f, name in SAFE_REMOVE_FUNCS if f == file}
        if funcs:
            src = remove_functions(src, file, funcs)
        # variables / assigns
        if file in SAFE_REMOVE_VARS:
            src = remove_assigns(src, file, SAFE_REMOVE_VARS[file])

        file.write_text(src, encoding="utf-8")
        print(f"[aplicado] {file.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
