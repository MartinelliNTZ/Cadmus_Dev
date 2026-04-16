# Análise de Cenário – Replace Text in Layouts (ReplaceInLayoutsDialog)

**Visão Geral**

A ferramenta localiza e substitui texto em rótulos (QgsLayoutItemLabel) dentro de todos os layouts de um projeto QGIS. Suporta opções de sensibilidade a maiúsculas/minúsculas, modo "chave" (substituição de conteúdo completo), criação automática de backup do projeto e geração de log detalhado de operações.

**Objetivo**

Automatizar substituições de texto em massa nos layouts de projetos QGIS, eliminando necessidade de edição manual de dezenas ou centenas de rótulos. Operação não bloqueante com rastreabilidade total via backup + log.

**Fluxo resumido**

- **Entrada**: Texto a buscar + Texto a substituir (via InputFieldsWidget) + opções (case_sensitive, full_replace).
- **Validação**: verificar se `old_text` não está vazio; bloquear execução se vazio.
- **Backup**: se projeto salvo, `ProjectUtils.create_project_backup()` gera cópia timestamped em `/backup/`.
- **Processamento**: `LayoutsUtils.replace_text_in_layouts()` itera todos layouts → todos rótulos → executa `replace()` ou substitui conteúdo completo conforme opção.
- **Logging**: `LogUtilsNew` registra cada ocorrência (layout, rótulo antigo, rótulo novo) em arquivo `.txt` na pasta `/backup/`.
- **Resultado**: callback retorna dict com `total_changes`, `total_layouts`, estrutura de relatório.
- **UI**: exibe modal de sucesso com resumo; se projeto não salvo, aviso (mas permite continuar sem backup).
- **Pós-processo**: nenhuma persistência automática (user responsável por salvar projeto via File → Save).

**Cenários de Uso (exemplos)**

### Cenário 1: Atualização Simples de Ano
- Project: `mapa_2024.qgz` (salvo).
- Buscador: "2023"
- Substituidor: "2024"
- Case sensitive: desativado.
- Full replace: desativado.
- Layouts: 5 (cada um com 3-5 rótulos com "2023").
- Resultado:
  - Backup criado: `mapa_2024_20260309_110534.qgz`
  - Log gerado: `replace_log_20260309_110534.txt` (15 substituições registradas)
  - Modal: "Layouts analisados: 5 | Substituições aplicadas: 15"

### Cenário 2: Substituição Sensível a Maiúsculas
- Buscador: "Seinfra" (minúscula no "i")
- Substituidor: "SEINFRA"
- Case sensitive: **ativado**.
- Resultado: busca exata por "Seinfra" (não encontra "SEINFRA" ou "seinfra", apenas "Seinfra").

### Cenário 3: Modo "Chave" (Substituição Completa de Rótulo)
- Rótulo original: "Mapa de Uso do Solo - Safra 2023"
- Buscador: "2023" (encontrado)
- Full replace: **ativado**.
- Substituidor: "2024"
- Resultado: rótulo completo SUBSTITUÍDO por "2024" (não apenas "2023" → "2024").
- Use case: rótulos parametrizados onde encontrar a chave = substituir tudo.

### Cenário 4: Projeto Não Salvo
- Abre projeto recém-criado (sem arquivo .qgz).
- Clica "Executar substituição".
- Sistema avisa: "Projeto não salvo. Continuar sem backup? (Sim/Não)".
- User clica "Sim".
- Substituição executa sem backup.
- Log registra: "AVISO: Executado sem backup - projeto não salvo em disco"

### Cenário 5: Busca com Resultado Zero
- Buscador: "TextoQuenaoExiste123"
- Sistema processa todos layouts, não encontra ocorrências.
- Modal: "Layouts analisados: 5 | Substituições aplicadas: 0"
- Log registra: "Nenhuma ocorrência encontrada em 5 layouts"

### Cenário 6: Múltiplos Layouts com Subst. Diferentes
- 10 layouts no projeto.
- 8 contêm o buscador, 2 não contêm.
- Resultado: apenas 8 layouts aparece no log; 2 ignorados (não listados).
- Total: "Layouts com alterações: 8/10"

### Cenário 7: Caracteres Especiais
- Buscador: "Km 10+500"
- Substituidor: "KM 10+500"
- Sistema preserva caracteres especiais (+, espaços, etc).
- Resultado: busca e substituição precisas.

### Cenário 8: Troca Rápida via Botão "⇅ Inverter"
- User preenche:
  - Buscar: "TextoAntigo"
  - Substituir: "TextoNovo"
- Clica botão "⇅ Inverter".
- Resultado: campos são automaticamente trocados:
  - Buscar: "TextoNovo"
  - Substituir: "TextoAntigo"
- Útil para reverter substituições (undo manual).

**Tipos de layout e conteúdo**

- **Entrada**: Layouts (QgsLayout) contendo rótulos textuais (QgsLayoutItemLabel).
- **Saída**: Mesmos layouts com conteúdo de rótulos atualizado.
- **Suportado**: Qualquer conteúdo de texto em rótulos.
- **Não suportado**: Imagens, shapefiles, SQL (elementos dinâmicos complexos).

**Impactos nos dados**

- **Preservado**: estrutura de layout intacta; posição, tamanho, fontes de rótulos.
- **Alterado**: conteúdo textual de rótulos conforme parâmetros.
- **Criado**: backup + log de auditoria.
- **Não alterado**: projeto não é salvo automaticamente (user responsável).

**Riscos e controles**

- **Texto em branco**: se `old_text` vazio, validação bloqueia com mensagem "Informe o texto a buscar."
- **Substituição errada**: modo full_replace pode sobrescrever conteúdo desejado (aviso recomendado na UI).
- **Sem backup se projeto não salvo**: aviso ao user; user deve clicar "Sim" para continuar sem backup (documentado).
- **Perda de alterações de rótulos posteriores**: se user faz edições de rótulos enquanto substituição está ocorrendo (threading issue, improvável em UI thread).
- **Corrupção do backup**: se pasta de backup não tem permissão de escrita → fallback (continuar sem backup).
- **Case sensitive com acento**: regex diferencia acentuação conforme setting; validar comportamento em "Seinfra" vs "Seinfrá".
- **Layouts com conteúdo dinâmico**: expressões SQL/Python em rótulos NÃO são processadas (apenas conteúdo estático).

**Observações sobre classes-chave**

- `InputFieldsWidget`: retorna dict com 'old_text' e 'new_text' via `get_values()`; usar `.strip()` para remover espaços extras.
- `LayoutsUtils.replace_text_in_layouts()`: itera `QgsProject.instance().layoutManager().layouts()` e cada `layout.itemsByType(QgsLayoutItem.LayoutLabel)`.
  - Parâmetros: `project`, `tool_key`, `old_text`, `new_text`, `case_sensitive`, `full_replace`.
  - Retorna: dict com `total_changes`, `total_layouts`, lista de layouts alterados.
- `ProjectUtils.create_project_backup()`: cria arquivo .qgz em `project_dir/backup/project_name_YYYYMMDDHHMMSS.qgz`.
  - Falha se pasta sem permissão de escrita → registra warning, continua.
- `ProjectUtils.is_project_saved()`: retorna True se arquivo .qgz existe em disco.
- `LogUtilsNew`: classe central para logging semântico (v1.6.2+); registra cada substituição com contexto (layout, rótulo antigo, novo).
  - Método: `LogUtilsNew.log_replace_operation(old_text, new_text, layout_name, total_count)`.
- `QgisMessageUtil.confirm_destructive()`: dialog de confirmação com aviso visual (cor vermelha); retorna True se user confirma.
- Botão "⇅ Inverter": conecta a `_swap_fields()` que invoca `InputFieldsWidget.set_values()` com valores trocados.

**Evoluções recomendadas**

1. **Preview pré-execução**: exibir lista de layouts/rótulos que serão alterados antes de confirmar.
2. **Undo integrado**: armazenar estado anterior em stack para reverter com um clique (em vez de manualmente inverter).
3. **Regex avançado**: permitir padrões regex em busca (ex.: "\d{4}" para encontrar qualquer ano).
4. **Filtro de layouts**: seleção de quais layouts processar (em vez de todos).
5. **Relatório exportável**: salvar relatório mais detalhado em CSV/PDF com timestamps e versões anteriores/novas.
6. **Lote de substituições**: carregar múltiplos pares (busca, replace) de arquivo CSV e executar sequencialmente.
7. **Histórico de operações**: manter log local de todas as substituições executadas (auditoria de longo termo).
8. **Teste de impacto**: modo "dry-run" (executar substituição sem gravar, apenas reportar).

**Conclusão**

Ferramenta clara e segura com auditoria via backup + log. Fluxo não bloqueante e reversível (user responsável por desfazer via projeto anterior). Prioridades:
1. Validação de `old_text` não vazio.
2. Aviso de modo "chave" (substitui conteúdo completo).
3. Backup funcional com versioning automático (backup nunca sobrescreve arquivo anterior).
4. Log detalhado com contexto de cada substituição (layout, rótulo antes/depois).
5. Documentação clara: backup em `/projeto/backup/` (user deve conhecer local).
6. Test: caso de uso com caracteres especiais e acentuação (verificar comportamento regex).
7. Thread-safety: garanta que `LayoutsUtils` não bloqueia UI (threading check).
