# Plano de Ação: Eliminação de Gargalos na Pipeline Drone Coordinates

**Versão:** 1.0.0  
**Data:** 2026-07-29  
**Baseado na análise do log:** `cadmus_20260728_130802_pid607616.log`

---

## Resumo Executivo

A pipeline atual processa **24.626 fotos em ~1h36min** (modo completo) e **81.444 fotos em ~23min** (modo básico). 
Os gargalos principais estão no I/O sequencial de arquivos (EXIF/XMP) e na renderização duplicada/triplicada do relatório HTML.

**Meta de melhoria:** Reduzir tempo de pipeline de ~1h36min para **~15-20min** (modo completo).

---

## Gargalo #1 (CRÍTICO): Extração XMP sequencial — ~35 minutos

### Diagnóstico
`XmpUtil._extract_xmp_text_raw()` lê cada arquivo JPG **inteiro** em memória via `fh.read().decode("latin1")` para localizar o bloco XMP. Para 24.626 fotos de ~20MB cada, isso representa **~500 GB de I/O sequencial**.

O bloco XMP nos JPGs DJI está nos **últimos ~4KB** do arquivo (footer após o segmento APP1). Lê-lo completamente é extremamente ineficiente.

### Solução Proposta

**1a. Leitura otimizada com seek (ALTA PRIORIDADE)**
```python
@staticmethod
def _extract_xmp_text_raw(image_path: str) -> str:
    """Lê APENAS os últimos 64KB do arquivo para encontrar o bloco XMP."""
    with open(image_path, "rb") as fh:
        # Arquivos DJI têm XMP nos últimos ~4KB
        fh.seek(0, 2)  # Vai para o final
        file_size = fh.tell()
        read_size = min(file_size, 65536)  # Lê no máximo 64KB do final
        fh.seek(file_size - read_size)
        raw = fh.read().decode("latin1", errors="ignore")
    
    start = raw.find("<x:xmpmeta")
    if start == -1:
        return ""
    end = raw.find("</x:xmpmeta>", start)
    if end == -1:
        return ""
    end += len("</x:xmpmeta>")
    return raw[start:end]
```

**Ganho estimado:** Redução de ~35min para **~3-5min** (redução de I/O de 500GB para ~1.5GB).

**1b. Cache de metadados em banco SQLite (MÉDIA PRIORIDADE)**
```python
# utils/mrk/MetadataCache.py
class MetadataCache:
    """Cache SQLite de metadados EXIF/XMP para evitar re-extração."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def get(self, image_path: str, mtime: float) -> dict | None:
        """Retorna metadados cacheados se o arquivo não mudou."""
        ...
    
    def set(self, image_path: str, mtime: float, metadata: dict):
        """Armazena metadados no cache."""
        ...
```

**Ganho estimado:** Evita re-extração completa em re-execuções (-35min na 2ª vez).

---

## Gargalo #2 (ALTO): Extração EXIF abre arquivo 3x — ~12 minutos

### Diagnóstico
`_enrich_exif()` chama sequencialmente:
1. `ExifUtil.extract_metadata_exif(image_path)` → abre JPG + parse EXIF
2. `ExifUtil.extract_metadata_os(image_path)` → apenas stat (OK)
3. `ExifUtil.extract_metadata_image(image_path)` → abre JPG + PIL Image

As chamadas 1 e 3 abrem o mesmo arquivo JPG duas vezes.

### Solução Proposta

**Unificar em uma única chamada `extract_all_metadata(image_path)`:**
```python
@staticmethod
def extract_all_metadata(image_path: str, tool_key: str = "") -> dict:
    """Extrai metadados EXIF/OS/Image em uma única abertura do arquivo."""
    data = {}
    try:
        stat = os.stat(image_path)
        data["File"] = os.path.basename(image_path)
        data["Path"] = image_path
        data["SizeMb"] = round(stat.st_size / (1024 * 1024), 2)
        data["DateTime"] = datetime.fromtimestamp(stat.st_ctime).strftime(...)
        
        with Image.open(image_path) as img:
            data["ExifImageWidth"], data["ExifImageHeight"] = img.size
            data["Format"] = f"{img.format}_{img.mode}"
            dpi = img.info.get("dpi")
            if dpi:
                data["DPIWidth"] = dpi_x
            
            exif_raw = img._getexif() or {}
            exif = {ExifTags.TAGS.get(k, k): v for k, v in exif_raw.items()}
            # ... resto do parsing EXIF
    except Exception as exc:
        logger.warning(f"Erro ao extrair metadados de {image_path}: {exc}")
    return data
```

**Ganho estimado:** Redução de ~12min para **~6-7min**.

---

## Gargalo #3 (CRÍTICO): Relatório HTML renderizado 3x — ~31 minutos

### Diagnóstico
O `ReportGenerationService.generate_from_json()`:
1. **1ª renderização**: sem `report_end` no JSON → salva HTML
2. Salva `report_end` no JSON + **re-renderiza** com report_end
3. **3ª renderização**: executada pela `DronePipelineService._on_pipeline_finished` (outra instância do ReportGenerationService)

Cada renderização recria 24.626 objetos `IMGMetadata`, reclassifica, gera gráficos e renderiza template Jinja2.

### Solução Proposta

**3a. Renderização única com placeholder (ALTA PRIORIDADE)**
```python
def generate_from_json(self, json_path, html_output_path=None):
    """Renderiza UMA ÚNICA vez, com placeholder para report_end."""
    report_start = datetime.now().isoformat()
    
    # Carrega timestamps existentes + report_start
    timestamps = JsonMetadataManager.load_timestamps(...)
    timestamps["report_start"] = report_start
    timestamps["report_end"] = ""  # Placeholder
    
    # ... carrega records, cria IMGMetadata, analisa (1x)
    records = JsonMetadataManager.load_records(...)
    results = [IMGMetadata(r).score() for r in records]
    
    # Renderiza UMA vez
    engine = RenderEngine(tool_key=self.tool_key)
    agg = ReportPapelineManager.analyze(results)
    charts = engine.generate_charts(agg)
    map_data = engine.generate_map_data(results)
    html = engine.render_report(results, agg, charts, map_data)
    engine.save_report(html, target_path)
    
    # Atualiza JSON com timestamps (sem re-renderizar)
    report_end = datetime.now().isoformat()
    JsonUtil.update_timestamps(json_path, {
        "report_start": report_start,
        "report_end": report_end,
    })
    
    return {"json_path": json_path, "html_path": target_path, ...}
```

**Ganho estimado:** Redução de ~31min para **~10-13min** (2 das 3 renderizações eliminadas).

**3b. Cache de IMGMetadata entre execuções (MÉDIA PRIORIDADE)**
Como o JSON não muda entre as renderizações, os objetos `IMGMetadata` e a análise `ReportPapelineManager.analyze()` podem ser cacheados.

**3c. Icones e logos pré-convertidos (BAIXA PRIORIDADE)**
```python
class ImageUtils:
    _base64_cache: Dict[str, str] = {}
    
    @staticmethod
    def photo_to_base64(path):
        if path not in ImageUtils._base64_cache:
            ImageUtils._base64_cache[path] = ...  # converte uma vez
        return ImageUtils._base64_cache[path]
```

---

## Gargalo #4 (ALTO): CustomPhotosFieldsUtil sequencial — ~20 minutos

### Diagnóstico
O `_calculate_custom_fields()` agrupa por `FolderLevel1` e processa cada grupo em lotes. A função `is_valid_sequence()` e `_calculate_sequence_fields()` são chamadas para cada foto, validando contra a anterior (O(n)).

### Solução Proposta

**4a. Processamento paralelo dos grupos (ALTA PRIORIDADE)**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

@staticmethod
def _calculate_custom_fields(all_records, tool_key, logger):
    grouped = _group_by_folder(all_records)
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_process_group, group_key, group, tool_key): group_key
            for group_key, group in grouped.items()
        }
        for future in as_completed(futures):
            group_key = futures[future]
            try:
                enriched = future.result()
                # mescla nos records
            except Exception as e:
                logger.warning(f"Falha no grupo {group_key}: {e}")
    
    return all_records
```

**Ganho estimado:** Redução de ~20min para **~6-8min** (4x paralelismo em CPU-bound).

**4b. Virtualização do cálculo de sequência (BAIXA PRIORIDADE)**
Em vez de calcular `prev_time_since`, `prev_geodesic_distance`, etc. para cada foto individualmente, pré-calcular arrays NumPy com todas as posições/alturas e aplicar broadcast.

---



---

## Gargalo #5 (MÉDIO): PipelineTask com busy-wait — consumo de CPU

### Diagnóstico
```python
class PipelineTask(QgsTask):
    def run(self):
        while not self._done:
            if self.isCanceled():
                return False
            QgsApplication.processEvents()
        return True
```

Este loop consome CPU continuamente, competindo com o processamento real das tasks.

### Solução Proposta

```python
class PipelineTask(QgsTask):
    def run(self):
        import time
        while not self._done:
            if self.isCanceled():
                return False
            QgsApplication.processEvents()
            time.sleep(0.01)  # 10ms sleep reduz CPU de 100% para ~5%
        return True
```

**Ganho estimado:** Libera CPU para as tasks reais, melhora responsividade geral.

---

## Gargalo #6 (CRÍTICO): Progresso sem granularidade — UI "travada"

### Diagnóstico
`_set_global_progress()` calcula progresso como fração do step atual sobre total de steps. Como cada step (EXIF: 12min, XMP: 35min) não reporta progresso intermediário, a barra fica em:
- 0% por **~35min** (durante todo o XMP)
- 33% por **~12min** (durante todo o EXIF)
- 50% por **~20min** (durante campos custom)

### Solução Proposta

**7a. PhotoEnrichmentTask com progresso incremental (ALTA PRIORIDADE)**
```python
class PhotoEnrichmentTask(BaseTask):
    def _run(self) -> bool:
        total_files = len(skeleton)
        processed = 0
        
        # Etapa EXIF
        for filename, record in skeleton.items():
            if self.isCanceled():
                return False
            # ... processa EXIF ...
            processed += 1
            self.setProgress(int(processed / total_files * 100))
        
        # Etapa XMP (mesmo padrão)
        ...
```

**7b. Progresso estimado com mensagem na barra (MÉDIA PRIORIDADE)**
```python
# Em PhotoEnrichmentTask
self.setProgress(50)  # "Enriquecendo MRK..."
# ...avisa ao usuário o que está acontecendo via QgisMessageUtil
```

**Ganho:** Usuário vê progresso **a cada 1-2s** durante as etapas mais longas.

---

## Plano de Implementação

### Fase 1 — Quick Wins (Dia 1)
| # | Tarefa | Esforço | Ganho |
|---|--------|---------|-------|
| 5 | Adicionar `time.sleep(0.01)` no PipelineTask | 5 min | Libera CPU |
| 3a | Renderização única do relatório HTML | 1h | -18min |
| 3c | Cache de base64 para ícones/logos | 30min | -30s por render |

### Fase 2 — Otimizações de I/O (Dia 2-3)
| # | Tarefa | Esforço | Ganho |
|---|--------|---------|-------|
| 1a | Leitura otimizada XMP com seek (últimos 64KB) | 30min | -30min |
| 2 | Unificar extração EXIF (3 em 1) | 1h | -5min |
| 4a | Paralelizar campos custom com ThreadPool | 2h | -12min |

### Fase 3 — Experiência do Usuário (Dia 3-4)
| # | Tarefa | Esforço | Ganho |
|---|--------|---------|-------|
| 7a | Progresso incremental nas tasks | 2h | UI responsiva |
| 1b | Cache SQLite de metadados | 4h | -35min em re-execuções |
| 4b | Virtualização NumPy de sequências | 3h | -5min (marginal) |

### Fase 4 — Consolidar (Dia 5)
| # | Tarefa | Esforço | Ganho |
|---|--------|---------|-------|
| - | Testes de regressão | 2h | Confiabilidade |
| - | Atualizar SKILL_METADATA_PIPELINE.md | 30min | Documentação |
| - | Atualizar changelog | 15min | Rastreabilidade |

---

## Estimativa de Ganhos

| Cenário | Antes | Depois | Redução |
|---------|-------|--------|---------|
| **24.626 fotos (completo)** | ~1h36min | **~15-20min** | **~80%** |
| **81.444 fotos (básico)** | ~23min | **~8-12min** | **~50%** |
| **Re-execução (com cache)** | ~1h36min | **~2-3min** | **~97%** |

---

## Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| ThreadPoolExecutor conflita com QGIS main thread | Baixa | Usar apenas em tasks (threads worker) |
| Cache SQLite corrompe em cancelamento | Média | Transações atômicas + WAL mode |
| Progresso incremental aumenta overhead | Baixa | Atualizar a cada 50 fotos, não 1 a 1 |
| RenderEngine espera report_end no template | Média | Template deve mostrar "" ou "em andamento" |

---

## Changelog

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-07-29 | 1.0.0 | Criação inicial do plano de ação baseado em análise de log |