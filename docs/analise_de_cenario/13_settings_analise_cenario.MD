# Análise de Cenário – Configurações Cadmus

**Visão Geral**

O plugin de Configurações centraliza preferências globais do Cadmus, permitindo ao usuário definir método de cálculo vetorial (Elipsoidal, Cartesiana, Ambos), precisão de campos geométricos em casas decimais e limiar de processamento assíncrono em MB. Preferências são persistidas em arquivos JSON na pasta de preferências do usuário e carregadas automaticamente ao iniciar ferramentas dependentes. Interface intuitiva com rádio buttons em grid (3 colunas), spinbox para precisão (0-10) e limiar (MB).

**Objetivo**

Centralizar configurações em um único ponto de acesso, eliminando necessidade de reconfigurar em cada ferramenta. Permitir ajuste fino de performance (limiar assíncrono) e qualidade de resultado (precisão). Fornecer acesso direto à pasta de preferências para debug/backup de configurações.

**Fluxo resumido**

- Entrada: usuário acessa Menu → Cadmus → Configurações Cadmus.
- Carregamento: `_load_prefs()` carrega preferências salvas via `load_tool_prefs(ToolKey.SETTINGS)`.
- Renderização: `_build_ui()` constrói interface com 3 seções:
  1. Link para Pasta de Preferências (abre via `QDesktopServices.openUrl()`).
  2. Rádio buttons para Método de Cálculo (Elipsoidal, Cartesiana, Ambos).
  3. Spinbox para Precisão (0-10 casas decimais, padrão 2).
  4. Spinbox para Limiar Assíncrono (MB, padrão 20 MB = 20971520 bytes).
- Salvamento: ao clicar "Salvar", `_save_prefs()` converte valores e persiste em JSON via `save_tool_prefs()`.
- Propagação: preferências carregadas por plugins dependentes via `BasePluginMTL.settings_preferences` dict.
- Fechamento: diálogo fecha com confirmação "Configurações Salvas".

**Cenários de Uso (exemplos)**

- Usuário prefere Cartesiana para análises locais em UTM: seleciona "Cartesiana", salva (padrão muda globalmente).
- Camadas gigantes (100k+ feições) travando: usuário reduz "Limiar assíncrono" de 20 MB para 5 MB, forçando async mais cedo.
- Resultado com muitas casas decimais: aumenta "Precisão" de 2 para 4 (ex: 10.4532 m em vez de 10.45 m).
- Backup de configurações: usuário abre Pasta de Preferências e copia `settings.json` para pendrive antes de atualização de QGIS.
- Problema de sincronização: usuário deleta `settings.json` e recarrega plugin (volta ao padrão).

**Tipos de preferências armazenadas**

- `calculation_method`: string (Elipsoidal | Cartesiana | Ambos), padrão Elipsoidal.
- `vector_field_precision`: int (0-10), padrão 2.
- `async_threshold_features`: int (feições), padrão 1000.

**Impactos nos dados**

- Preservado: dados do projeto, camadas existentes, histórico do QGIS.
- Alterado: arquivo JSON de preferências (`prefs/settings.json`), em memória `settings_preferences` dict no plugin.
- Não alterado: layers, atributos, geometrias (configurações apenas afetam comportamento futuro de ferramentas).

**Riscos e controles**

- Preferências corrompidas: se JSON inválido, `load_tool_prefs()` retorna dict vazio; usuário clica "Salvar" e recupera padrões.
- Pasta de preferências não existe: erro ao abrir; validação via `os.path.exists(PREF_FOLDER)` com fallback a aviso QMessageBox.
- Tipo de dado inválido no JSON: conversão pode falhar; `try/except` em `_load_prefs()` com fallback a valor padrão.
- Precisão fora do range (0-10): spinbox com `minimum=0, maximum=10` impede entrada inválida.
- Limiar assíncrono muito alto: usuário pode definir > 1 TB (máximo=1024*1024 MB); não há validação, pode causar comportamento inesperado.
- Concorrência: múltiplas instâncias do QGIS escrevendo `settings.json` simultaneamente podem corromper arquivo.

**Observações sobre classes-chave**

- `BasePluginMTL._build_ui()`: método superclasse que constrói layout base; `SettingsPlugin._build_ui()` chama `super()._build_ui()` depois adiciona widgets.
- `WidgetFactory.create_radio_button_grid()`: cria grid de rádio buttons com layout automático; retorna `(layout, widget)`.
- `WidgetFactory.create_double_spin_input()`: cria spinbox com label; retorna `(layout, spinbox)`.
- `WidgetFactory.create_bottom_action_buttons()`: cria botões Salvar/Fechar/Ajuda; conecta callbacks.
- `load_tool_prefs(tool_key)`: carrega JSON da pasta de preferências; retorna dict (vazio se arquivo não existe).
- `save_tool_prefs(tool_key, prefs_dict)`: escreve dict em JSON na pasta de preferências.
- `LogUtilsNew`: logging estruturado com `logger.debug()`, `logger.info()`, `logger.warning()`.
- `QDesktopServices.openUrl()`: abre URL em aplicativo padrão; compatível com `file://` URIs em Windows.

**Conversões de unidades**

- Spinbox Limiar exibe valores em **MB** (user-friendly).
- Internamente armazenado em **bytes** (preciso para comparação em runtime).
- Fórmula: `bytes = MB * 1024 * 1024` (ao salvar); `MB = bytes / (1024 * 1024)` (ao carregar).

**Evoluções recomendadas**

- Validação de limiar mínimo: impedir valores < 100 KB ou > 1 GB (warning ao salvar).
- Perfis de preferência: salvar múltiplos perfis (ex: "desenvolvimento", "produção", "performance") e permitir switch rápido.
- Import/Export: botões para exportar/importar JSON de preferências (backup/compartilhamento).
- Sincronização em nuvem: integração com Google Drive/OneDrive para sincronizar preferências entre máquinas.
- Presets de performance: botões rápidos (ex: "Modo Rápido" = Cartesiana + precisão 1, "Modo Preciso" = Elipsoidal + precisão 6).
- Help interativo: tooltips em cada campo explicando impacto (ex: "Valores menores = async mais cedo").
- Auditoria: log de mudanças de preferências com timestamp (quando, quem, valores antigos/novos).

**Conclusão**

Plugin de configurações essencial para customização de comportamento sem alterar código. Interface simples e intuitiva; persistência em JSON garante configurações sobrevivam a reinicializações. Impacto mínimo em dados (nenhum), máximo em UX. Recomendado adicionar validação de range para limiar assíncrono e mecanismo de sincronização para ambientes multi-usuário.
