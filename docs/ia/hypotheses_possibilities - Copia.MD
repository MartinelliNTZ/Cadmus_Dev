# Hipóteses para cursor de resize persistente

Este arquivo reúne as 5 hipóteses analisadas na conversa e registra que a hipótese 5 foi implementada (instrumentação + logs).

1) Mapeamento de coordenadas (local vs global)
- Causa: eventos propagados pelo ScrollWidget chegam ao MainLayout com posições locais relativas ao ScrollWidget, não ao diálogo.
- Solução: mapear `event.globalPos()` para coordenadas do diálogo antes de repassar.
- Impacto: Baixo; corrige casos onde _get_resize_edge usa coordenadas do diálogo.

2) Falta de tratamento de leaveEvent/reset de cursor
- Causa: ausência de `leaveEvent`/reset quando ponteiro sai do diálogo ou do widget; cursor pode ficar preso.
- Solução: implementar `leaveEvent` em widgets relevantes e resetar cursor; garantir `mouseTracking=True`.
- Impacto: Baixo-médio; cobre casos em que o cursor não é restaurado.

3) ScrollWidget propaga eventos sem tradução
- Causa: ScrollWidget chamando `parent().mouseMoveEvent(event)` sem mapear posições.
- Solução: traduzir as coordenadas antes de repassar (mapFromGlobal) — similar à hipótese 1.
- Impacto: Baixo; melhora confiabilidade ao usar scroll.

4) Reparenting / ciclo de vida dos widgets
- Causa: reparentings frequentes podem deixar handlers obsoletos ou corromper estado de cursor.
- Solução: reduzir reparentings (usar add_items de forma consistente) ou garantir rebind de handlers.
- Impacto: Médio; exige revisão de como add_items/WidgetFactory reparenta widgets.

5) Z-order / SizeGrip / handlers mais invasivos (IMPLEMENTADO)
- Causa: elementos de resize nativos (SizeGrip) ou widgets em z-order incorreto podem interceptar eventos ou manter cursor.
- Solução aplicada: traduzir eventos do `ScrollWidget` para coordenadas do diálogo antes de repassar; adicionar logs extensivos em `ScrollWidget` e `MainLayout` para capturar `pos`, `globalPos`, `mapped_to_parent`, `resize_edge`, `resize_active` e mudanças de dimensão.
- Impacto: Médio; alteração localizada e reversível. Fornece dados de diagnóstico completos para validar comportamento.


Observação: Os logs gerados estão sendo enviados para o arquivo de log padrão do plugin via `LogUtils`. Testes manuais no QGIS são necessários para validar visualmente o comportamento após a instrumentação.
