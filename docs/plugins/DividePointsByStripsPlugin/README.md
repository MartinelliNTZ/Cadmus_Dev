# DividePointsByStripsPlugin

## Diagrama de Fluxo

```mermaid
flowchart TD
    A[Usuário abre plugin] --> B[UI construída via WidgetFactory]
    B --> C[Usuário seleciona camada e parâmetros]
    C --> D[Executa processamento]
    D --> E{Valida entradas}
    E -- Inválido --> F[Mensagem de erro via QgisMessageUtil]
    E -- Válido --> G[Chama SequentialPointBreakJudge]
    G --> H[Segmenta pontos em tiros/faixas]
    H --> I[Cria camada de resultado]
    I --> J{Salvar camada?}
    J -- Não --> K[Adiciona camada ao projeto]
    J -- Sim --> L[Filtra campos e salva camada]
    L --> K
    K --> M[Exibe mensagem de sucesso]
    F --> N[Fim]
    M --> N
```

## Fluxo Resumido

1. Usuário abre o plugin pelo menu ou atalho.
2. Interface é construída dinamicamente via WidgetFactory.
3. Usuário seleciona camada de pontos, campos e parâmetros.
4. Ao executar:
   - Valida entradas obrigatórias.
   - Se inválido, exibe mensagem de erro.
   - Se válido, chama SequentialPointBreakJudge para segmentação.
   - Cria camada de resultado.
   - Se opção de salvar estiver marcada, filtra campos e salva camada.
   - Adiciona camada ao projeto.
   - Exibe mensagem de sucesso com resumo.

## Integrações
- UI: WidgetFactory
- Persistência: Preferences
- Processamento: SequentialPointBreakJudge
- Mensagens: QgisMessageUtil
- Manipulação de camadas: VectorLayerSource, ProjectUtils

---

> Documentação gerada automaticamente em 17/04/2026.
