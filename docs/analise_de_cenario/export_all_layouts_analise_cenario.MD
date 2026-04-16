# Análise de Cenário – Export All Layouts

**Visão Geral**

Ferramenta para exportar todos os layouts do projeto em PDF e/ou PNG, com opções de união dos arquivos exportados e controle de substituição de arquivos existentes.

**Objetivo**

Automatizar a exportação em lote de layouts, suportando:
- exportação em PDF e/ou PNG;
- união de PDFs gerados em um único arquivo final;
- conversão/união de PNGs em PDF final;
- controle de sobrescrita de arquivos existentes;
- persistência de preferências do usuário.

**Fluxo resumido**

1. UI: usuário escolhe opções (PDF/PNG, merge, substituir) e pasta de saída.
2. Validação: confirma formatos selecionados e dependências (PyPDF2, Pillow).
3. Preparação: cria pasta de saída se necessário; calcula total de layouts.
4. Exportação: itera layouts via `QgsLayoutExporter`, gera arquivos PDF/PNG, atualiza diálogo de progresso.
5. Pós-processo: se solicitado, une PDFs (PyPDF2) e/ou converte/une PNGs (Pillow) em PDF final.
6. Registro: logs por layout/arquivo e resumo final mostrado ao usuário.

**Componentes principais**

- `ExportAllLayoutsDialog` (_plugins_): UI construída com `BasePluginMTL` + `WidgetFactory`.
- `WidgetFactory`: `create_checkbox_grid`, `create_input_fields_widget`, `create_path_selector`, `create_simple_button`, `create_bottom_action_buttons`.
- `PDFUtils`: lógica de união de PDFs/PNGs (usa PyPDF2/Pillow).
- `DependenciesManager`: checagem e instalação assistida de dependências.
- `ProgressDialog`: exibe progresso cancelável.

**Cenários de Uso (exemplos)**

- Exportar apenas PDF → gera um PDF por layout e opcionalmente une todos em um único PDF.
- Exportar PNG e unir em PDF final → gera PNGs, depois os converte/une em PDF com Pillow.
- Exportar ambos, sem substituir existentes → adiciona sufixos à saída para evitar sobrescrita.

**Riscos e controles**

- Dependências ausentes: validação antes de executar e instalação assistida; exige reinício do QGIS após instalação.
- Espaço em disco e permissões: criar pasta de saída pode falhar; logar e avisar usuário.
- Erro em exportação de layout específico: capturar exceção, logar e continuar com próximos layouts.
- Performance: layouts grandes podem demorar; ProgressDialog e possibilidade de cancelar.

**Observações de implementação**

- Preferir gravar logs detalhados por layout (nome, formato, destino, status).
- `max_width` para PNGs deve ser validado como int > 0.
- `WidgetFactory` deve ser usado para construir UI consistente (manter retorno `(layout, widget)` onde aplicável).

**Evoluções recomendadas**

- Modo `dry-run` que apenas lista arquivos que seriam gerados.
- Preview de tamanhos/estimativas de disco.
- Opção para escolher nomes customizados por layout via máscara.
