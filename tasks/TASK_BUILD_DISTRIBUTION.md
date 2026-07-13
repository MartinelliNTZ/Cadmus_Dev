# TASK: BuildDistribution - Sistema de Distribuição Ofuscada

## Visão Geral

Criar sistema de build e distribuição que:
1. **Build Script** — ofusca classes com PyArmor, empacota em `.cadmus_dist`, remove .py originais
2. **DistributionInstaller** — Desempacota `.cadmus_dist` nas pastas corretas, instala chave de licença
3. **RegistryDialog** — Botão para selecionar `.cadmus_dist` e executar instalação
4. **PathExtensionPlugin** — Bloqueado por licença

## Arquivos a Criar

### 1. `scripts/BuildDistribution.py`
Script de build que ofusca com PyArmor e empacota.

```python
"""
BuildDistribution — Script de Build e Distribuição Ofuscada
============================================================
Empacota módulos Python do Cadmus em distribuição ofuscada via PyArmor.

Uso:
    python scripts/BuildDistribution.py                    # Build padrão (PathExtensionPlugin)
    python scripts/BuildDistribution.py --all              # Todos os módulos configurados
    python scripts/BuildDistribution.py --key="CHAVE"     # Com chave de licença embutida
    python scripts/BuildDistribution.py --clean            # Remove artefatos
    python scripts/BuildDistribution.py --info             # Mostra configuração atual

Fluxo:
    1. Lê configuração dos módulos a ofuscar
    2. Para cada módulo: ofusca com PyArmor, gera .pyd
    3. Remove .py original após ofuscação bem-sucedida
    4. Empacota .pyd + metadados em .cadmus_dist
    5. Opcional: insere chave de licença no pacote
"""
```

### 2. `core/config/DistributionInstaller.py`
Classe que desempacota e instala a distribuição.

```python
class DistributionInstaller(BaseUtil):
    """
    Instalador de distribuição ofuscada Cadmus.
    
    Fluxo:
    1. Abre .cadmus_dist (ZIP)
    2. Lê metadata.json (versão, módulos, key opcional)
    3. Extrai arquivos .pyd para as pastas corretas
    4. Se contém key: salva via RegistryManager
    5. Valida instalação
    """
```

### 3. Modificação em `core/ui/RegistryDialog.py`
Adicionar:
- Botão "📦 Instalar Pacote" que abre QFileDialog para `.cadmus_dist`
- Chama DistributionInstaller.install()
- Feedback visual

### 4. Modificação em `plugins/PathExtensionPlugin.py`
Adicionar verificação de licença no `execute_tool()`.

## .cadmus_dist — Formato do Pacote

ZIP contendo:
```
metadata.json          # {"version": "1.0", "modules": [...], "key": "..."}
core/config/RegistryManager.pyd
core/config/ToolRegistry.pyd
plugins/PathExtensionPlugin.pyd
...
```

## Chave Padrão
`7N1V9-2S1H9-5G9K4`

## Dependências
- PyArmor (pip install pyarmor)
- Python padrão do QGIS