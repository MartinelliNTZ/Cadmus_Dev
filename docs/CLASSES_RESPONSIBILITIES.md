# Mapa de Responsabilidades - Módulo `utils/report`

## Visão Geral da Arquitetura

O módulo de relatório segue o princípio da **responsabilidade única** e do **orquestrador que delega, não executa**.

```
                    ┌─────────────────────────────────────┐
                    │      ReportPapelineManager          │
                    │       (Orquestrador puro)            │
                    │   "O chefe não trabalha, ele manda"  │
                    └──────┬────────┬────────┬────────────┘
                           │        │        │
              ┌────────────┘        │        └────────────┐
              ▼                     ▼                     ▼
    ┌───────────────┐    ┌──────────────────┐   ┌─────────────────┐
    │JsonMetadata   │    │ FlightAggregator │   │  AlertManager   │
    │   Manager     │    │   (Voos)         │   │ (Qualidade)     │
    │ (Estatístico) │    └──────────────────┘   └─────────────────┘
    └───────────────┘                                   │
                                                        │
                                              ┌─────────┴──────────┐
                                              ▼                    ▼
                                   ┌─────────────────┐  ┌─────────────────┐
                                   │ AggregateAnalyzer│  │ RangeMetadata   │
                                   │  (Info. Gerais)  │  │   Manager       │
                                   └─────────────────┘  │   (Ranges)      │
                                                        └─────────────────┘
```

## Responsabilidades por Classe

### 1. `JsonMetadataManager` - **O Estatístico**
> "Me dê os dados brutos que eu filtro e trago as distribuições"

**O que faz:**
- Carrega JSON do disco (v2.0)
- Calcula estatísticas PURAS sobre indicadores das imagens
- Gera distribuições por nível (1..5) de cada indicador
- Calcula PQI (Photogrammetry Quality Index)
- Gera séries temporais (`_series_by_time`)
- Gera catálogo de indicadores com labels e descrições

**O que NÃO faz:**
- ❌ Não sabe nada sobre voos, equipamentos, gráficos
- ❌ Não gera alertas
- ❌ Não analisa qualidade - só calcula estatísticas
- ❌ Não sabe o que é um threshold - recebe configuração pronta

---

### 2. `FlightAggregator` - **O Agregador de Voos**
> "Quais são os voos? Como eles estão?"

**O que faz:**
- Agrupa imagens por `flight_id`
- Calcula métricas operacionais por voo (velocidade, duração, área, temperatura, LRF)
- Gera séries temporais por voo para gráficos (temperatura, LRF)
- Calcula médias por hora do dia

**Método principal:** `FlightAggregator.aggregate(results)` (agora @staticmethod)

**O que NÃO faz:**
- ❌ Não sabe nada sobre thresholds, níveis, indicadores, alertas
- ❌ Não analisa qualidade das imagens
- ❌ Não calcula estatísticas de indicadores
- ❌ Não tem estado de instância - todas as operações são estáticas

---

### 3. `AlertManager` - **O Analista de Qualidade**
> "Pergunte pra ele: esses dados estão bons?"

**O que faz:**
- Gera alertas de qualidade (CRITICO, ALERTA, INFO) para:
  - Dewarp desabilitado
  - Altitude incompleta
  - Motion Blur elevado
  - Gimbal desalinhado
  - Sinal RTK não-fixo
  - Variação de GSD
  - Overlap insuficiente
  - Yaw inconsistente
  - RTK STD (qualidade posicional)
  - RTK Effective Precision degradada
  - Temperatura do sensor elevada
- **Calcula métricas avançadas** (`compute_advanced_metrics`): RTK, Gimbal, Yaw, Overlap, Blur, Velocidade, Consistência de luz
- **Analisa strips** (`compute_strip_analysis`): agrupa por StripID e identifica faixas problemáticas
- **Analisa tendências temporais** (`compute_quality_trends`): PQI por quartil, manhã vs meio-dia
- **Classifica estabilidade RTK** (`compute_rtk_classification`)
- **Gera recomendações operacionais** (`compute_recommendations`): baseadas nas métricas
- Converte AlertRecord para dict serializável
- Gera sumário por categoria

**O que NÃO faz:**
- ❌ Não carrega dados do disco
- ❌ Não agrupa voos
- ❌ Não extrai informações gerais (equipamentos, firmware, GPS)
- ❌ Não renderiza HTML

---

### 4. `AggregateAnalyzer` - **O Analisador de Informações Gerais**
> "Tudo que faltou: informações brutas do conjunto"

**O que faz:**
- Extrai informações de equipamentos (modelos, números de série)
- Extrai versões de firmware
- Extrai datum GPS e status GPS
- Calcula intervalo de datas de captura
- Calcula top models por prefixo do filename
- Encontra último shutter count por câmera
- Analisa fontes de luz (classificação textual e por código)
- Calcula área total estimada (soma das áreas dos voos)

**O que NÃO faz:**
- ❌ Não gera alertas
- ❌ Não analisa qualidade
- ❌ Não agrupa voos
- ❌ Não calcula estatísticas de indicadores

---

### 5. `RangeMetadataManager` - **O Fornecedor de Ranges**
> "Qual o range para este dado?"

**O que faz:**
- Carrega configuração de thresholds do YAML
- Fornece thresholds por indicador
- Classifica valores em níveis (1..5) conforme regra configurada
- Singleton compartilhado por todas as classes

**O que NÃO faz:**
- ❌ Não analisa dados
- ❌ Não gera alertas
- ❌ Não sabe o que é um voo ou equipamento

---

### 6. `RenderEngine` - **O Renderizador Burro**
> "Só exibe, não analisa nada"

**O que faz:**
- Renderiza HTML via template Jinja2
- Gera dados de gráficos Chart.js a partir do agg
- Gera snippet Leaflet para mapa interativo
- Decide visibilidade de colunas na tabela de voos
- Salva HTML no disco

**O que NÃO faz:**
- ❌ Não analisa qualidade
- ❌ Não calcula métricas
- ❌ Não gera alertas
- ❌ Não sabe o que significam os dados que exibe

---

### 7. `ReportPapelineManager` - **O Orquestrador Chefe**
> "Manda os outros fazerem, não trabalha"

**O que faz:**
- Chama `JsonMetadataManager.compute_indicator_statistics()`
- Chama `FlightAggregator.aggregate()`
- Chama `AggregateAnalyzer.compute_general_info()`, `compute_top_models()`, `compute_shutter_per_camera()`, `compute_light_source_analysis()`, `compute_total_area()`
- Chama `AlertManager.compute_advanced_metrics()`, `compute_strip_analysis()`, `compute_quality_trends()`, `compute_rtk_classification()`, `compute_recommendations()`
- Chama `AlertManager.analyze()` para gerar alertas
- Monta o dict `agg` no formato esperado pelo template
- Mantém métodos auxiliares de status operacional (`_compute_dewarp_status`, `_compute_altitude_status`) pois combinam dados brutos com dados agregados

**O que NÃO faz:**
- ❌ Não calcula estatísticas (delega ao JsonMetadataManager)
- ❌ Não agrupa voos (delega ao FlightAggregator)
- ❌ Não analisa qualidade (delega ao AlertManager)
- ❌ Não extrai informações gerais (delega ao AggregateAnalyzer)
- ❌ Não renderiza HTML (delega ao RenderEngine)

---

## Mapa de Perguntas/Responsabilidades

| Pergunta | Quem Responde |
|----------|---------------|
| Qual a média e desvio do GSD? | `JsonMetadataManager` |
| Qual o nível médio de cada indicador? | `JsonMetadataManager` |
| Qual o PQI geral do bloco? | `JsonMetadataManager` |
| Quantas imagens estão em cada nível? | `JsonMetadataManager` |
| Quanto tempo durou o voo F001? | `FlightAggregator` |
| Qual a velocidade média do voo? | `FlightAggregator` |
| A temperatura subiu ao longo do voo? | `FlightAggregator` |
| Tem dewarp desabilitado? | `AlertManager` |
| Tem motion blur? | `AlertManager` |
| O gimbal está desalinhado? | `AlertManager` |
| O sinal RTK está bom? | `AlertManager` |
| O overlap é suficiente? | `AlertManager` |
| Quais faixas estão problemáticas? | `AlertManager` |
| A qualidade está caindo ao longo do voo? | `AlertManager` |
| Que recomendações operacionais fazer? | `AlertManager` |
| Quais equipamentos foram usados? | `AggregateAnalyzer` |
| Qual firmware estava rodando? | `AggregateAnalyzer` |
| Qual o intervalo de datas? | `AggregateAnalyzer` |
| Qual a fonte de luz predominante? | `AggregateAnalyzer` |
| Qual a área total estimada? | `AggregateAnalyzer` |
| Qual o range para este indicador? | `RangeMetadataManager` |
| Renderiza o HTML final | `RenderEngine` |
| Coordena tudo | `ReportPapelineManager` |

---

## Fluxo de Chamadas (Ordem no `analyze`)

```
1. JsonMetadataManager.compute_indicator_statistics()
2. FlightAggregator.aggregate()
3. AggregateAnalyzer.compute_general_info()
4. AggregateAnalyzer.compute_top_models()
5. AggregateAnalyzer.compute_shutter_per_camera()
6. AggregateAnalyzer.compute_light_source_analysis()
7. AggregateAnalyzer.compute_total_area()
8. ReportPapelineManager._compute_dewarp_status()
9. ReportPapelineManager._compute_altitude_status()
10. AlertManager.compute_advanced_metrics()
11. AlertManager.compute_rtk_classification()
12. AlertManager.compute_quality_trends()
13. AlertManager.compute_strip_analysis()
14. AlertManager.compute_recommendations()
15. AlertManager.analyze()