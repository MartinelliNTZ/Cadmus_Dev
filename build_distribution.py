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
import subprocess
import sys
from pathlib import Path
from typing import Optional, Union, Tuple

from core.services.PackageManager import PackageManager

# ======================================================================
# CONSTANTES
# ======================================================================

# Chave de licença opcional incorporada no pacote de distribuição
# Se vazia "", nenhuma chave é adicionada
DISTRIBUTION_KEY = "6U5D9-4H0J8-6P1U4"
VERSION = "3.0.0.3"

# Nome do arquivo de saída (sem extensão) — extensão .dist
DISTRIBUTION_FILENAME = f"Cadmus_package_{VERSION}_dist"

# Nome do arquivo de distribuição com fontes .py (gerado antes da compilação)
SOURCE_DISTRIBUTION_FILENAME = f"Cadmus_package_{VERSION}_src"
# Nome do arquivo de distribuição com .pyc compilados (gerado após compilação)
PYC_DISTRIBUTION_FILENAME = f"Cadmus_package_{VERSION}_pyc"

ZIP_FILENAME = f"Cadmus-{VERSION}.zip"  # Nome do arquivo ZIP final (opcional)

# ======================================================================
# Módulos a serem compilados na execução direta
# ======================================================================
# Exemplo de dicionário completo (não apagar - referência)
_MODULES_EXAMPLE = {
    "plugins": [
        "PathExtensionPlugin.py",
        "DividePointsByStripsPlugin.py",
    ],
    "utils/judge": [
        "SimpleSPBJudge.py",
        "ScoreSPBJudge.py",
        "SequentialPointBreakJudge.py",
    ],
    "core/config": [
        "RegistryManager.py",
        "RegistryFileManager.py",
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
        "ReportGenerationTask.py",
    ],
    "core/engine_tasks": [
        "PathExtensionStep.py",
        "ReportGenerationStep.py",
    ],
    "utils/report": [
        "__init__.py",
        "AggregateAnalyzer.py",
        "AlertManager.py",
        "FlightAggregator.py",
        "IMGMetadata.py",
        "JsonMetadataManager.py",
        "RenderEngine.py",
        "ReportPapelineManager.py",
    ],
}
ZIP_PACKAGES = [
    "core",
    "i18n",
    "plugins",
    "processing",
    "resources",
    "utils",
    "__init__.py",
    "cadmus_plugin.py",
    "icon.png",
    "LICENSE",
    "metadata.txt",
    "NOTICE",
    "resources.py",
    "resources.qrc",
]

# Módulos ativos para compilação
MODULES = {
    "plugins": [
        "PathExtensionPlugin.py",
        "ReportMetadataPlugin.py",
        "DividePointsByStripsPlugin.py",
    ],
    "core/config": [
        "RegistryManager.py",
        "RegistryFileManager.py",
        "Security.py",
    ],
    "core/services": [
        "ReportGenerationService.py",
    ],
    "core/task": [
        "PathExtensionTask.py",
        "ReportGenerationTask.py",
    ],
    "core/engine_tasks": [
        "PathExtensionStep.py",
        "ReportGenerationStep.py",
    ],
    "utils/judge": [
        "SimpleSPBJudge.py",
        "ScoreSPBJudge.py",
        "SequentialPointBreakJudge.py",
    ],
    "utils/report": [
        "__init__.py",
        "AggregateAnalyzer.py",
        "AlertManager.py",
        "FlightAggregator.py",
        "IMGMetadata.py",
        "JsonMetadataManager.py",
        "RenderEngine.py",
        "ReportPapelineManager.py",
    ],
}
# ======================================================================

# Arquivos estáticos que são copiados diretamente para o .dist (sem compilação)
# Esses arquivos NÃO são removidos após o empacotamento
STATIC_FILES = [
    "resources/reports/config.yaml",
    "resources/reports/template.html",
]

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

    def __init__(self, root_dir: Union[str, Path] = None):
        """
        Args:
            root_dir: Diretório raiz do projeto.
                      Se None, usa o diretório onde este script está.
        """
        self._root = (
            Path(root_dir).resolve() if root_dir else Path(__file__).resolve().parent
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def build(self, modules: Optional[dict] = None) -> bool:
        """
        Executa o pipeline completo:
          1. Atualiza metadata.txt e AboutDialog.py com a versão em VERSION
          2. Remove todos os diretórios __pycache__ do projeto
          3. Empacota os .py originais em um .dist de fonte (antes de compilar)
          4. Compila todos os módulos para .pyc
          5. Remove os originais .py
          6. Empacota os .pyc em um segundo .dist
          7. Remove os .pyc (plugin para de funcionar)
          8. Remove novamente __pycache__
          9. Cria o pacote ZIP final com ZIP_PACKAGES

        Args:
            modules: Dicionário de módulos. Se None, usa MODULES.

        Returns:
            True se tudo OK.
        """
        if modules is None:
            modules = MODULES

        print("=" * 55)
        print("  BuildDistribution — Pipeline completo (2 distribuições)")
        print("=" * 55)

        # 0. Atualizar arquivos de versão (metadata.txt e AboutDialog.py)
        self._update_version_files()

        # 1. Remover todos os __pycache__ do projeto
        self._remove_pycache()

        # 2. Empacotar .py originais em .dist de fonte (antes da compilação)
        source_ok = self._package_source(modules)
        if not source_ok:
            print(
                "[BuildDistribution] ERRO: Falha no empacotamento da fonte. Abortando."
            )
            return False

        # 3. Compilar e remover .py
        compile_ok, compile_fail = self.compile_modules(modules)
        if compile_fail > 0:
            print("[BuildDistribution] ERRO: Falha na compilação. Abortando.")
            return False

        # 4. Empacotar .pyc em .dist
        package_ok = self._package(modules)
        if not package_ok:
            print("[BuildDistribution] ERRO: Falha no empacotamento.")
            return False

        # 5. Remover .pyc (plugin para de funcionar)
        self._remove_pyc(modules)

        # 6. Remover novamente __pycache__ (caso a compilação tenha gerado novos)
        self._remove_pycache()

        # 7. Criar o pacote ZIP final com todos os arquivos do plugin
        zip_ok = self._create_zip()
        if not zip_ok:
            print("[BuildDistribution] ERRO: Falha na criação do ZIP.")
            return False

        print("=" * 55)
        print(f"  BUILD CONCLUÍDO: {compile_ok} módulo(s) compilado(s)")
        print(f"  Pacote fonte (.py):     {SOURCE_DISTRIBUTION_FILENAME}.dist")
        print(f"  Pacote compilado (.pyc): {PYC_DISTRIBUTION_FILENAME}.dist")
        print(f"  Pacote ZIP:              {ZIP_FILENAME}")
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
            print(
                f"[BuildDistribution] .pyc antigo removido: {dest_pyc.relative_to(self._root)}"
            )

        qgis_python = _find_qgis_python()
        if qgis_python:
            ok = self._compile_with_qgis_python(qgis_python, source, dest_pyc)
        else:
            print(
                "[BuildDistribution] Aviso: Python do QGIS não encontrado.",
                "Usando Python atual. O .pyc pode não ser carregado pelo QGIS.",
            )
            ok = self._compile_with_current_python(source, dest_pyc)

        if not ok:
            return False

        try:
            source.unlink()
            print(f"[BuildDistribution] .py removido: {source.relative_to(self._root)}")
        except OSError as exc:
            print(f"[BuildDistribution] ERRO ao remover .py: {exc}")
            return False

        print(
            f"[BuildDistribution] OK — {rel_path} -> {dest_pyc.relative_to(self._root)} "
            f"({dest_pyc.stat().st_size // 1024} KB)"
        )
        return True

    def compile_modules(self, modules: Optional[dict] = None) -> Tuple[int, int]:
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

    def _package_source(self, modules: dict) -> bool:
        """
        Empacota os arquivos .py originais em um .dist de fonte (antes da compilação).
        Delega a criação do pacote para PackageManager.create_package().

        Returns:
            bool: True se OK.
        """
        dist_path = self._root / f"{SOURCE_DISTRIBUTION_FILENAME}.dist"
        print(
            f"[BuildDistribution] Empacotando distribuição de fonte (.py): {dist_path}"
        )

        # Prepara módulos como {diretorio_relativo: [arquivos.py]}
        # PackageManager.resolve os caminhos usando root_dir
        modules_prepared = {
            directory: [Path(f).name for f in files]
            for directory, files in modules.items()
        }

        return PackageManager.create_package(
            dist_path=dist_path,
            modules=modules_prepared,
            static_files=STATIC_FILES,
            root_dir=self._root,
            key=DISTRIBUTION_KEY,
            manifest_extra={"type": "source"},
        )

    def _package(self, modules: dict) -> bool:
        """
        Empacota os .pyc gerados em um arquivo .dist (formato ZIP).
        Delega a criação do pacote para PackageManager.create_package().

        Returns:
            bool: True se OK.
        """
        dist_path = self._root / f"{PYC_DISTRIBUTION_FILENAME}.dist"
        print(
            f"[BuildDistribution] Empacotando distribuição compilada (.pyc): {dist_path}"
        )

        # Prepara módulos com extensão .pyc
        modules_prepared = {
            directory: [Path(f).with_suffix(".pyc").name for f in files]
            for directory, files in modules.items()
        }

        ok = PackageManager.create_package(
            dist_path=dist_path,
            modules=modules_prepared,
            static_files=STATIC_FILES,
            root_dir=self._root,
            key=DISTRIBUTION_KEY,
        )

        if ok and DISTRIBUTION_KEY:
            print(f"[BuildDistribution] Chave incorporada: {DISTRIBUTION_KEY}")

        return ok

    def _update_version_files(self):
        """
        Atualiza a versão nos arquivos metadata.txt e AboutDialog.py
        com base no valor da constante VERSION definida neste script.
        """
        import re
        from datetime import date

        print(f"[BuildDistribution] Atualizando versão para {VERSION}...")

        # --- metadata.txt ---
        metadata_path = self._root / "metadata.txt"
        if metadata_path.exists():
            content = metadata_path.read_text(encoding="utf-8")
            # Substitui version=QUALQUER_COISA no metadata.txt
            new_content = re.sub(
                r'^version=.*$',
                f'version={VERSION}',
                content,
                count=1,
                flags=re.MULTILINE,
            )
            if new_content != content:
                metadata_path.write_text(new_content, encoding="utf-8")
                print(f"[BuildDistribution]   metadata.txt -> version={VERSION}")
            else:
                print(f"[BuildDistribution]   metadata.txt já está em version={VERSION}")
        else:
            print("[BuildDistribution]   AVISO: metadata.txt não encontrado.")

        # --- plugins/AboutDialog.py ---
        about_path = self._root / "plugins" / "AboutDialog.py"
        if about_path.exists():
            content = about_path.read_text(encoding="utf-8")

            # Substitui a versão no AboutDialog (ex: 2.0.7 -> 3.0.0)
            # A linha se parece com:  f"<b>{STR.VERSION}:</b> 2.0.7<br>"
            new_content = re.sub(
                r'(STR\.VERSION.*?</b>\s*)\d+\.\d+\.\d+',
                rf'\g<1>{VERSION}',
                content,
                count=1,
            )

            # Atualiza a data para a data atual
            today = date.today()
            date_str = f"{today.day:02d} / {today.month:02d} / {today.year}"
            new_content = re.sub(
                r'(STR\.UPDATED_ON.*?</b>\s*)\d+\s*/\s*\d+\s*/\s*\d+',
                r'\g<1>' + date_str,
                new_content,
                count=1,
            )

            if new_content != content:
                about_path.write_text(new_content, encoding="utf-8")
                print(f"[BuildDistribution]   AboutDialog.py -> version={VERSION}, updated={date_str}")
            else:
                print(f"[BuildDistribution]   AboutDialog.py já está atualizado.")
        else:
            print("[BuildDistribution]   AVISO: plugins/AboutDialog.py não encontrado.")

    def _remove_pycache(self):
        """
        Remove recursivamente todos os diretórios __pycache__ e todo o
        seu conteúdo a partir do diretório raiz do projeto.
        """
        print("[BuildDistribution] Removendo diretórios __pycache__...")
        removed = 0
        for pycache_dir in self._root.rglob("__pycache__"):
            if pycache_dir.is_dir():
                try:
                    # Remove todos os arquivos dentro do __pycache__
                    for item in pycache_dir.iterdir():
                        if item.is_dir():
                            # Remove subdiretórios recursivamente
                            for sub_item in item.rglob("*"):
                                if sub_item.is_file():
                                    sub_item.unlink()
                            item.rmdir()
                        else:
                            item.unlink()
                    # Remove o próprio diretório __pycache__
                    pycache_dir.rmdir()
                    print(
                        f"[BuildDistribution]   __pycache__ removido: "
                        f"{pycache_dir.relative_to(self._root)}"
                    )
                    removed += 1
                except OSError as exc:
                    print(
                        f"[BuildDistribution]   ERRO ao remover "
                        f"{pycache_dir.relative_to(self._root)}: {exc}"
                    )
        print(f"[BuildDistribution] {removed} diretório(s) __pycache__ removido(s).")

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
                        print(
                            f"[BuildDistribution]   .pyc removido: {directory}/{pyc_path.name}"
                        )
                        removed += 1
                    except OSError as exc:
                        print(f"[BuildDistribution]   ERRO ao remover .pyc: {exc}")
        print(f"[BuildDistribution] {removed} .pyc removido(s).")

    # ------------------------------------------------------------------
    # Empacotamento ZIP (.zip)
    # ------------------------------------------------------------------

    def _create_zip(self) -> bool:
        """
        Cria um arquivo ZIP com todos os arquivos e diretórios
        listados em ZIP_PACKAGES dentro de uma pasta "Cadmus/",
        excluindo os arquivos .dist e o próprio ZIP gerado anteriormente.

        Returns:
            bool: True se OK.
        """
        import zipfile

        zip_path = self._root / ZIP_FILENAME
        print(f"[BuildDistribution] Criando ZIP: {zip_path}")

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for item in ZIP_PACKAGES:
                    item_path = self._root / item
                    if not item_path.exists():
                        print(
                            f"[BuildDistribution]   AVISO: {item} não encontrado, ignorando."
                        )
                        continue

                    if item_path.is_dir():
                        # Adiciona diretório recursivamente dentro da pasta "Cadmus"
                        for file_path in item_path.rglob("*"):
                            if file_path.is_file():
                                # Pula arquivos .dist e o próprio .zip
                                if file_path.suffix in (".dist",) or file_path.name == ZIP_FILENAME:
                                    continue
                                # O caminho interno no ZIP começa com "Cadmus/"
                                arcname = Path("Cadmus") / file_path.relative_to(self._root)
                                zf.write(file_path, arcname)
                                print(
                                    f"[BuildDistribution]   ZIP adicionado: {arcname}"
                                )
                    else:
                        # Arquivo individual dentro da pasta "Cadmus"
                        arcname = Path("Cadmus") / item_path.relative_to(self._root)
                        zf.write(item_path, arcname)
                        print(
                            f"[BuildDistribution]   ZIP adicionado: {arcname}"
                        )

            size_mb = zip_path.stat().st_size / (1024 * 1024)
            print(
                f"[BuildDistribution] ZIP criado com sucesso: {zip_path.name} "
                f"({size_mb:.2f} MB) — conteúdo dentro de 'Cadmus/'"
            )
            return True

        except Exception as exc:
            print(f"[BuildDistribution] ERRO ao criar ZIP: {exc}")
            return False

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
            capture_output=True,
            text=True,
            timeout=60,
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
            print(
                f"[BuildDistribution] .pyc gerado: {dest_pyc.relative_to(self._root)} "
                f"({dest_pyc.stat().st_size // 1024} KB)"
            )
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
            print(
                f"[BuildDistribution] .pyc gerado: {dest_pyc.relative_to(self._root)} "
                f"({dest_pyc.stat().st_size // 1024} KB)"
            )
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
