class HtmlInstructions:
    def __init__(self, provider):
        self.provider = provider

    def get_raster_difference_statistics_help(self):
        return f"""
            {self.provider.logo}
            Ferramenta do pacote Cadmus para cálculo de diferença entre múltiplos rasters, com geração automática de estatísticas e relatório consolidado em HTML.
            {self.provider.transform_h('Objetivo')}
            Calcular diferenças entre todos os pares possíveis de rasters.
            Identificar variações entre superfícies.
            Gerar estatísticas automáticas para cada comparação.
            Consolidar resultados em relatório único.
            {self.provider.transform_h('Como usar')}
            1. Abra a ferramenta.
            2. Informe uma pasta com rasters ou selecione rasters já carregados no QGIS.
            3. Defina a saída, se quiser.
            4. Execute.
            {self.provider.transform_h('Saídas')}
            DIF_rasterA_rasterB.tif
            DIF_rasterA_rasterB_stats.html
            raster_difference_stats_summary.html
            {self.provider.transform_h('Atenções')}
            O número de combinações cresce rapidamente.
            Pode gerar muitos arquivos.
            Diferenças usam apenas a banda 1.
            {self.provider.author_info}
        """

    def get_difference_fields_help(self):
        return f"""
            {self.provider.logo}
            Ferramenta do pacote Cadmus para gerar campos de diferença entre um campo base e outros campos numéricos da camada.
            {self.provider.transform_h('Objetivo')}
            Calcular a diferença entre vários atributos numéricos usando um campo base como referência.
            {self.provider.transform_h('Como usar')}
            1. Abra a ferramenta.
            2. Selecione a camada de pontos.
            3. Defina o campo base.
            4. Escolha os campos a excluir, se necessário.
            5. Configure prefixo e precisão.
            6. Execute.
            {self.provider.transform_h('Saídas')}
            Novos campos com o prefixo definido.
            {self.provider.transform_h('Atenções')}
            Campos não numéricos são ignorados.
            Valores nulos geram saída nula.
            {self.provider.author_info}
        """

    def get_raster_mass_clipper_help(self):
        return f"""
            {self.provider.logo}
            Ferramenta do pacote Cadmus para recorte em lote de rasters usando uma camada poligonal como máscara.
            {self.provider.transform_h('Objetivo')}
            Recortar múltiplos rasters em uma única execução.
            Permitir recorte por camada inteira ou por feição.
            Aplicar correção automática de borda.
            {self.provider.transform_h('Como usar')}
            1. Abra a ferramenta.
            2. Defina a máscara poligonal.
            3. Selecione os rasters.
            4. Configure o modo e a pasta de saída.
            5. Execute.
            {self.provider.transform_h('Saídas')}
            raster_clip.tif
            raster_feat_1.tif
            {self.provider.transform_h('Atenções')}
            O modo por feição pode gerar muitos arquivos.
            O buffer amplia levemente a área recortada.
            {self.provider.author_info}
        """

    def get_geometry_difference_line_help(self):
        return f"""
            {self.provider.logo}
            Ferramenta do pacote Cadmus para criação de linhas entre pontos com cálculo de distância.
            {self.provider.transform_h('Objetivo')}
            Gerar linhas conectando pontos relacionados.
            Calcular distância entre pares.
            Suportar comparação entre uma ou duas camadas.
            {self.provider.transform_h('Como usar')}
            1. Abra a ferramenta.
            2. Selecione a camada A.
            3. Ative a segunda camada se necessário.
            4. Defina os campos de agrupamento.
            5. Execute.
            {self.provider.transform_h('Saídas')}
            Camada de linhas com group_key, feature_a, feature_b e distance.
            {self.provider.transform_h('Atenções')}
            O modo 2 exige camada B e campo correspondente.
            Geometrias vazias são ignoradas.
            {self.provider.author_info}
        """

    def get_create_grid_v1_help(self):
        return f"""
            {self.provider.logo}
            Ferramenta do pacote Cadmus para criar uma grade de pontos, linhas ou polígonos dentro de uma área poligonal.
            {self.provider.transform_h('Objetivo')}
            Gerar uma grade regular usando a extensão de uma camada de entrada.
            Extrair a grade somente onde ela intersecta a camada de entrada.
            {self.provider.transform_h('Como usar')}
            1. Abra a ferramenta.
            2. Selecione a camada de entrada de polígonos.
            3. Defina o espaçamento horizontal e vertical.
            4. Selecione o tipo de grade.
            5. Ative o log detalhado se desejar acompanhar a execução.
            6. Execute.
            {self.provider.transform_h('Saídas')}
            Camada de grade com geometria de ponto, linha ou polígono.
            {self.provider.transform_h('Atenções')}
            O espaçamento define a densidade da grade.
            Se a camada de entrada tiver geometrias inválidas, a extração pode produzir uma grade menor.
            {self.provider.author_info}
        """

    def get_raster_mass_sampler_help(self):
        return f"""
            {self.provider.logo}
            Ferramenta do pacote Cadmus para amostragem massiva de múltiplos rasters em pontos.
            {self.provider.transform_h('Objetivo')}
            Extrair valores de vários rasters em pontos.
            Gerar nova camada com valores amostrados.
            {self.provider.transform_alert('O nome do raster deve ser claro e único, pois será usado para nomear os campos de saída.')}
            {self.provider.transform_h('Como usar')}
            1. Abra a ferramenta.
            2. Selecione os pontos.
            3. Selecione os rasters.
            4. Defina CRS de saída, se necessário.
            5. Execute.
            {self.provider.transform_h('Saídas')}
            Nova camada de pontos com atributos adicionais de cada raster.
            {self.provider.transform_h('Atenções')}
            Valores fora da extensão retornam nulo.
            Diferenças de CRS podem impactar a precisão.
            {self.provider.author_info}
        """

    def get_attribute_statistics_help(self):
        return f"""
            {self.provider.logo}
            Ferramenta do pacote Cadmus para calcular estatísticas descritivas de atributos numéricos e exportar CSV.
            {self.provider.transform_h('Objetivo')}
            Calcular média, mediana, desvio padrão, percentis e outras estatísticas.
            Exportar resultados para CSV.
            {self.provider.transform_h('Como usar')}
            1. Abra a ferramenta.
            2. Selecione a camada de entrada.
            3. Defina campos a excluir, se necessário.
            4. Ajuste a precisão decimal.
            5. Escolha as estatísticas desejadas.
            6. Configure a saída e execute.
            {self.provider.transform_h('Saídas')}
            Arquivo CSV com uma linha por campo analisado.
            {self.provider.transform_h('Atenções')}
            Apenas campos numéricos são considerados.
            Valores nulos são ignorados.
            {self.provider.author_info}
        """
