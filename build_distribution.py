# -*- coding: utf-8 -*-
"""
BuildDistribution — Compilação, empacotamento e distribuição de módulos
========================================================================
Ao ser executado (inclusive por duplo clique):
  1. Compila todos os módulos definidos em MODULES para .pyc
  2. Remove os originais .py
  3. Empacota os .pyc em um arquivo de distribuição (.dist)
  4. Remove os .pyc (plugin para de funcionar)
  5. Opcionalmente incorpora uma chave de licença no pacote

O plugin para de funcionar após a execução.
Para restaurar, use Configurações → 🔑 → "📦 Restaurar Distribuição"
e selecione o arquivo .dist.

Uso programático:
    from build_distribution import BuildDistribution

    builder = BuildDistribution()
    builder.build()  # Compila + empacota + limpa
"""

import os
import py_compile
import shutil
import subprocess
import sys
import zipfile
import tempfile
import json
from pathlib import Path


# ======================================================================
# CONSTANTES
# ======================================================================

# Chave de licença opcional incorporada no pacote de distribuição
# Se vazia "", nenhuma chave é adicionada
DISTRIBUTION_KEY = "7N1V9-2S1H9-5G9K4"

# Nome do arquivo de saída (sem extensão) — extensão .dist
DISTRIBUTION_FILENAME = "cadmus_distribution"

# ======================================================================
# Módulos a serem compilados na execução direta
# ======================================================================
# Exemplo de dicionário completo (não apagar - referência)
_MODULES_EXAMPLE = {
    "plugins": [
        "PathExtensionPlugin.py",
    ],
    "utils/judge": [
        "SimpleSPBJudge.py",
        "ScoreSPBJudge.py",
    ],
    "core/config": [
        "RegistryManager.py",
        "ToolRegistry.py",
        "LogUtils.py",
        "LogCleanupUtils.py",
        "Security.py",
    ],
    "core/services": [
        "DronePipelineService.py",
        "ReportGenerationService.py",
    ],
    "core/task": [
        "PathExtensionTask.py",
    ],
    "core/engine_tasks": [
        "PathExtensionStep.py",
    ],
}

# Módulos ativos para compilação
MODULES = {
    "plugins": [
        "PathExtensionPlugin.py",
    ],
    "core/config": [
        "RegistryManager.py",
    ],
    "core/task": [
        "PathExtensionTask.py",
    ],
    "core/engine_tasks": [
        "PathExtensionStep.py",
    ],
}
# ======================================================================

# Caminhos conhecidos do Python do QGIS (prioridade da versão mais recente)
_QGIS_PYTHON_CANDIDATES = [
    r"C:\Program Files\QGIS 4.0.0\apps\Python312\python.exe",
    r"C:\Program Files\QGIS 4.0.0\bin\python.exe",
    r"C:\Program Files\QGIS 3.40.14\apps\Python312\python.exe",
    r"C:\Program Files\QGIS 3.40.14\bin\python.exe",
    r"C:\Program Files\QGIS 3.34.12\apps\Python312\python.exe",
    r"C:\Program Files\QGIS 3.34.12\bin\python.exe",
    r"C:\Program Files\QGIS 3.16\apps\Python37\python.exe",
    r"C:\OSGeo4W\apps\Python39\python.exe",
    r"C:\OSGeo4W64\apps\Python39\python.exe",
]


def _find_qgis_python() -> str:
    """Retorna o caminho do Python do QGIS ou string vazia."""
    for c in _QGIS_PYTHON_CANDIDATES:
        if os.path.isfile(c):
            return c
    return ""


class BuildDistribution:
    """
    Compila módulos .py para .pyc, remove originais, empacota em .dist
    e remove os .pyc, deixando o plugin desabilitado até restaurar.
    """

    def __init__(self, root_dir: str | Path | None = None):
        """
        Args:
            root_dir: Diretório raiz do projeto.
                      Se None, usa o diretório onde este script está.
        """
        self._root = Path(root_dir).resolve() if root_dir else Path(__file__).resolve().parent

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def build(self, modules: dict | None = None) -> bool:
        """
        Executa o pipeline completo: compilar → remover .py → empacotar → remover .pyc.

        Args:
            modules: Dicionário de módulos. Se None, usa MODULES.

        Returns:
            True se tudo OK.
        """
        if modules is None:
            modules = MODULES

        print("=" * 55)
        print("  BuildDistribution — Pipeline completo")
        print("=" * 55)

        # 1. Compilar e remover .py
        compile_ok, compile_fail = self.compile_modules(modules)
        if compile_fail > 0:
            print("[BuildDistribution] ERRO: Falha na compilação. Abortando.")
            return False

        # 2. Empacotar .pyc em .dist
        package_ok = self._package(modules)
        if not package_ok:
            print("[BuildDistribution] ERRO: Falha no empacotamento.")
            return False

        # 3. Remover .pyc (plugin para de funcionar)
        self._remove_pyc(modules)

        print("=" * 55)
        print(f"  BUILD CONCLUÍDO: {compile_ok} módulo(s) compilado(s)")
        print(f"  Pacote: {DISTRIBUTION_FILENAME}.dist")
        print("=" * 55)
        print("  O plugin agora está desabilitado.")
        print("  Para restaurar, use Configurações → 🔑")
        print("  → '📦 Restaurar Distribuição'")
        print("=" * 55)
        return True

    def compile_and_remove(self, rel_path: str) -> bool:
        """
        Compila um arquivo .py para .pyc e remove o original.

        Se um .pyc antigo existir, ele é removido antes da compilação.

        Args:
            rel_path: Caminho relativo ao root_dir.

        Returns:
            True se bem-sucedido.
        """
        source = self._root / rel_path
        if not source.exists():
            print(f"[BuildDistribution] ERRO: Arquivo não encontrado: {source}")
            return False

        if source.suffix != ".py":
            print(f"[BuildDistribution] ERRO: '{source.name}' não é um arquivo .py")
            return False

        dest_pyc = source.with_suffix(".pyc")

        # Remove .pyc antigo se existir
        if dest_pyc.exists():
            dest_pyc.unlink()
            print(f"[BuildDistribution] .pyc antigo removido: {dest_pyc.relative_to(self._root)}")

        qgis_python = _find_qgis_python()
        if qgis_python:
            ok = self._compile_with_qgis_python(qgis_python, source, dest_pyc)
        else:
            print("[BuildDistribution] Aviso: Python do QGIS não encontrado.",
                  "Usando Python atual. O .pyc pode não ser carregado pelo QGIS.")
            ok = self._compile_with_current_python(source, dest_pyc)

        if not ok:
            return False

        try:
            source.unlink()
            print(f"[BuildDistribution] .py removido: {source.relative_to(self._root)}")
        except OSError as exc:
            print(f"[BuildDistribution] ERRO ao remover .py: {exc}")
            return False

        print(f"[BuildDistribution] OK — {rel_path} -> {dest_pyc.relative_to(self._root)} "
              f"({dest_pyc.stat().st_size // 1024} KB)")
        return True

    def compile_modules(self, modules: dict | None = None) -> tuple[int, int]:
        """
        Compila todos os módulos definidos em um dicionário.

        Args:
            modules: Dicionário no formato { "diretório": ["arquivo1.py", ...] }

        Returns:
            (sucessos, falhas)
        """
        if modules is None:
            modules = MODULES

        success = 0
        fail = 0

        for directory, files in modules.items():
            for filename in files:
                rel_path = f"{directory}/{filename}"
                if self.compile_and_remove(rel_path):
                    success += 1
                else:
                    fail += 1

        return success, fail

    # ------------------------------------------------------------------
    # Empacotamento (.dist)
    # ------------------------------------------------------------------

    def _package(self, modules: dict) -> bool:
        """
        Empacota os .pyc gerados em um arquivo .dist (formato ZIP).

        O arquivo contém:
        - manifest.json (metadados + chave de licença opcional)
        - Os .pyc com seus caminhos relativos

        Returns:
            bool: True se OK.
        """
        dist_path = self._root / f"{DISTRIBUTION_FILENAME}.dist"
        print(f"[BuildDistribution] Empacotando distribuição: {dist_path}")

        try:
            with tempfile.TemporaryDirectory(prefix="cadmus_dist_") as tmp_dir:
                tmp_zip = os.path.join(tmp_dir, "dist.zip")

                with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                    # Manifest
                    manifest = {
                        "version": 1,
                        "key": DISTRIBUTION_KEY if DISTRIBUTION_KEY else "",
                        "modules": {},
                    }

                    for directory, files in modules.items():
                        dir_path = self._root / directory
                        manifest["modules"][directory] = []
                        for filename in files:
                            pyc_path = dir_path / Path(filename).with_suffix(".pyc").name
                            if pyc_path.exists():
                                arcname = f"{directory}/{pyc_path.name}"
                                zf.write(str(pyc_path), arcname)
                                manifest["modules"][directory].append(pyc_path.name)
                                print(f"[BuildDistribution]   + {arcname}")

                    # Escreve manifest.json no ZIP
                    zf.writestr("manifest.json", json.dumps(manifest, indent=2))

                # Copia para o destino final
                if dist_path.exists():
                    os.remove(dist_path)
                shutil.copy2(tmp_zip, dist_path)

            size_kb = dist_path.stat().st_size // 1024
            print(f"[BuildDistribution] Pacote gerado: {dist_path.name} ({size_kb} KB)")

            if DISTRIBUTION_KEY:
                print(f"[BuildDistribution] Chave incorporada: {DISTRIBUTION_KEY}")

            return True

        except Exception as exc:
            print(f"[BuildDistribution] ERRO no empacotamento: {exc}")
            return False

    def _remove_pyc(self, modules: dict):
        """
        Remove os arquivos .pyc após o empacotamento,
        deixando o plugin desabilitado.
        """
        print("[BuildDistribution] Removendo .pyc (plugin será desabilitado)...")
        removed = 0
        for directory, files in modules.items():
            dir_path = self._root / directory
            for filename in files:
                pyc_path = dir_path / Path(filename).with_suffix(".pyc").name
                if pyc_path.exists():
                    try:
                        pyc_path.unlink()
                        print(f"[BuildDistribution]   .pyc removido: {directory}/{pyc_path.name}")
                        removed += 1
                    except OSError as exc:
                        print(f"[BuildDistribution]   ERRO ao remover .pyc: {exc}")
        print(f"[BuildDistribution] {removed} .pyc removido(s).")

    # ------------------------------------------------------------------
    # Compilação
    # ------------------------------------------------------------------

    def _compile_with_qgis_python(
        self, python_exe: str, source: Path, dest_pyc: Path
    ) -> bool:
        """Compila usando o Python do QGIS via subprocess."""
        rel = source.relative_to(self._root)
        print(f"[BuildDistribution] Compilando (QGIS Python): {rel}")

        script = (
            "import py_compile, sys\n"
            f"src = {str(source)!r}\n"
            f"dst = {str(dest_pyc)!r}\n"
            "try:\n"
            "    py_compile.compile(src, cfile=dst, doraise=True)\n"
            "    sys.exit(0)\n"
            "except py_compile.PyCompileError as e:\n"
            "    print(f'[BuildDistribution] ERRO na compilação: {e}')\n"
            "    sys.exit(1)\n"
        )

        result = subprocess.run(
            [python_exe, "-c", script],
            capture_output=True, text=True, timeout=60,
            cwd=str(self._root),
        )

        if result.stdout:
            for line in result.stdout.strip().splitlines():
                if line.startswith("[BuildDistribution]"):
                    print(line)

        if result.returncode != 0:
            if result.stderr:
                print(f"[BuildDistribution] Stderr: {result.stderr.strip()[-300:]}")
            return False

        if dest_pyc.exists():
            print(f"[BuildDistribution] .pyc gerado: {dest_pyc.relative_to(self._root)} "
                  f"({dest_pyc.stat().st_size // 1024} KB)")
        return True

    def _compile_with_current_python(self, source: Path, dest_pyc: Path) -> bool:
        """Compila usando o Python atual (fallback)."""
        rel = source.relative_to(self._root)
        print(f"[BuildDistribution] Compilando (Python atual): {rel}")

        try:
            py_compile.compile(
                str(source),
                cfile=str(dest_pyc),
                doraise=True,
            )
        except py_compile.PyCompileError as exc:
            print(f"[BuildDistribution] ERRO na compilação: {exc}")
            return False

        if dest_pyc.exists():
            print(f"[BuildDistribution] .pyc gerado: {dest_pyc.relative_to(self._root)} "
                  f"({dest_pyc.stat().st_size // 1024} KB)")
        return True

    @property
    def root(self) -> Path:
        return self._root


# ------------------------------------------------------------------
# CLI — execução direta (inclusive duplo clique)
# ------------------------------------------------------------------
if __name__ == "__main__":
    builder = BuildDistribution()

    print("=" * 55)
    print("  BuildDistribution — Compilando e empacotando")
    print("=" * 55)

    qgis_py = _find_qgis_python()
    if qgis_py:
        print(f"  Python QGIS: {qgis_py}")
    else:
        print("  Aviso: Python do QGIS não encontrado!")

    success = builder.build()

    if not success:
        print("\n  BUILD FALHOU!")
        sys.exit(1)