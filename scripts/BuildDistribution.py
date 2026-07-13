# -*- coding: utf-8 -*-
"""
BuildDistribution — Script de Build e Distribuição Ofuscada
============================================================
Empacota módulos Python do Cadmus em distribuição ofuscada via PyArmor.

Uso:
    python scripts/BuildDistribution.py                    # Build padrão (PathExtensionPlugin)
    python scripts/BuildDistribution.py --all              # Todos os módulos configurados
    python scripts/BuildDistribution.py --key="CHAVE"     # Com chave de licença embutida
    python scripts/BuildDistribution.py --clean            # Remove artefatos (.pyd, .c, build/)
    python scripts/BuildDistribution.py --info             # Mostra configuração atual

Fluxo:
    1. Verifica PyArmor e ambiente
    2. Para cada módulo: ofusca com PyArmor e gera .pyd
    3. Remove .py original após ofuscação bem-sucedida
    4. Empacota .pyd + metadata.json em .cadmus_dist
    5. Remove artefatos temporários

Requisitos:
    - PyArmor: pip install pyarmor
    - Python do QGIS 3.9+
    - Microsoft C++ Build Tools (para compilação nativa PyArmor)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
PLUGIN_ROOT = Path(__file__).resolve().parent.parent

DIST_EXTENSION = ".cadmus_dist"
DEFAULT_KEY = "7N1V9-2S1H9-5G9K4"

# Módulos disponíveis para distribuição ofuscada
MODULES = {
    "path_extension": {
        "files": [
            "plugins/PathExtensionPlugin.py",
        ],
        "desc": "Plug-in de extensão de caminhos (PathExtensionPlugin)",
    },
}

# Paths para localizar Python do QGIS
QGIS_PYTHON_CANDIDATES = [
    r"C:\Program Files\QGIS 3.16.16\apps\Python39\python.exe",
    r"C:\Program Files\QGIS 3.28.3\apps\Python39\python.exe",
    r"C:\Program Files\QGIS 3.34.0\apps\Python39\python.exe",
    r"C:\Program Files\QGIS 3.36.0\apps\Python39\python.exe",
    r"C:\OSGeo4W\apps\Python39\python.exe",
    r"C:\OSGeo4W64\apps\Python39\python.exe",
]

PYARMOR_CANDIDATES = [
    r"C:\Users\marti\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages",
    r"C:\Users\marti\AppData\Local\Python\Python39\Lib\site-packages",
    r"C:\Users\marti\AppData\Local\Programs\Python\Python39\Lib\site-packages",
    r"C:\Users\marti\AppData\Roaming\Python\Python39\site-packages",
]


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def _log(msg: str, level: str = "INFO"):
    """Log formatado para console."""
    print(f"[{level}] {msg}")


def _find_qgis_python() -> str:
    """Detecta o Python do QGIS no sistema."""
    for c in QGIS_PYTHON_CANDIDATES:
        if os.path.isfile(c):
            return c
    return ""


def _find_any_python() -> str:
    """Fallback: tenta python do PATH."""
    for cmd in ["python", "python3", "py"]:
        try:
            r = subprocess.run(
                [cmd, "-c", "import sys; print(sys.version.split()[0])"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                return cmd
        except Exception:
            continue
    return ""


def _get_pyarmor_env() -> tuple:
    """
    Retorna (env_dict, pyarmor_path) com PYTHONPATH ajustado
    para localizar PyArmor.
    """
    env = os.environ.copy()
    for candidate in PYARMOR_CANDIDATES:
        pyarmor_init = os.path.join(candidate, "pyarmor", "__init__.py")
        if os.path.isfile(pyarmor_init):
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{candidate};{existing}" if existing else candidate
            return env, candidate
    return env, ""


def _check_pyarmor(python_exe: str, env: dict) -> bool:
    """Verifica se PyArmor está acessível no Python informado."""
    try:
        result = subprocess.run(
            [python_exe, "-c", "import pyarmor; print(pyarmor.__version__)"],
            capture_output=True, text=True, env=env,
            cwd=str(PLUGIN_ROOT), timeout=30,
        )
        if result.returncode == 0:
            _log(f"PyArmor OK — versão {result.stdout.strip()}")
            return True
        _log(f"PyArmor não encontrado: {result.stderr.strip()}", "ERROR")
        return False
    except Exception as e:
        _log(f"Erro ao verificar PyArmor: {e}", "ERROR")
        return False


# ---------------------------------------------------------------------------
# Ofuscação PyArmor
# ---------------------------------------------------------------------------

def _obfuscate_file(py_path: str, python_exe: str, env: dict) -> bool:
    """
    Ofusca um único arquivo .py com PyArmor.

    O PyArmor gera um .pyd (ou .so) na pasta dist/.
    Este método copia o .pyd gerado para a pasta do arquivo original
    e remove o .py original.

    Args:
        py_path: Caminho completo para o arquivo .py
        python_exe: Caminho do Python do QGIS
        env: Environment com PYTHONPATH para PyArmor

    Returns:
        bool: True se ofuscação foi bem-sucedida
    """
    py_file = Path(py_path)
    stem = py_file.stem
    target_dir = py_file.parent

    _log(f"  Ofuscando: {py_path}...")

    # Comando PyArmor: gera .pyd na subpasta "dist/"
    cmd = [
        python_exe, "-m", "pyarmor", "gen",
        "--platform", "windows.x86_64",
        "--enable-suffix",  # Mantém sufixo de plataforma
        "--recursive",       # Ofusca dependências (se necessário)
        "-O", str(PLUGIN_ROOT / "build" / "dist"),
        str(py_path),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, env=env,
            cwd=str(PLUGIN_ROOT), timeout=300,
        )

        if result.returncode != 0:
            stderr_clean = result.stderr.strip()[-500:]
            _log(f"    Erro PyArmor: {stderr_clean}", "ERROR")
            return False

        # Procura .pyd gerado
        dist_dir = PLUGIN_ROOT / "build" / "dist"
        found_pyd = None
        if dist_dir.exists():
            for pyd_file in dist_dir.rglob("*.pyd"):
                # PyArmor nomeia com sufixo, ex: PathExtensionPlugin.cp39-win_amd64.pyd
                if stem in pyd_file.name:
                    found_pyd = pyd_file
                    break

        if not found_pyd:
            _log("    .pyd não encontrado na saída do PyArmor.", "ERROR")
            return False

        # Remove sufixo de plataforma do nome: ex: PathExtensionPlugin.cp39-win_amd64.pyd
        # → PathExtensionPlugin.pyd
        dest_name = f"{stem}.pyd"
        dest_path = target_dir / dest_name

        # Copia .pyd para o local do arquivo original
        shutil.copy2(found_pyd, dest_path)
        _log(f"    → {dest_path.relative_to(PLUGIN_ROOT)} "
             f"({os.path.getsize(dest_path) // 1024} KB)")

        # Remove .py original APÓS confirmação do .pyd
        if dest_path.exists():
            py_file.unlink(missing_ok=True)
            _log(f"    ✘ Removido: {py_path}")

        return True

    except subprocess.TimeoutExpired:
        _log("    Timeout: PyArmor excedeu 300s.", "ERROR")
        return False
    except Exception as e:
        _log(f"    Erro inesperado: {e}", "ERROR")
        return False


# ---------------------------------------------------------------------------
# Empacotamento .cadmus_dist
# ---------------------------------------------------------------------------

def _create_package(selected: list, output_name: str, key: Optional[str] = None) -> bool:
    """
    Cria o arquivo .cadmus_dist com os módulos ofuscados.

    Args:
        selected: Lista de nomes de módulos (ex: ["path_extension"])
        output_name: Nome base do arquivo de saída (sem extensão)
        key: Chave de licença opcional

    Returns:
        bool: True se o pacote foi criado com sucesso
    """
    package_path = PLUGIN_ROOT / f"{output_name}{DIST_EXTENSION}"
    _log(f"\n--- Criando pacote: {package_path} ---")

    # Coleta arquivos .pyd dos módulos ofuscados
    pyd_files = []
    for mod_name in selected:
        mod = MODULES.get(mod_name)
        if not mod:
            continue
        for py_file_rel in mod["files"]:
            pyd_rel = Path(py_file_rel).with_suffix(".pyd")
            pyd_path = PLUGIN_ROOT / pyd_rel
            if pyd_path.exists():
                pyd_files.append(pyd_rel)
                _log(f"  ✓ {pyd_rel}")
            else:
                _log(f"  ⚠ {pyd_rel} não encontrado (não ofuscado?)", "WARN")

    if not pyd_files:
        _log("Nenhum .pyd encontrado para empacotar. Execute o build primeiro.", "ERROR")
        return False

    # Prepara metadata
    metadata = {
        "version": "1.0",
        "modules": [str(p) for p in pyd_files],
    }
    if key:
        metadata["key"] = key

    # Cria pacote ZIP
    try:
        with tempfile.TemporaryDirectory(prefix="cadmus_pkg_") as tmpdir:
            tmp_root = Path(tmpdir)

            # Escreve metadata.json
            meta_path = tmp_root / "metadata.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            # Copia .pyd preservando estrutura de pastas
            for pyd_rel in pyd_files:
                src = PLUGIN_ROOT / pyd_rel
                dst = tmp_root / pyd_rel
                os.makedirs(dst.parent, exist_ok=True)
                shutil.copy2(src, dst)

            # Cria ZIP
            with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(tmp_root):
                    for file in files:
                        full_path = Path(root) / file
                        arcname = full_path.relative_to(tmp_root)
                        zf.write(full_path, arcname)

        size_kb = os.path.getsize(package_path) // 1024
        _log(f"\n  ✔ Pacote criado: {package_path.relative_to(PLUGIN_ROOT)} ({size_kb} KB)")
        _log(f"  Módulos: {len(pyd_files)} | Chave: {'✓' if key else '✘'}")

        # Limpa .pyd das pastas (só no pacote)
        for pyd_rel in pyd_files:
            pyd_path = PLUGIN_ROOT / pyd_rel
            if pyd_path.exists():
                pyd_path.unlink()
                _log(f"  Limpo: {pyd_rel}")

        return True

    except Exception as e:
        _log(f"Erro ao criar pacote: {e}", "ERROR")
        return False


# ---------------------------------------------------------------------------
# Limpeza
# ---------------------------------------------------------------------------

def _clean_all():
    """Remove artefatos de build (.pyd, .c, build/, __pycache__)."""
    removed = 0

    for mod_name, mod in MODULES.items():
        for py_file in mod["files"]:
            py_path = Path(py_file)
            stem = py_path.stem
            target_dir = PLUGIN_ROOT / py_path.parent

            # Remove .pyd
            pyd_file = target_dir / f"{stem}.pyd"
            if pyd_file.exists():
                pyd_file.unlink()
                _log(f"  Removido: {pyd_file.relative_to(PLUGIN_ROOT)}")
                removed += 1

    # Remove build/
    build_dir = PLUGIN_ROOT / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
        _log(f"  Removido: build/")
        removed += 1

    # Remove __pycache__ das pastas dos módulos
    for mod_name, mod in MODULES.items():
        for py_file in mod["files"]:
            cache = PLUGIN_ROOT / Path(py_file).parent / "__pycache__"
            if cache.exists():
                shutil.rmtree(cache)
                _log(f"  Removido: {cache.relative_to(PLUGIN_ROOT)}/__pycache__")

    # Remove .cadmus_dist
    for f in PLUGIN_ROOT.glob(f"*{DIST_EXTENSION}"):
        f.unlink()
        _log(f"  Removido: {f.name}")
        removed += 1

    if removed == 0:
        _log("Nada para limpar.")
    else:
        _log(f"Limpeza concluída. {removed} arquivo(s) removido(s).")


# ---------------------------------------------------------------------------
# Info
# ---------------------------------------------------------------------------

def _show_info():
    """Mostra configuração atual do sistema de distribuição."""
    _log("=" * 50)
    _log("  BUILD DISTRIBUTION — CONFIGURAÇÃO")
    _log("=" * 50)
    _log(f"Plugin root: {PLUGIN_ROOT}")
    _log(f"Extensão pacote: {DIST_EXTENSION}")
    _log(f"Chave padrão: {DEFAULT_KEY}")
    _log("")
    _log("Módulos disponíveis:")
    for mod_name, mod in MODULES.items():
        _log(f"  [{mod_name}] {mod['desc']}")
        for py_file in mod["files"]:
            fp = PLUGIN_ROOT / py_file
            status = "✓" if fp.exists() else "✘"
            _log(f"    {status} {py_file}")
    _log("=" * 50)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="BuildDistribution — Empacota módulos Python com PyArmor em .cadmus_dist",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python scripts/BuildDistribution.py                  # Build padrão\n"
            "  python scripts/BuildDistribution.py --all            # Todos módulos\n"
            "  python scripts/BuildDistribution.py --key=MINHA_CHAVE\n"
            "  python scripts/BuildDistribution.py --clean          # Remove artefatos\n"
            "  python scripts/BuildDistribution.py --info           # Mostra configuração\n"
        ),
    )
    parser.add_argument("--all", action="store_true",
                        help="Compilar todos os módulos configurados")
    parser.add_argument("--path_extension", action="store_true",
                        help="Compilar apenas PathExtensionPlugin")
    parser.add_argument("--key", type=str, default=None,
                        help="Chave de licença para embutir no pacote")
    parser.add_argument("--python", type=str, default=None,
                        help="Caminho do Python do QGIS")
    parser.add_argument("--output", type=str, default="cadmus_update",
                        help="Nome base do pacote de saída (sem extensão)")
    parser.add_argument("--clean", action="store_true",
                        help="Remove artefatos de build")
    parser.add_argument("--info", action="store_true",
                        help="Mostra configuração atual")

    args = parser.parse_args()

    # ── Info ────────────────────────────────────────────────────────────
    if args.info:
        _show_info()
        return

    # ── Clean ──────────────────────────────────────────────────────────
    if args.clean:
        _clean_all()
        return

    # ── Detecta Python ────────────────────────────────────────────────
    python_exe = args.python or _find_qgis_python() or _find_any_python()
    if not python_exe:
        _log("Python do QGIS não encontrado.", "ERROR")
        _log("Use --python para especificar o caminho.", "INFO")
        sys.exit(1)

    # ── Detecta PyArmor ───────────────────────────────────────────────
    env, pyarmor_path = _get_pyarmor_env()
    if pyarmor_path:
        _log(f"PyArmor: {pyarmor_path}")
    else:
        _log("PyArmor não encontrado nos paths padrão.", "WARN")

    _log(f"Python: {python_exe}")
    _log(f"Plugin: {PLUGIN_ROOT}")

    # ── Verifica PyArmor ─────────────────────────────────────────────
    if not _check_pyarmor(python_exe, env):
        _log("PyArmor não está acessível. Instale com: pip install pyarmor", "ERROR")
        sys.exit(1)

    # ── Seleciona módulos ─────────────────────────────────────────────
    selected = []
    if args.all:
        selected = list(MODULES.keys())
    elif args.path_extension:
        selected = ["path_extension"]
    else:
        # Default: path_extension
        selected = ["path_extension"]

    _log(f"\nMódulos a ofuscar: {', '.join(selected)}")

    # ── Ofusca ────────────────────────────────────────────────────────
    all_ok = True
    for mod_name in selected:
        mod = MODULES[mod_name]
        _log(f"\n--- {mod['desc']} ---")
        for py_file_rel in mod["files"]:
            py_path = PLUGIN_ROOT / py_file_rel
            if not py_path.exists():
                _log(f"  ⚠ Pulando (não encontrado): {py_file_rel}")
                continue

            ok = _obfuscate_file(str(py_path), python_exe, env)
            if ok:
                _log(f"  ✔ Ofuscado: {py_file_rel}")
            else:
                _log(f"  ✘ FALHA: {py_file_rel}")
                all_ok = False

    if not all_ok:
        _log("\n⚠ Algumas ofuscações falharam. Verifique os erros acima.", "WARN")
        # Continua para tentar empacotar o que foi ofuscado com sucesso

    # ── Empacota ──────────────────────────────────────────────────────
    key = args.key or DEFAULT_KEY
    package_ok = _create_package(selected, args.output, key)

    # ── Remove build temporário ──────────────────────────────────────
    build_dir = PLUGIN_ROOT / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
        _log("Build temporário removido.")

    # ── Sumário ──────────────────────────────────────────────────────
    _log("\n" + "=" * 50)
    if package_ok:
        _log("  BUILD DISTRIBUTION CONCLUÍDO ✓")
        _log("=" * 50)
        _log(f"Pacote gerado: {args.output}{DIST_EXTENSION}")
        _log("Copie o arquivo .cadmus_dist para instalação via RegistryDialog.")
    else:
        _log("  BUILD DISTRIBUTION FALHOU ✘")
        _log("=" * 50)


if __name__ == "__main__":
    # Import zipfile aqui (precisa estar no escopo)
    import zipfile
    if not hasattr(zipfile, "ZIP_DEFLATED"):
        zipfile.ZIP_DEFLATED = 8
    main()