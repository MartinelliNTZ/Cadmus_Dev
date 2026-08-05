# Configuracoes Cadmus — Guia Rapido

Esta ferramenta centraliza preferencias globais usadas por partes do plugin Cadmus.

No estado atual do codigo, ela permite:

- escolher o metodo padrao de calculo vetorial;
- definir a precisao numerica de campos vetoriais;
- definir o limiar de feicoes para processamento assincrono;
- abrir a pasta local de preferencias do Cadmus.

## Como usar

1. Abra `Cadmus > Configuracoes Cadmus`.
2. Escolha o metodo de calculo vetorial:
- `Elipsoidal`
- `Cartesiano`
- `Ambos`
3. Ajuste a precisao de campos vetoriais.
4. Ajuste o limiar assincrono.
5. Clique em `Salvar`.

## O que o plugin faz de verdade

- Carrega preferencias salvas com `load_tool_prefs()`.
- Salva as configuracoes no conjunto de preferencias da chave `settings`.
- Mostra uma mensagem de confirmacao apos salvar.
- Fecha a janela logo depois de aplicar as preferencias.
- Permite abrir a pasta local onde os arquivos de preferencias ficam armazenados.

## Significado de cada opcao

- `Metodo de calculo vetorial`: define o texto da preferencia `calculation_method`.
- `Precisao de campos vetoriais`: salva um valor inteiro em `vector_field_precision`.
- `Limiar assincrono`: salva um valor inteiro em `async_threshold_features`.

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
