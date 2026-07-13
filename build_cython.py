# -*- coding: utf-8 -*-
"""
Build Script — Compilação Cython para Cadmus
=============================================
Script de build completo. Ao ser executado:
  1. Detecta Python do QGIS e Cython
  2. Compila módulos selecionados com Cython (um por vez)
  3. Copia .pyd para as pastas corretas (remove sufixo cp39-win_amd64)
  4. Remove artefatos temporários (.c, build/, __pycache__)

Uso:
    python build_cython.py                    # Compila tudo (judge + config)
    python build_cython.py --judge            # Só judges
    python build_cython.py --config           # Só config
    python build_cython.py --services         # Só services (experimental)
    python build_cython.py --all              # Compila tudo (judge+config+services)
    python build_cython.py --clean            # Remove .c, .pyd, build/
    python build_cython.py --check            # Verifica ambiente

Requisitos:
    - Python 3.9+ (mesmo do QGIS)
    - Cython instalado (no Python do sistema ou QGIS)
    - Microsoft C++ Build Tools
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
PLUGIN_ROOT = Path(__file__).resolve().parent

# Módulos disponíveis para compilação
MODULES = {
    "judge": {
        "path": "utils/judge",
        "files": [
            "SimpleSPBJudge.py",
            "ScoreSPBJudge.py",
        ],
        "desc": "Algoritmos de julgamento geométrico (strips/faixas)",
    },
    "config": {
        "path": "core/config",
        "files": [
            "RegistryManager.py",
            "ToolRegistry.py",
            "LogUtils.py",
            "LogCleanupUtils.py",
            "Security.py",
        ],
        "desc": "Gerenciamento de licença, registry e logging",
    },
    "single": {
        "path": "utils/judge",
        "files": [
            "SequentialPointBreakJudge.py",
        ],
        "desc": "Algoritmo pesado de julgamento (compilação experimental)",
    },
    "services": {
        "path": "core/services",
        "files": [
            "DronePipelineService.py",
            "ReportGenerationService.py",
        ],
        "desc": "Serviços de pipeline e relatórios (experimental)",
    },
}

# Paths para localizar Cython no sistema
CYTHON_CANDIDATES = [
    r"C:\Users\marti\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages",
    r"C:\Users\marti\AppData\Local\Python\Python39\Lib\site-packages",
    r"C:\Users\marti\AppData\Local\Programs\Python\Python39\Lib\site-packages",
    r"C:\Users\marti\AppData\Roaming\Python\Python39\site-packages",
    r"C:\Users\marti\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.14_qbz5n2kfra8p0\LocalCache\local-packages\Python314\site-packages",
]


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def _log(msg: str, level: str = "INFO"):
    print(f"[{level}] {msg}")


def _find_qgis_python() -> str:
    """Detecta o Python do QGIS no sistema."""
    candidates = [
        r"C:\Program Files\QGIS 3.16.16\apps\Python39\python.exe",
        r"C:\Program Files\QGIS 3.28.3\apps\Python39\python.exe",
        r"C:\Program Files\QGIS 3.34.0\apps\Python39\python.exe",
        r"C:\Program Files\QGIS 3.36.0\apps\Python39\python.exe",
        r"C:\OSGeo4W\apps\Python39\python.exe",
        r"C:\OSGeo4W64\apps\Python39\python.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return ""


def _find_any_python() -> str:
    """Fallback: tenta python do PATH."""
    for cmd in ["python", "python3", "py"]:
        try:
            r = subprocess.run(
                [cmd, "-c", "import sys; print(sys.version.split()[0])"],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                return cmd
        except Exception:
            continue
    return ""


def _get_cython_env() -> dict:
    """Retorna dict de env com PYTHONPATH para achar Cython."""
    env = os.environ.copy()
    for candidate in CYTHON_CANDIDATES:
        cython_init = os.path.join(candidate, "Cython", "__init__.py")
        if os.path.isfile(cython_init):
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{candidate};{existing}" if existing else candidate
            return env, candidate
    return env, ""


def _check_cython(python_exe: str, env: dict) -> bool:
    """Verifica se Cython está acessível no Python informado."""
    try:
        result = subprocess.run(
            [python_exe, "-c", "import Cython; print(Cython.__version__)"],
            capture_output=True, text=True, env=env,
            cwd=str(PLUGIN_ROOT), timeout=30,
        )
        if result.returncode == 0:
            _log(f"Cython OK — versão {result.stdout.strip()}")
            return True
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Compilação Cython
# ---------------------------------------------------------------------------

def _build_single(py_path: str, module_name: str, python_exe: str, env: dict) -> bool:
    """Compila um único arquivo .py com Cython."""
    with tempfile.TemporaryDirectory(prefix="cadmus_build_") as temp_dir:
        setup_path = os.path.join(temp_dir, "setup_cython.py")
        with open(setup_path, "w", encoding="utf-8") as f:
            f.write(
                '# -*- coding: utf-8 -*-\n'
                '"""Setup gerado automaticamente pelo build_cython.py"""\n'
                'import sys\n'
                'from setuptools import setup, Extension\n'
                'from Cython.Build import cythonize\n\n'
                f'ext = Extension(\n'
                f'    {module_name!r},\n'
                f'    sources=[{py_path!r}],\n'
                f')\n'
                'setup(\n'
                '    ext_modules=cythonize(\n'
                '        [ext],\n'
                '        language_level="3",\n'
                '        compiler_directives={\n'
                '            "binding": False,\n'
                '            "boundscheck": False,\n'
                '            "wraparound": False,\n'
                '            "initializedcheck": False,\n'
                '            "cdivision": True,\n'
                '            "embedsignature": False,\n'
                '        },\n'
                '    ),\n'
                '    script_args=["build_ext", "--inplace"],\n'
                ')\n'
            )

        result = subprocess.run(
            [python_exe, setup_path],
            capture_output=True, text=True, env=env,
            cwd=str(PLUGIN_ROOT), timeout=300,
        )

        if result.returncode != 0:
            stderr_clean = result.stderr.strip()[-500:]
            _log(f"    Erro: {stderr_clean}", "ERROR")
            return False

        # Copia .pyd gerado do build/ para o local correto
        build_dir = PLUGIN_ROOT / "build"
        target_dir = Path(py_path).parent
        if build_dir.exists():
            for pyd_file in build_dir.rglob("*.pyd"):
                if module_name in pyd_file.name:
                    dest = target_dir / f"{module_name}.pyd"
                    shutil.copy2(pyd_file, dest)
                    _log(f"    → {dest.relative_to(PLUGIN_ROOT)} "
                         f"({os.path.getsize(dest) // 1024} KB)")
                    break

        return True


def _compile_selected(selected: list, python_exe: str, env: dict) -> bool:
    """Compila módulos selecionados, um arquivo por vez."""
    all_ok = True

    for module_name in selected:
        mod = MODULES[module_name]
        mod_path = PLUGIN_ROOT / mod["path"]
        _log(f"\n--- {mod['desc']} ---")

        for py_file in mod["files"]:
            full_path = mod_path / py_file
            if not full_path.exists():
                _log(f"  ⚠ Pulando (não encontrado): {py_file}")
                continue

            stem = Path(py_file).stem
            _log(f"  Compilando: {py_file}...")

            ok = _build_single(str(full_path), stem, python_exe, env)
            if ok:
                # Remove arquivo .c gerado
                c_file = mod_path / f"{stem}.c"
                if c_file.exists():
                    c_file.unlink()
                _log(f"  ✔ OK")
            else:
                _log(f"  ✘ FALHA")
                all_ok = False

    return all_ok


# ---------------------------------------------------------------------------
# Limpeza
# ---------------------------------------------------------------------------

def _clean_all():
    """Remove todos artefatos gerados pelo Cython (.c, .pyd, build/, __pycache__)."""
    ext = ".pyd"
    removed = 0

    for mod_name, mod in MODULES.items():
        mod_path = PLUGIN_ROOT / mod["path"]
        for py_file in mod["files"]:
            stem = Path(py_file).stem

            # Remove .c
            c_file = mod_path / f"{stem}.c"
            if c_file.exists():
                c_file.unlink()
                _log(f"  Removido: {mod['path']}/{stem}.c")
                removed += 1

            # Remove .pyd
            pyd_file = mod_path / f"{stem}{ext}"
            if pyd_file.exists():
                pyd_file.unlink()
                _log(f"  Removido: {mod['path']}/{stem}{ext}")
                removed += 1

    # Remove build/
    build_dir = PLUGIN_ROOT / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
        _log(f"  Removido: build/")
        removed += 1

    # Remove __pycache__ das pastas compiladas
    for mod_name, mod in MODULES.items():
        cache = PLUGIN_ROOT / mod["path"] / "__pycache__"
        if cache.exists():
            shutil.rmtree(cache)
            _log(f"  Removido: {mod['path']}/__pycache__")

    # Remove .pyd com sufixo na raiz (cp39-win_amd64)
    for f in PLUGIN_ROOT.glob("*.pyd"):
        f.unlink()
        _log(f"  Removido raiz: {f.name}")
        removed += 1

    if removed == 0:
        _log("Nada para limpar.")
    else:
        _log(f"Limpeza concluída. {removed} arquivo(s) removido(s).")


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------

def _run_check(python_exe: str, env: dict):
    """Verifica o ambiente de desenvolvimento."""
    _log("=" * 50)
    _log("  VERIFICAÇÃO DE AMBIENTE")
    _log("=" * 50)

    # Versão Python
    result = subprocess.run(
        [python_exe, "--version"], capture_output=True, text=True, timeout=15,
    )
    _log(f"Python: {result.stdout.strip() or result.stderr.strip()}")
    _log(f"Executável: {python_exe}")

    # Cython
    has_cython = _check_cython(python_exe, env)
    _log(f"Cython: {'✓ INSTALADO' if has_cython else '✘ NÃO ENCONTRADO'}")

    # VS Build Tools
    vswhere = r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    if os.path.isfile(vswhere):
        r2 = subprocess.run(
            [vswhere, "-latest", "-property", "catalog_productLine"],
            capture_output=True, text=True, timeout=15,
        )
        _log(f"Visual Studio: {r2.stdout.strip() or 'não encontrado'}")
    else:
        _log("Visual Studio: vswhere não encontrado (pode não ter Build Tools)")

    # Módulos
    _log("\nMódulos disponíveis para compilação:")
    for mod_name, mod in MODULES.items():
        for py_file in mod["files"]:
            fp = PLUGIN_ROOT / mod["path"] / py_file
            status = "✓" if fp.exists() else "✘"
            size = fp.stat().st_size if fp.exists() else 0
            _log(f"  [{status}] {mod['path']}/{py_file} ({size // 1024} KB)")

    _log("=" * 50)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build script Cython para Cadmus - compila .py → .pyd para performance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python build_cython.py              # Compila judje + config\n"
            "  python build_cython.py --all        # Compila tudo\n"
            "  python build_cython.py --judge      # Só judges\n"
            "  python build_cython.py --clean      # Remove artefatos\n"
            "  python build_cython.py --check      # Verifica ambiente\n"
        ),
    )
    parser.add_argument("--judge", action="store_true",
                        help="Compilar apenas utils/judge/")
    parser.add_argument("--config", action="store_true",
                        help="Compilar apenas core/config/")
    parser.add_argument("--services", action="store_true",
                        help="Compilar apenas core/services/ (experimental)")
    parser.add_argument("--single", action="store_true",
                        help="Compilar SequentialPointBreakJudge (experimental)")
    parser.add_argument("--all", action="store_true",
                        help="Compilar todos os módulos")
    parser.add_argument("--python", type=str, default=None,
                        help="Caminho do Python do QGIS")
    parser.add_argument("--clean", action="store_true",
                        help="Remove .c, .pyd, build/")
    parser.add_argument("--check", action="store_true",
                        help="Verifica ambiente sem compilar")

    args = parser.parse_args()

    # ── Detecta Python ──────────────────────────────────────────────
    python_exe = args.python or _find_qgis_python() or _find_any_python()
    if not python_exe or not os.path.isfile(python_exe):
        _log("Python do QGIS não encontrado.", "ERROR")
        _log("Use --python para especificar o caminho.", "INFO")
        sys.exit(1)

    # ── Detecta Cython ──────────────────────────────────────────────
    env, cython_path = _get_cython_env()
    if cython_path:
        _log(f"Cython: {cython_path}")
    else:
        _log("Cython não encontrado nos paths padrão.", "WARN")

    _log(f"Python: {python_exe}")

    # ── Check ───────────────────────────────────────────────────────
    if args.check:
        _run_check(python_exe, env)
        return

    # ── Clean ───────────────────────────────────────────────────────
    if args.clean:
        _clean_all()
        return

    # ── Seleciona módulos ──────────────────────────────────────────
    selected = []
    if args.all:
        selected = list(MODULES.keys())
    elif args.judge:
        selected = ["judge"]
    elif args.config:
        selected = ["config"]
    elif args.services:
        selected = ["services"]
    elif args.single:
        selected = ["single"]
    else:
        # Default: judge + config (os que compilam com sucesso)
        selected = ["judge", "config"]

    # ── Verifica Cython antes de compilar ──────────────────────────
    if not _check_cython(python_exe, env):
        _log("Cython não está acessível pelo Python do QGIS.", "ERROR")
        _log("Dica: Cython está instalado no Python 3.14 do sistema.", "INFO")
        _log("O script tenta usar PYTHONPATH para acessá-lo.", "INFO")
        _log("Caminhos verificados:", "INFO")
        for c in CYTHON_CANDIDATES:
            _log(f"  - {c} ({'✓' if os.path.isdir(c) else '✘'})")
        sys.exit(1)

    # ── Compila ────────────────────────────────────────────────────
    _log(f"\nMódulos a compilar: {', '.join(selected)}")
    success = _compile_selected(selected, python_exe, env)

    # ── Sumário ────────────────────────────────────────────────────
    _log("\n" + "=" * 50)
    if success:
        _log("  BUILD CONCLUÍDO ✓")
        _log("=" * 50)
        _log("Arquivos .pyd gerados nas pastas dos módulos.")
        _log("Reinicie o QGIS para carregar as versões compiladas.")
    else:
        _log("  BUILD PARCIAL (algumas falhas) ⚠")
        _log("=" * 50)
        _log("Motivos comuns de falha:")
        _log("  • LNK1104: arquivo muito grande (SequentialPointBreakJudge)")
        _log("  • qgis.core: dependência não resolvida (services)")
        _log("  • Arquivo .pyd já existe e está em uso (feche QGIS)")

    _log("\nPara limpar artefatos: python build_cython.py --clean")


if __name__ == "__main__":
    main()