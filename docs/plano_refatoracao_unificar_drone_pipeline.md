# Proposta de Refatoração: Unificação do Pipeline Drone (DronePipelineService)

## 1. Problema

Atualmente existem **3 classes** que implementam o mesmo pipeline de forma duplicada:

| Classe | Arquivo | Ativação | Responsabilidade |
|--------|---------|----------|------------------|
| `DroneCoordinates` | `plugins/DroneCoordinates.py` | Botão Executar na UI | UI completa + pipeline |
| ~~`DroneCoordinatesRunner`~~ | ~~`core/services/DroneCoordinatesRunner.py`~~ | ~~Chamado pelo MrkDropHandler~~ | ~~Pipeline headless~~ — **removido** |
| `MrkDropHandler` | `core/services/MrkDropHandler.py` | Drag-and-drop no QGIS | Wrapper QgsCustomDropHandler → delega para Runner |

### Código duplicado identificado

1. **Montagem dos steps do pipeline** (ocorre em DroneCoordinates.execute_tool() e DroneCoordinatesRunner.run_mrk_file())
2. **Callback `_on_pipeline_finished`** (ocorre em ambas as classes com lógica quase idêntica)
3. **Resolução de campos de ordenação/agrupamento** (`_resolve_track_order_field`, `_resolve_track_group_fields` — idênticos nas duas)
4. **Salvamento GPKG + aplicação de QML** (lógica duplicada nos callbacks)
5. **Carregamento de preferências** (cada classe faz seu próprio `prefs.get(...)` com defaults diferentes, o que já causou bugs)

---

## 2. Arquitetura Proposta

```
                    ┌─────────────────────────┐
                    │   DronePipelineService   │  ← NOVO: único ponto de entrada
                    │  (core/services/)        │
                    └──────────┬──────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                 ▼
      DroneCoordinates   DroneCoordinates    MrkDropHandler
      (UI)               Runner              (wizard)
              │                │                 │
              └────────────────┼─────────────────┘
                               ▼
                    ┌─────────────────────────┐
                    │   AsyncPipelineEngine   │  ← JÁ EXISTE
                    └─────────────────────────┘
```

### 2.1 `DronePipelineService` (NOVA)

Classe central que contém **toda a lógica de construção e execução do pipeline**:

```python
class DronePipelineService:
    """
    Serviço único do pipeline de drone.
    
    Responsabilidades:
      - Carregar preferências com defaults centralizados
      - Montar steps com parâmetros corretos
      - Definir callbacks on_success / on_error
      - Gerenciar pós-processamento (GPKG, QML, track layer, report)
    """

    DEFAULTS = {
        "photos": True,
        "use_mrk": True,
        "recursive": True,
        "generate_report": True,
        # ... todos os defaults em UM lugar
    }

    @staticmethod
    def execute(
        iface,
        input_path: str,
        file_path: Optional[str] = None,
        *,
        on_finished: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ) -> bool:
        """
        Constrói e inicia o pipeline a partir das preferências salvas.
        
        Args:
            iface: Interface QGIS
            input_path: Diretório base das fotos
            file_path: Caminho do arquivo MRK (opcional — None = modo UI)
            on_finished: Callback customizado (opcional)
            on_error: Callback customizado (opcional)
        
        Returns:
            True se o pipeline foi iniciado
        """
        pass

    @staticmethod
    def _on_pipeline_finished(
        iface,
        context: ExecutionContext,
        *,
        on_finished: Optional[Callable] = None,
    ):
        """
        Callback único de sucesso.
        - Cria layer de pontos
        - Salva GPKG (se configurado)
        - Aplica QML (se configurado)
        - Cria layer de traço
        - Salva GPKG do traço (se configurado)
        - Aplica QML do traço (se configurado)
        - Gera relatório (se configurado)
        - Notifica usuário
        
        Toda a lógica de pós-processamento vive AQUI.
        """
        pass
```

### 2.2 Simplificação das 3 classes existentes

#### `DroneCoordinates.py` (plugins)
```python
class DroneCordinates(BasePluginMTL):
    def execute_tool(self):
        # ... validações de UI ...
        # Apenas 1 linha de pipeline:
        DronePipelineService.execute(
            iface=self.iface,
            input_path=base_folder,
            paths=paths,
        )
```

#### `DroneCoordinatesRunner.py` (core/services)
```python
class DroneCoordinatesRunner:
    def run_mrk_file(self, file_path, *, on_finished=None, on_error=None):
        return DronePipelineService.execute(
            iface=self.iface,
            input_path=os.path.dirname(file_path),
            file_path=file_path,
            on_finished=on_finished,
            on_error=on_error,
        )
```

#### `MrkDropHandler.py` (core/services)
```python
class MrkDropHandler(QgsCustomDropHandler):
    def handleFileDrop(self, file):
        return DronePipelineService.execute(
            iface=self.iface,
            input_path=os.path.dirname(file),
            file_path=file,
        )
```

---

## 3. Benefícios

| Aspecto | Antes | Depois |
|---------|-------|--------|
| **Defaults** | 3 lugares com defaults diferentes | 1 centralizado em `DronePipelineService.DEFAULTS` |
| **Montagem de steps** | Duplicada em DroneCoordinates + Runner | Única em `DronePipelineService.execute()` |
| **Callback on_finished** | Duplicado em DroneCoordinates + Runner | Único em `DronePipelineService._on_pipeline_finished()` |
| **Resolução de track fields** | Duplicado em 2 classes | Métodos estáticos compartilhados |
| **Testabilidade** | Difícil (depende de UI ou drag) | Fácil (chama builder com parâmetros) |
| **Risco de bugs** | Alto (defaults divergentes já causaram erro) | Baixo (um ponto de verdade) |
| **Manutenção** | Modificar 3 arquivos para uma mudança | Modificar 1 arquivo |

---

## 4. Exemplo de Implementação

### 4.1 `DronePipelineService` (implementação completa)

```python
# core/services/DronePipelineService.py

class DronePipelineService:
    """
    Serviço único do pipeline de drone.
    
    Responsabilidades:
      - Carregar preferências com defaults centralizados
      - Montar steps com parâmetros corretos
      - Definir callbacks on_success / on_error
      - Gerenciar pós-processamento (GPKG, QML, track layer, report)
    """

    DEFAULTS = {
        "photos": True,
        "use_mrk": True,
        "recursive": True,
        "generate_report": True,
        "apply_style_points": False,
        "apply_style_track": False,
    }

    @staticmethod
    def _load_safe_prefs(tool_key: str) -> dict:
        """Carrega prefs e aplica defaults garantidos."""
        raw = load_tool_prefs(tool_key)
        result = dict(DronePipelineService.DEFAULTS)
        result.update(raw)
        return result

    @staticmethod
    def execute(
        iface,
        input_path: str,
        file_path: Optional[str] = None,
        *,
        paths: Optional[List[str]] = None,
        on_finished: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ) -> bool:
        tool_key = ToolKey.DRONE_COORDINATES
        prefs = DronePipelineService._load_safe_prefs(tool_key)

        # --- Carregar campos selecionados ---
        exif_selected = prefs.get("exif_fields_selected", [])
        xmp_selected = prefs.get("xmp_fields_selected", [])
        selected_required = MetadataFields.normalize_selected_keys(
            exif_selected + xmp_selected,
            allowed_keys=MetadataFields.required_keys(),
        )
        selected_custom = MetadataFields.normalize_selected_keys(
            prefs.get("custom_fields_selected", []),
            allowed_keys=MetadataFields.custom_keys(),
        )
        selected_mrk = MetadataFields.normalize_selected_keys(
            prefs.get("mrk_fields_selected", []),
            allowed_keys=MetadataFields.mrk_keys(),
        )

        use_mrk = prefs["use_mrk"]
        source = "mrk+photo" if use_mrk else "photo"
        enable_mrk = use_mrk
        apply_photos = prefs["photos"]

        # --- Montar ExecutionContext ---
        context = ExecutionContext(
            input_path=input_path,
            tool_key=tool_key,
            files=[file_path] if (enable_mrk and file_path) else (paths or []),
        )

        # --- Montar Steps ---
        enable_exif = apply_photos
        enable_xmp = apply_photos
        enable_custom = apply_photos and bool(selected_custom)

        resolve_paths = [file_path] if (enable_mrk and file_path) else (paths or [])
        
        steps = [
            PhotoEnrichmentStep(
                source=source,
                enable_mrk=enable_mrk,
                enable_exif=enable_exif,
                enable_xmp=enable_xmp,
                enable_custom_fields=enable_custom,
                selected_required_fields=selected_required,
                selected_custom_fields=selected_custom,
                selected_mrk_fields=selected_mrk,
                recursive=prefs["recursive"],
                paths=resolve_paths,
            ),
            JsonVectorizationStep(source=source),
        ]
        if prefs["generate_report"]:
            steps.append(ReportGenerationStep())

        # Dados extras para callback
        if file_path:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            context.set_result("points_layer_name", f"{base_name}_{STR.POINTS}")
            context.set_result("track_layer_name", f"{base_name}_{STR.TRACK}")
            context.set_result("auto_points_output_path",
                ExplorerUtils.build_suffixed_output_path(file_path, STR.POINTS.lower()))
            context.set_result("auto_track_output_path",
                ExplorerUtils.build_suffixed_output_path(file_path, STR.TRACK.lower()))
            context.set_result("source_mrk_file", file_path)

        # --- Callbacks ---
        def _on_finished(ctx: ExecutionContext):
            DronePipelineService._on_pipeline_finished(
                iface, ctx,
                on_finished=on_finished,
            )
        def _on_error(errors):
            if callable(on_error):
                on_error(errors)

        engine = AsyncPipelineEngine(
            steps=steps,
            context=context,
            on_finished=_on_finished,
            on_error=_on_error,
        )
        engine.start()
        return True

    @staticmethod
    def _on_pipeline_finished(
        iface,
        context: ExecutionContext,
        *,
        on_finished: Optional[Callable] = None,
    ):
        """Callback único de sucesso — todo pós-processamento aqui."""
        layer = context.get_result("layer") or context.get("layer")
        if not layer or not layer.isValid():
            QgisMessageUtil.modal_error(iface, STR.ERROR_LAYER_NOT_FOUND)
            return

        points_output_path = context.get_result("auto_points_output_path")
        track_output_path = context.get_result("auto_track_output_path")
        points_layer_name = context.get_result("points_layer_name", STR.POINTS)
        track_layer_name = context.get_result("track_layer_name", STR.TRACK)

        # --- Pontos: salvar + QML + adicionar ao projeto ---
        if points_output_path:
            points_layer = DronePipelineService._save_and_load(
                layer, points_output_path, fallback_name=points_layer_name,
                iface=iface,
            )
        else:
            points_layer = layer
            QgsProject.instance().addMapLayer(layer)

        DronePipelineService._apply_qml_if_configured(
            points_layer, "apply_style_points", "qml_path_points",
        )

        # --- Traço ---
        order_field = DronePipelineService._resolve_track_order_field(points_layer)
        group_fields = DronePipelineService._resolve_track_group_fields(points_layer)
        line_layer = VectorLayerGeometry.create_line_layer_from_points(
            list(points_layer.getFeatures()),
            order_by_field=order_field,
            name=track_layer_name,
            group_by_fields=group_fields,
            attribute_fields=MetadataFields.default_track_attribute_keys(),
        )

        if line_layer and line_layer.isValid():
            if track_output_path:
                track_layer = DronePipelineService._save_and_load(
                    line_layer, track_output_path, fallback_name=track_layer_name,
                    iface=iface,
                )
            else:
                track_layer = line_layer
                QgsProject.instance().addMapLayer(line_layer)

            DronePipelineService._apply_qml_if_configured(
                track_layer, "apply_style_track", "qml_path_track",
            )

        # --- Relatório ---
        json_path = context.json_path or context.get_result("json_path")
        if json_path and load_tool_prefs(ToolKey.DRONE_COORDINATES).get("generate_report", False):
            try:
                from .ReportGenerationService import ReportGenerationService
                report_payload = ReportGenerationService(
                    tool_key=ToolKey.DRONE_COORDINATES
                ).generate_from_json(json_path)
            except Exception as e:
                LogUtils(tool=ToolKey.DRONE_COORDINATES, class_name="DronePipelineService")\
                    .error(f"Falha ao gerar report: {e}")

        QgisMessageUtil.bar_success(iface, STR.SUCCESS_MESSAGE if not points_output_path
                                     else STR.CONVERT_FILE_SUCCESS)
        if callable(on_finished):
            on_finished({
                "file_path": context.get_result("source_mrk_file"),
                "points_layer": points_layer,
                "track_layer": track_layer if line_layer else None,
                "report_payload": report_payload if json_path else None,
            })

    @staticmethod
    def _save_and_load(layer, output_path, *, fallback_name, iface):
        """Salva layer em GPKG e carrega no projeto."""
        existing = VectorLayerSource.load_existing_vector_layer(
            output_path, tool_key=ToolKey.DRONE_COORDINATES
        )
        if existing:
            existing.setName(fallback_name)
            ProjectUtils.add_layer_if_missing(existing)
            return existing
        saved = VectorLayerSource.save_and_load_layer(
            layer, output_path,
            tool_key=ToolKey.DRONE_COORDINATES,
            decision="overwrite",
        )
        if saved and saved.isValid():
            saved.setName(fallback_name)
            ProjectUtils.add_layer_if_missing(saved)
            return saved
        layer.setName(fallback_name)
        ProjectUtils.add_layer_if_missing(layer)
        return layer

    @staticmethod
    def _apply_qml_if_configured(layer, enabled_key: str, path_key: str):
        """Aplica QML se configurado nas preferências."""
        if not layer or not layer.isValid():
            return
        prefs = load_tool_prefs(ToolKey.DRONE_COORDINATES)
        if not prefs.get(enabled_key, False):
            return
        qml_path = prefs.get(path_key, "").strip()
        if qml_path and os.path.exists(qml_path):
            ok = layer.loadNamedStyle(qml_path)
            if isinstance(ok, tuple):
                ok = ok[0]
            if ok:
                layer.triggerRepaint()

    @staticmethod
    def _resolve_track_order_field(layer):
        candidates = [
            "Foto", "foto", "PhotoNum",
            MetadataFields.resolve_output_name("Foto"),
            "mrk_index", "id",
        ]
        for name in candidates:
            if name and layer.fields().lookupField(name) != -1:
                return name
        return layer.fields().field(0).name()

    @staticmethod
    def _resolve_track_group_fields(layer):
        pairs = [
            ("MrkPath", "MrkFile"),
            ("mrk_path", "mrk_file"),
            (
                MetadataFields.resolve_output_name("MrkPath"),
                MetadataFields.resolve_output_name("MrkFile"),
            ),
        ]
        for a, b in pairs:
            if layer.fields().lookupField(a) != -1 and layer.fields().lookupField(b) != -1:
                return [a, b]
        fallback = ["FolderLevel1", "FolderL1",
                     MetadataFields.resolve_output_name("FolderLevel1")]
        for name in fallback:
            if name and layer.fields().lookupField(name) != -1:
                return [name]
        return None
```

### 4.2 `MrkDropHandler` simplificado

```python
# core/services/MrkDropHandler.py
class MrkDropHandler(QgsCustomDropHandler):
    PROVIDER_KEY = "cadmus_mrk"

    def __init__(self, iface):
        super().__init__()
        self.iface = iface

    def handleFileDrop(self, file):
        if not ExplorerUtils.has_extension(file, [".mrk"]):
            return False
        QgisMessageUtil.bar_info(self.iface, STR.MRK_DROP_START, duration=3)
        return DronePipelineService.execute(
            iface=self.iface,
            input_path=os.path.dirname(file),
            file_path=file,
        )

    def customUriProviderKey(self):
        return self.PROVIDER_KEY

    def handleCustomUriDrop(self, uri):
        if not uri:
            return False
        return self.handleFileDrop(uri.uri)
```

### 4.3 `DroneCoordinatesRunner` removido

`DroneCoordinatesRunner` deixa de existir — sua responsabilidade é absorvida pelo `DronePipelineService`. O `MrkDropHandler` chama o service diretamente.

### 4.4 `DroneCoordinates` plugin simplificado

```python
# plugins/DroneCoordinates.py (trecho relevante)
class DroneCordinates(BasePluginMTL):
    def execute_tool(self):
        # ... validações de UI (pastas, dependências etc.) ...
        
        paths = self.folder_selector.get_paths()
        if not paths:
            self.logger.error("Nenhum diretório selecionado", code="NO_SELECTION")
            return

        first_path = paths[0]
        base_folder = (
            os.path.dirname(first_path)
            if os.path.isfile(first_path)
            else first_path
        )

        DronePipelineService.execute(
            iface=self.iface,
            input_path=base_folder,
            paths=paths,
        )
```

---

## 5. Plano de Migração

### Fase 1 — Criar `DronePipelineService`
1. Criar `core/services/DronePipelineService.py`
2. Mover toda a lógica de `DroneCoordinates.execute_tool()` para lá
3. Mover toda a lógica de `DroneCoordinatesRunner.run_mrk_file()` para lá
4. Mover callbacks `_on_pipeline_finished` de ambas as classes

### Fase 2 — Simplificar classes existentes
1. `DroneCoordinates.execute_tool()` → chama `DronePipelineService.execute()`
2. `DroneCoordinatesRunner.run_mrk_file()` → chama `DronePipelineService.execute()`
3. `MrkDropHandler.handleFileDrop()` → chama `DronePipelineService.execute()`

### Fase 3 — Remover duplicação
1. Remover `_resolve_track_order_field` e `_resolve_track_group_fields` das 2 classes
2. Remover `_save_or_load_existing`, `_load_layer`, `_notify_error`
3. Opcional: Remover `DroneCoordinatesRunner` se ninguém mais o importar

### Fase 4 — Testes
1. Testar pipeline via UI (botão Executar)
2. Testar pipeline via drag-drop de .mrk
3. Testar com e sem MRK, com e sem fotos, recursivo e não recursivo
4. Validar GPKG, QML, relatório

---

## 6. Riscos e Considerações

| Risco | Mitigação |
|-------|-----------|
| Quebrar compatibilidade com código que importa DroneCoordinatesRunner | Manter classe como wrapper delegando para o Service (Fase 2) |
| Perder callbacks customizados do Runner | `DronePipelineService.execute()` aceita `on_finished`/`on_error` opcionais |
| Diferenças de comportamento entre UI e Runner | Centralizar `DEFAULTS` garante consistência |
| Acoplamento com Preferences | Service usa `_load_safe_prefs()` que sempre retorna defaults válidos |
