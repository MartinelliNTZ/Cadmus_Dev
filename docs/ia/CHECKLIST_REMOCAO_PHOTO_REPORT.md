# Checklist - Remocao da pasta `photo_report`

## Pre-condicoes
- [ ] Confirmar que `utils/report/*` esta em uso no runtime.
- [ ] Confirmar que `resources/reports/template.html` e `resources/reports/config.yaml` existem e estao validos.
- [ ] Confirmar que `core/services/ReportGenerationService.py` gera HTML com sucesso.

## Integracoes
- [ ] Confirmar chamada de report no `DroneCoordinates` (checkbox Generate Report).
- [ ] Confirmar chamada de report no `DroneCoordinatesRunner`.
- [ ] Confirmar funcionamento do plugin `ReportMetadataPlugin`.

## Vetorizacao sem MRK
- [ ] Confirmar geracao de camada por pasta de fotos.
- [ ] Confirmar JSON de diagnostico em `%TEMP%/cadmus/reports/json`.
- [ ] Confirmar HTML em `%TEMP%/cadmus/reports/html`.

## Limpeza final
- [ ] Remover pasta legada `photo_report`.
- [ ] Rodar validacao sintatica (`py_compile`) nos modulos afetados.
- [ ] Revisar changelog/todo antes de publicar.
