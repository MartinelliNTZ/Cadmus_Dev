# Guia de Internacionalizacao

## Objetivo

Este documento explica o padrao adotado para substituir strings hardcoded por `STR.*` no plugin Cadmus, como organizar novas chaves em `i18n/Strings_pt_BR.py`, e como continuar o trabalho sem perder consistencia.

## Arquivos centrais

- `i18n/Strings_pt_BR.py`
- `i18n/Strings_en.py`
- `i18n/Strings_es.py`
- `i18n/TranslationManager.py`

`STR` e a instancia retornada por `TranslationManager`, entao tudo o que for exibido ao usuario deve, sempre que possivel, vir de `STR`.

## Regra principal

Trocar apenas textos visiveis ao usuario.

Nao trocar:

- mensagens de `self.logger`
- comentarios
- nomes internos de classes, metodos, variaveis e chaves tecnicas

Trocar:

- titulos de janela
- labels
- textos de botoes
- opcoes de checkbox/radio
- mensagens de `QMessageBox`
- mensagens em `QgisMessageUtil`
- textos de progresso
- textos copiados para clipboard
- blocos textuais mostrados em dialogs e resultados

## Como decidir o nome da string

### 1. Se a string for generica, nao usar prefixo do plugin

Exemplos bons:

- `SAVE`
- `CLOSE`
- `WARNING`
- `ERROR`
- `ADVANCED_PARAMETERS`
- `ASYNC_START_ERROR`
- `INPUT_LINE_LAYER`
- `OUTPUT_FOLDER`

Essas chaves devem ficar em grupos genericos do arquivo de strings.

### 2. Se a string for especifica da funcionalidade, usar prefixo do plugin

Exemplos:

- `SETTINGS_TITLE`
- `REPLACE_IN_LAYOUTS_TITLE`
- `LOAD_FOLDER_LAYERS_TITLE`
- `GENERATE_TRAIL_TITLE`
- `COPY_ATTRIBUTES_TITLE`
- `EXPORT_ALL_LAYOUTS_TITLE`

Use prefixo do plugin quando o texto fizer sentido apenas naquele contexto.

### 3. Reaproveitar antes de criar

Antes de adicionar uma chave nova:

1. procurar se ja existe uma string equivalente em `Strings_pt_BR.py`
2. avaliar se uma pequena generalizacao resolve
3. so criar nova chave se a reutilizacao deixar o nome confuso

Exemplo de boa decisao:

- usar `ADVANCED_PARAMETERS` em vez de `GENERATE_TRAIL_ADVANCED_PARAMETERS`

Exemplo de ma decisao:

- criar `LOAD_FOLDER_LAYERS_ASYNC_START_ERROR` para um texto que serve para qualquer fluxo assincrono

## Como lidar com strings dinamicas

Nao colocar placeholders complexos na string quando isso piorar a manutencao.

Preferir montar no plugin:

```python
QMessageBox.information(
    self,
    STR.SETTINGS_SAVED_TITLE,
    f"{STR.CALCULATION_METHOD_LABEL} {selected_method}\n\n"
    f"{STR.SETTINGS_SAVED_MESSAGE}",
)
```

Boas praticas:

- manter emojis no plugin
- manter HTML no plugin
- manter caminhos de arquivo no plugin
- manter valores variaveis no plugin

Ou seja, a string centralizada deve guardar o texto base, e a composicao final acontece no codigo quando houver variaveis no meio.

## Organizacao atual de `Strings_pt_BR.py`

O arquivo foi reorganizado em grupos para facilitar reutilizacao:

- `General`
- `About`
- `Buttons`
- `Common labels`
- `Common option labels`
- `Common messages`
- blocos especificos por plugin

Ao adicionar novas chaves:

- primeiro tente encaixar nos grupos genericos
- so depois crie um bloco especifico do plugin

## Processo recomendado para alterar um plugin

### Passo 1. Ler o plugin inteiro

Identifique todos os textos visiveis ao usuario.

### Passo 2. Separar o que e UI do que e tecnico

Nao mexa em:

- logs
- comentarios
- strings de debug
- nomes internos

### Passo 3. Procurar reaproveitamento

Antes de criar uma nova chave, verifique se ja existe algo equivalente em:

- `Buttons`
- `Common labels`
- `Common option labels`
- `Common messages`

### Passo 4. Criar chaves novas com nomes intuitivos

Se for generica, nome generico.
Se for especifica, prefixo do plugin.

### Passo 5. Substituir no plugin

Importar:

```python
from ..i18n.TranslationManager import STR
```

E trocar os hardcodes por `STR.*`.

### Passo 6. Atualizar `Strings_en.py` e `Strings_es.py`

Toda chave nova em `Strings_pt_BR.py` deve ganhar traducao correspondente nos arquivos:

- `i18n/Strings_en.py`
- `i18n/Strings_es.py`

Esses arquivos herdam de `Strings_pt_BR`, mas nao devem depender eternamente do fallback em portugues para textos novos.

### Passo 7. Atualizar changelog

Registrar no:

- `docs/ia/changelog.txt`

Resumo esperado:

- plugins alterados
- reorganizacao das strings
- novas traducoes adicionadas

## O que evitar

- criar nomes especificos demais para textos genericos
- repetir a mesma frase em varias chaves com nomes diferentes
- colocar placeholder desnecessario dentro da string
- traduzir log junto com UI
- deixar chave nova apenas em `pt_BR` quando o fluxo ja usa `en/es`

## Checklist rapido

- o texto e visivel ao usuario?
- a chave ja existe?
- o nome ficou intuitivo?
- ela pertence a um grupo generico ou especifico?
- o plugin agora usa `STR.*`?
- `Strings_en.py` foi atualizado?
- `Strings_es.py` foi atualizado?
- o changelog foi atualizado?

## Plugins ja ajustados neste ciclo

- `SettingsPlugin`
- `ReplaceInLayouts`
- `LoadFolderLayers`
- `GenerateTrailPlugin`
- `CopyAttributesPlugin`
- `ExportAllLayouts`
- `coord_result_dialog`
- `DroneCoordinates`

## Regra de ouro

Se a mesma frase puder aparecer em mais de um plugin, prefira uma chave generica.
Se a frase so fizer sentido em um unico plugin, use prefixo especifico.

O objetivo nao e apenas traduzir, mas deixar o catalogo de strings facil de manter, facil de entender e facil de reaproveitar.
