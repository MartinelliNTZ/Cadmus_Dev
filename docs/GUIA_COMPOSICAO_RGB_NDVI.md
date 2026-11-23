# Guia de composição RGB e cálculo de NDVI no QGIS

Este guia descreve como montar uma composição colorida RGB e como calcular o
NDVI (Normalized Difference Vegetation Index) com segurança. O foco é evitar
resultados visualmente convincentes, mas radiometricamente incorretos.

> **Regra principal:** antes de combinar bandas ou calcular um índice, confirme
> o sensor, o produto, a identificação espectral das bandas, as unidades dos
> pixels, o valor NoData e a grade espacial. O número da banda, sozinho, não
> identifica sua função.

## 1. O que precisa ser conferido antes de começar

Prepare uma cópia de trabalho e registre, para cada entrada:

- sensor, satélite, câmera ou produto utilizado;
- data e hora de aquisição;
- nível do produto: valores digitais (DN), radiância, reflectância no topo da
  atmosfera (TOA) ou reflectância de superfície;
- nome, número, faixa espectral e resolução espacial de cada banda;
- fator de escala, offset e tipo numérico armazenado;
- valor NoData, máscara de qualidade (QA), nuvens, sombras, cirrus, neve e
  pixels saturados;
- CRS, resolução, extensão, número de linhas/colunas e origem da grade;
- se o arquivo é multibanda ou se cada banda está em um arquivo separado.

Não use uma legenda, um tutorial de outro sensor ou apenas o nome do arquivo
para deduzir esses valores. A fonte de verdade deve ser o metadado do produto
e a documentação do sensor.

## 2. Composição RGB

### 2.1 O que é uma composição RGB

Uma composição RGB associa três bandas a três canais de exibição:

| Canal de exibição | Composição natural | Falsa cor infravermelha |
|---|---|---|
| Vermelho (R) | banda vermelha | banda NIR |
| Verde (G) | banda verde | banda vermelha |
| Azul (B) | banda azul | banda verde |

Os nomes “natural” e “falsa cor” descrevem a visualização, não uma alteração
nas medições. A composição não cria informação espectral nova; apenas organiza
bandas existentes em um raster de três bandas ou em uma simbologia RGB.

Uma banda multibanda já contém as bandas no mesmo arquivo. Nesse caso, não é
necessário fundi-las fisicamente para visualizar RGB: basta configurar a
simbologia **Multiband color** da camada e informar qual banda será usada em R,
G e B.

### 2.2 Quando as bandas estão em arquivos separados

Só combine bandas separadas depois de confirmar que elas são compatíveis:

1. pertencem à mesma cena ou foram adquiridas no mesmo instante;
2. usam a mesma unidade física e o mesmo nível de processamento;
3. têm a mesma extensão, CRS, resolução e grade de pixels;
4. estão alinhadas pixel a pixel, sem deslocamento de meia célula;
5. têm o mesmo tratamento de NoData e as mesmas máscaras de validade.

Se alguma condição não for atendida, reprojete e alinhe as bandas antes da
composição. Reprojetar somente uma banda ou simplesmente recortar pelo mesmo
retângulo não garante alinhamento de pixels.

### 2.3 Procedimento no QGIS

#### Opção A — somente visualizar

1. Carregue o raster multibanda no QGIS.
2. Abra **Propriedades da camada > Simbologia**.
3. Selecione **Multiband color**.
4. Defina as bandas nos canais R, G e B conforme o produto e a composição
   desejada.
5. Ajuste o contraste usando estatísticas da própria cena. Um corte por
   percentis pode melhorar a visualização, mas não deve alterar os valores do
   raster usado em cálculos.

Essa opção altera a renderização. Ela não cria um novo arquivo RGB.

#### Opção B — criar um raster multibanda

Para bandas em arquivos separados:

1. Carregue as bandas e confira as propriedades de cada uma.
2. Se necessário, reprojete e alinhe todas para a mesma CRS, resolução,
   extensão e grade.
3. Abra **Processamento > GDAL > Construir raster virtual (VRT)**.
4. Selecione os arquivos na ordem em que deseja armazená-los: primeiro R,
   depois G e depois B.
5. Ative a opção equivalente a **colocar cada arquivo de entrada em uma banda
   separada**.
6. Gere o VRT e confira a ordem das bandas no resultado.
7. Para um arquivo independente dos originais, converta o VRT para GeoTIFF
   com **GDAL > Translate (converter formato)**. O VRT continua referenciando
   os arquivos de origem; se eles forem movidos, o VRT poderá deixar de
   funcionar.

Quando a composição for produzida por código do Cadmus, a operação existente
para composição de bandas é
*RasterLayerProcessing.compose_multiband_raster*. Ela deve receber as bandas
já validadas e alinhadas; a composição não substitui a etapa de controle de
qualidade.

### 2.4 Tipo de dado e formato de saída

Escolha o tipo de dado conforme o objetivo:

- **Float32:** reflectância, radiância ou qualquer produto que preserve casas
  decimais;
- **UInt16 ou outro inteiro original:** dados quantizados que ainda precisam
  ser calibrados;
- **Byte/UInt8:** somente uma cópia destinada à visualização após alongamento
  de contraste, nunca o arquivo principal para NDVI.

Use GeoTIFF com compressão sem perdas quando o arquivo for persistente. Para
aquisições grandes, tiling, BigTIFF e overviews podem melhorar o desempenho,
mas devem ser configurados sem mudar os valores científicos. Não use JPEG ou
outra compressão com perdas para o raster que será usado em análises.

### 2.5 Máscara alfa e NoData não são a mesma coisa

- **NoData** informa que o pixel não deve participar da análise.
- **Máscara QA** registra a qualidade ou a razão da exclusão.
- **Canal alfa** controla transparência na tela.

Um pixel transparente pode continuar contendo um número válido. Portanto, não
use a transparência visual como substituta de NoData ou de uma máscara de
qualidade. Preserve a máscara original quando ela for necessária para o NDVI.

### 2.6 Validação da composição RGB

Depois de gerar o arquivo, confira:

- o raster possui exatamente três bandas, na ordem esperada;
- o mapeamento R/G/B está correto, sem troca entre vermelho, verde e azul;
- CRS, extensão, resolução, linhas, colunas e origem da grade coincidem com as
  bandas de entrada;
- tipo de dado, escala, offset e NoData foram preservados;
- não existem bordas, faixas ou deslocamentos causados por alinhamento ruim;
- a imagem faz sentido em áreas conhecidas, sem depender apenas de uma cor
  visualmente agradável;
- o histograma não foi alterado de forma irreversível por conversão para Byte.

Para uma falsa cor NIR-R-G, vegetação vigorosa normalmente aparece em tons
avermelhados, mas a cor exata depende do contraste, da máscara, da atmosfera e
da simbologia. A cor, sozinha, não é uma validação radiométrica.

## 3. NDVI

### 3.1 Fórmula

O NDVI usa uma banda no infravermelho próximo (NIR) e uma banda no vermelho
(Red):

    NDVI = (NIR - Red) / (NIR + Red)

Ele não é calculado a partir dos canais R, G e B de uma imagem renderizada.
Para calculá-lo, use os rasters espectrais originais ou bandas calibradas.

O resultado idealmente fica entre -1 e +1, mas valores fora desse intervalo
podem surgir por ruído, pixels inválidos, saturação, escalas incorretas ou
efeitos atmosféricos. Não limite automaticamente o resultado a -1/+1 sem
investigar a causa.

### 3.2 Escolha correta das bandas

Escolha a banda vermelha e a NIR pela faixa espectral e pelo metadado do sensor:

- **Red:** faixa próxima da absorção da clorofila, aproximadamente na região de
  0,64–0,67 µm;
- **NIR:** faixa próxima de 0,8–0,9 µm, onde a vegetação saudável tende a
  apresentar alta reflectância.

Esses intervalos são uma referência física, não uma lista universal de números
de banda. A banda red edge não é automaticamente a banda Red e não deve ser
usada no lugar da NIR sem justificar outro índice.

Não misture uma banda de reflectância de superfície com outra de DN, TOA ou
radiância. Também não misture cenas, datas ou produtos diferentes sem um
objetivo analítico explícito e sem documentar a compatibilização.

### 3.3 Pré-processamento obrigatório

Antes do cálculo:

1. **Calibre os valores.** Aplique o fator de escala e o offset indicados no
   metadado. Não presuma que o valor armazenado é reflectância entre 0 e 1.
2. **Use a mesma unidade nas duas bandas.** Se houver escala ou offset, aplique
   a transformação completa a Red e NIR antes da divisão.
3. **Alinhe as grades.** As duas bandas devem ter a mesma CRS, resolução,
   extensão, número de linhas/colunas e geotransformação.
4. **Reamostre com coerência.** Para reflectância contínua, use o mesmo método
   nas duas bandas, normalmente bilinear quando a reprojeção for necessária.
   Para máscaras categóricas, use vizinho mais próximo. Evite interpolar uma
   máscara QA como se fosse reflectância.
5. **Aplique as máscaras.** Exclua, conforme o objetivo, nuvens, sombras,
   cirrus, neve/gelo, água, pixels saturados, bordas ruins e pixels sem
   observação válida.
6. **Preserve o NoData.** Não transforme NoData em zero sem verificar o
   produto. Zero pode ser um valor físico possível ou uma codificação de
   inválido, dependendo da fonte.
7. **Recorte somente depois de alinhar** ou use o mesmo grid de referência para
   que Red e NIR tenham exatamente os mesmos pixels na área de interesse.

A reflectância de superfície costuma ser a escolha mais adequada para mapas de
vegetação e comparações temporais, mas a decisão depende do produto e do
objetivo. O nível radiométrico usado deve ser registrado no resultado.

### 3.4 Cálculo no Raster Calculator do QGIS

Supondo que os nomes das bandas sejam NIR e RED, uma expressão básica é:

    ("NIR@1" - "RED@1") / ("NIR@1" + "RED@1")

Use uma proteção contra denominador nulo ou instável:

    if(
      abs("NIR@1" + "RED@1") <= 0.000001,
      NULL,
      ("NIR@1" - "RED@1") / ("NIR@1" + "RED@1")
    )

O valor 0.000001 é apropriado apenas quando as entradas estão em uma escala
semelhante à reflectância entre 0 e 1. Para DN ou outra escala, use um limite
coerente com a unidade, ou calibre as bandas antes do cálculo. O objetivo é
evitar divisão por zero e resultados numericamente instáveis, não esconder
pixels ruins.

Na janela do Raster Calculator:

1. selecione a banda NIR e a banda Red corretas;
2. use a expressão com proteção do denominador;
3. defina a extensão e a resolução a partir de uma grade de referência já
   alinhada;
4. grave o resultado como **Float32**;
5. defina NoData de saída ou use a máscara de validade de modo que pixels
   inválidos permaneçam inválidos;
6. verifique o CRS de saída e evite gerar o índice em uma grade diferente sem
   justificativa.

Se a calibração ainda não tiver sido aplicada, use bandas calibradas como
entradas. Não faça uma divisão usando os DN e tente corrigir o resultado depois
por meio de uma multiplicação simples: um offset aditivo pode mudar o
denominador e alterar o índice.

### 3.5 Máscaras e pixels inválidos

Uma forma segura de pensar no cálculo é:

    se Red ou NIR for inválido:
        NDVI = NoData
    senão se abs(NIR + Red) <= limite:
        NDVI = NoData
    senão:
        NDVI = (NIR - Red) / (NIR + Red)

Além da máscara de nuvens, considere a máscara de sombra. Uma nuvem pode ser
removida e ainda deixar a sombra correspondente, produzindo NDVI artificialmente
baixo. Em áreas agrícolas, também podem ser relevantes solo exposto, palhada,
água entre linhas e pixels mistos na borda dos talhões.

### 3.6 Simbologia e interpretação

Para inspeção, uma rampa divergente ou sequencial com limite fixo de -1 a +1
facilita a comparação entre cenas. Estatísticas de cada cena podem ser úteis
para explorar detalhes, mas um alongamento automático diferente em cada mapa
pode fazer resultados distintos parecerem iguais.

As faixas abaixo são apenas uma orientação inicial:

| NDVI aproximado | Possível interpretação |
|---:|---|
| menor que 0 | água, sombra, nuvem, neve ou superfície sem vegetação; investigar a máscara |
| 0 a 0,2 | solo exposto, material seco ou vegetação muito esparsa |
| 0,2 a 0,5 | vegetação esparsa a moderada ou mistura de coberturas |
| acima de 0,5 | vegetação mais densa, dependendo do sensor, cultura e condição |

Não use esses limites como classificação universal. Cultura, estágio fenológico,
tipo de solo, umidade, geometria de aquisição, atmosfera e resolução espacial
podem mudar os valores. Para tomada de decisão, valide com observações de campo
ou outra fonte independente.

### 3.7 Controle de qualidade do NDVI

Após o cálculo, faça pelo menos estas verificações:

- inspecione histograma, mínimo, máximo, média e percentis;
- procure valores fora de -1/+1 e investigue-os antes de corrigi-los;
- compare áreas conhecidas de vegetação, solo, água e construções;
- sobreponha o NDVI à imagem RGB ou à falsa cor para localizar nuvens, sombras,
  bordas e deslocamentos;
- verifique se o NoData não virou uma faixa extrema da legenda;
- confirme que não há linhas, blocos, halos ou costuras na área de mosaico;
- confirme que a mesma máscara e o mesmo tratamento radiométrico foram usados
  quando comparar datas;
- amostre alguns pixels e refaça a fórmula manualmente para confirmar a ordem
  NIR/Red;
- registre a versão do produto, a fórmula, as bandas, o fator de escala, o
  offset, as máscaras, o método de reamostragem e o tipo do arquivo de saída.

## 4. Erros frequentes e correção

| Erro | Consequência | Correção |
|---|---|---|
| Trocar a ordem R/G/B | Cores falsas ou interpretação visual errada | Conferir a atribuição dos canais e o metadado |
| Confundir número da banda com faixa espectral | RGB/NDVI calculado com banda inadequada | Usar a documentação do sensor |
| Usar a imagem renderizada para o NDVI | Contraste e cores contaminam o cálculo | Usar Red e NIR espectrais |
| Misturar DN, TOA e reflectância | Valores e comparações sem significado físico | Calibrar e usar o mesmo nível de produto |
| Ignorar escala e offset | NDVI distorcido, sobretudo com offset aditivo | Calibrar as duas bandas antes da fórmula |
| Red e NIR desalinhadas | Bordas, ruído e valores de outra cobertura | Reprojetar/reamostrar para uma grade comum |
| Salvar NDVI como inteiro | Perda de precisão ou truncamento | Usar Float32 |
| Tratar NoData como zero | Índice artificialmente baixo ou alto | Preservar NoData e aplicar máscara |
| Ignorar divisão por zero | Infinitos, erros ou manchas | Usar limite para o denominador |
| Usar somente máscara de nuvem | Sombras e pixels ruins permanecem | Aplicar QA completa e inspecionar resultado |
| Usar interpolação em máscara QA | Classes inválidas entre categorias | Reamostrar QA por vizinho mais próximo |
| Usar contraste por percentis como dado científico | Valores originais são alterados | Aplicar alongamento somente na visualização |
| Comparar datas com produtos diferentes | Tendência aparente causada pelo processamento | Padronizar produto, máscara, escala e grade |
| Usar compressão com perdas | Artefatos nos pixels e nas bordas | Usar compressão sem perdas |
| Confundir canal alfa com NoData | Pixels transparentes entram no cálculo | Configurar NoData/máscara explicitamente |

## 5. Fluxo recomendado de ponta a ponta

1. Identifique sensor, produto, bandas, unidades, escala, offset e máscaras.
2. Faça uma cópia de trabalho e preserve os arquivos originais.
3. Valide CRS, resolução, extensão, dimensões e alinhamento.
4. Reprojete e alinhe bandas incompatíveis usando uma grade de referência.
5. Calibre Red e NIR para a mesma unidade física.
6. Gere a composição RGB apenas para inspeção e comunicação, se necessário.
7. Aplique máscaras de qualidade e mantenha NoData corretamente.
8. Calcule o NDVI com proteção para denominador nulo/instável e saída Float32.
9. Valide estatísticas, mapas, pixels amostrados e áreas conhecidas.
10. Exporte o raster final com metadados do processamento e sem substituir os
    originais.

## 6. Checklist final

Antes de entregar ou usar o resultado:

- [ ] As bandas foram identificadas pela faixa espectral, não apenas pelo número.
- [ ] Red e NIR pertencem ao mesmo produto e estão na mesma unidade.
- [ ] Escala e offset foram aplicados conforme o metadado.
- [ ] As bandas estão alinhadas na mesma grade.
- [ ] NoData, nuvens, sombras, cirrus e saturação foram tratados.
- [ ] O RGB usa a ordem correta de canais.
- [ ] O NDVI foi calculado com a fórmula correta e denominador protegido.
- [ ] O NDVI foi salvo como Float32.
- [ ] Estatísticas e pixels conhecidos foram verificados.
- [ ] Máscaras, parâmetros e origem dos dados foram documentados.
- [ ] O arquivo original não foi sobrescrito.

