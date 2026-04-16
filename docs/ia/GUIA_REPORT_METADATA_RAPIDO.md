# Guia Rapido - Report Metadata

## Fluxo 1: Regerar HTML a partir de JSON temporario
1. Abra a ferramenta **Relatorio de Metadata** em Agricultura.
2. Clique em **Atualizar lista de JSON**.
3. Selecione um JSON no combo.
4. Clique em **Gerar relatorio**.
5. Use **Abrir pasta de relatorios** para acessar o HTML.

## Fluxo 2: Gerar vetor sem MRK (somente fotos)
1. Abra **Relatorio de Metadata**.
2. Expanda **Gerar Vetor Sem MRK**.
3. Selecione a **Pasta de fotos**.
4. Marque/desmarque:
   - **Vasculhar subpastas**
   - **Gerar relatorio apos vetorizacao**
5. Clique em **Gerar vetor de fotos**.

## Saidas geradas
- JSON temporario: `%TEMP%/cadmus/reports/json`
- HTML temporario: `%TEMP%/cadmus/reports/html`
- Camada vetorial: adicionada no projeto QGIS (quando houver coordenadas validas).

## Observacoes
- Fotos sem coordenada valida entram no diagnostico do JSON, mas nao entram na camada.
- O fluxo tenta XMP e EXIF; se os dois faltarem, marca baixa confiabilidade no diagnostico.
