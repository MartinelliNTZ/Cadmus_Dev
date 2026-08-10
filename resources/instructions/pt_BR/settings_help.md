<!--
Versao: 1.0.0
Data de criacao: 2026-08-10
Data da ultima modificacao: 2026-08-10
-->

# Configuracoes Cadmus — Guia Rapido

Esta ferramenta centraliza preferencias globais usadas por partes do plugin Cadmus.

No estado atual do codigo, ela permite:

- definir a pasta raiz de projetos Cadmus;
- escolher o SRC (sistema de referencia de coordenadas) padrao;
- definir o idioma da interface (ou auto-detectar o do QGIS);
- escolher o metodo padrao de calculo vetorial (Elipsoidal, Cartesiano, Ambos);
- definir os sufixos dos campos de area cartesiana e elipsoidal;
- definir a precisao numerica de campos vetoriais;
- definir o limiar de feicoes para processamento assincrono;
- controlar quais categorias de ferramentas aparecem na toolbar;
- abrir a pasta local de preferencias do Cadmus.

## Como usar

1. Abra `Cadmus > Configuracoes Cadmus`.
2. Em **Geral**:
   - Defina a pasta de projetos (opcional).
   - Escolha o SRC padrao (recomendado: EPSG:4326 WGS84).
   - Escolha o idioma da interface ou `Auto-detectar`.
   - Ajuste a precisao de campos vetoriais (0 a 10 casas).
   - Ajuste o limiar assincrono (1 a 100000000 feicoes).
   - Marque/desmarque as categorias visiveis na toolbar.
3. Em **Calculos Vetoriais**:
   - Escolha o metodo de calculo: `Elipsoidal`, `Cartesiano` ou `Ambos`.
   - Defina os sufixos dos campos de area (cartesianos e elipsoidais).
4. Clique em `Salvar`.

## O que o plugin faz de verdade

- Carrega preferencias salvas com `load_tool_prefs()`.
- Salva as configuracoes em tres conjuntos de preferencias:
  - chave `SYSTEM` (preferencias globais do aplicativo);
  - chave `VECTOR_FIELDS` (sufixos de area);
  - chave `settings` (estado da janela e colapsaveis).
- Valida que os sufixos cartesiano e elipsoidal nao sejam iguais; se forem, cancela o salvamento e exibe um aviso.
- Mostra uma mensagem de confirmacao apos salvar.
- Recarrega as strings de traducao com o novo idioma selecionado.
- Fecha a janela logo depois de aplicar as preferencias.
- Permite abrir a pasta local onde os arquivos de preferencias ficam armazenados.
- Se a visibilidade das categorias da toolbar mudar, emite um sinal para atualizar a toolbar dinamicamente.

## Significado de cada opcao

- `Pasta de projetos`: salva o caminho em `projects_folder`.
- `SRC padrao`: salva o authid (ex: `EPSG:4326`) em `default_crs_authid`.
- `Idioma`: salva o locale (ex: `pt_BR`) em `plugin_language`; se `Auto-detectar`, remove a chave para o QGIS decidir.
- `Metodo de calculo vetorial`: salva o texto em `calculation_method`.
- `Sufixo cartesiano`: salva em `cartesian_suffix` (chave `VECTOR_FIELDS`).
- `Sufixo elipsoidal`: salva em `ellipsoidal_suffix` (chave `VECTOR_FIELDS`).
- `Precisao de campos vetoriais`: salva um valor inteiro em `vector_field_precision`.
- `Limiar assincrono`: salva um valor inteiro em `async_threshold_features`.
- `Toolbar - Categorias visiveis`: salva um dicionario de categorias em `toolbar_category_visibility`.

## Metodo de calculo vetorial (Elipsoidal vs Cartesiano)

### Elipsoidal (recomendado para WGS84 / SRC geografico)

Calcula areas e comprimentos sobre a **superficie curva do elipsoide** da Terra (ex: WGS84).
- **Ideal para camadas em SRC geografico (lat/lon)** como WGS84 (EPSG:4326).
- Os resultados sao em **metros / metros²**, independente do SRC da camada.
- E mais preciso para grandes areas e altas latitudes, pois considera a curvatura terrestre.
- **Exemplo**: uma area calculada em EPSG:4326 com este metodo retorna valores fisicos reais em m².

### Cartesiano (recomendado para UTM / SRC projetado)

Calcula areas e comprimentos no **plano cartesiano** do SRC da camada.
- **Ideal para SRC projetados como UTM** (ex: EPSG:31983 SIRGAS 2000 / UTM 23S), onde as unidades ja sao metros.
- E rapido e simples, pois usa apenas calculos planares (teorema de Pitagoras / produto vetorial).
- **Cuidado**: em SRC geografico (graus), o calculo cartesiano produziria valores em **graus / graus²**, sem significado fisico.
- Se o modo Cartesiano for solicitado em uma camada geografica, o plugin automaticamente muda para `Ambos` e exibe um aviso.

### Ambos

Calcula os dois metodos simultaneamente.
- Gera **dois campos separados** para cada metrica (um cartesiano e um elipsoidal).
- Usa os sufixos configurados abaixo para diferenciar os campos.
- Util para comparar resultados e validar a qualidade dos dados.

## Tooltips (descricoes dos widgets)

Ao passar o mouse sobre qualquer campo das configuracoes, uma descricao detalhada e exibida:

- **Pasta de projetos**: pasta raiz onde os projetos Cadmus sao criados e organizados; usada como local padrao para novos projetos e arquivos de entrada/saida.
- **SRC padrao**: sistema de referencia usado quando nenhum SRC e especificado; WGS84 (EPSG:4326) e o padrao recomendado para dados globais.
- **Idioma**: define o idioma da interface; `Auto-detectar` usa o idioma do QGIS.
- **Precisao de campos vetoriais**: numero de casas decimais usadas em area, comprimento e coordenadas X/Y; valores maiores aumentam precisao mas geram campos mais longos.
- **Limiar assincrono**: numero minimo de feicoes para o processamento rodar em segundo plano; camadas menores que o limiar rodam de forma sincrona (bloqueante).
- **Toolbar - Categorias visiveis**: controla quais categorias de ferramentas aparecem na toolbar; desmarque para ocultar botoes.
- **Metodo de calculo**: elipsoidal (ideal WGS84/geografico), cartesiano (ideal UTM/projetado) ou ambos.
- **Sufixo cartesiano**: texto adicionado aos campos calculados em modo cartesiano; vazio = sem sufixo.
- **Sufixo elipsoidal**: texto adicionado aos campos calculados em modo elipsoidal; padrao `_eli` para diferenciar dos cartesianos.

## Comportamento importante

- O limiar assincrono atual e medido em numero de feicoes, nao em MB.
- O codigo aceita valores de precisao entre 0 e 10.
- O limiar assincrono aceita valores de 1 ate 100000000.
- Ha retrocompatibilidade de leitura com a antiga chave `async_threshold_bytes`, mas ao carregar o plugin passa a usar o limite por feicoes.
- Os sufixos cartesiano e elipsoidal nao podem ser iguais; o salvamento e bloqueado com um aviso.
- Este plugin apenas salva preferencias; ele nao executa calculos vetoriais por conta propria.

## Pasta de preferencias

- O link da interface tenta abrir a pasta `PREF_FOLDER` no sistema operacional.
- Se a pasta nao existir, o plugin exibe um aviso em vez de abrir o explorador.

## Quando usar

Use esta ferramenta quando quiser ajustar o comportamento padrao de outras ferramentas do Cadmus que dependem dessas preferencias globais.

## Cuidados

- Altere o metodo de calculo apenas se ele fizer sentido para o seu fluxo.
- Se voce reduzir demais o limiar assincrono, mais operacoes podem passar a rodar em segundo plano.
- Se houver comportamento estranho apos mudar preferencias, vale revisar os arquivos salvos na pasta de preferencias.