# -*- coding: utf-8 -*-
"""ATUALIZE SOMENTE ESSE ARQUIVO, NAO TRADUZA PARA OS DEMAIS IDIOMAS NAO """


class Strings_pt_BR:
    """ "Strings for Brazilian Portuguese (pt-BR)"""

    # General
    APP_NAME = "Cadmus"
    PLUGIN_LANGUAGE = "Idioma do Plugin"

    # Theme
    THEME = "Tema"
    THEME_DESC = "Tema visual do Cadmus. Deixe em branco para usar o tema padrão"

    # About
    ABOUT_CADMUS = "Sobre o Cadmus"
    VERSION = "Versão"
    UPDATED_ON = "Atualizada em"
    CREATED_ON = "Criado em"
    CREATOR = "Criador"
    LOCATION = "Local"

    # Buttons
    CLOSE = "Fechar"
    SAVE = "Salvar"
    LOAD_FILES = "Carregar Arquivos"
    EXPORT = "Exportar"
    CANCEL = "Cancelar"
    OK = "OK"
    EXECUTE = "Executar"
    COPIED = "Copiado"
    COPY = "Copiar"
    COPY_VALUE_TO_CLIPBOARD = (
        "Copia o valor exibido para a área de transferência."
    )
    SELECT = "Selecionar"
    REMOVE = "Remover"
    INVERT = "Inverter"
    SELECT_ALL = "Selecionar Todos"
    DESELECT_ALL = "Desselecionar Todos"
    ENABLE = "Ativar"
    INFO = "Info"
    INSTRUCTIONS = "Instruções"
    AUTO_DETECT = "Auto-detectar"
    PROJECTS_DEFAULT_FOLDER = "Pasta padrão de projetos"
    OPEN_SETTINGS = "Abrir Configurações"

    # Tooltips internos dos widgets reutilizáveis
    CLOSE_WINDOW_WITHOUT_EXECUTING = (
        "Fecha esta janela sem executar a ferramenta."
    )
    OPEN_SETTINGS_PANEL = (
        "Abre as configurações do Cadmus para ajustar preferências gerais."
    )
    OPEN_TOOL_INSTRUCTIONS = (
        "Abre as instruções da ferramenta e mostra como usá-la."
    )
    SELECT_ALL_LIST = "Marca todas as opções da lista."
    DESELECT_ALL_LIST = "Desmarca todas as opções da lista."
    INVERT_LIST_SELECTION = (
        "Inverte a marcação: marca as opções desmarcadas e desmarca as marcadas."
    )
    LOCK_FIELD = (
        "Campo desbloqueado: clique para bloqueá-lo e impedir alterações."
    )
    UNLOCK_FIELD = (
        "Campo bloqueado: clique para desbloqueá-lo e permitir alterações."
    )
    CHOOSE_FILE = (
        "Seleciona um arquivo para usar na ferramenta."
    )
    CHOOSE_FILES = (
        "Seleciona um ou mais arquivos para usar na ferramenta."
    )
    CHOOSE_FOLDER = (
        "Seleciona uma pasta para usar na ferramenta."
    )
    CHOOSE_FOLDERS = (
        "Seleciona uma ou mais pastas para usar na ferramenta."
    )
    CHOOSE_LAYER = (
        "Alterna para selecionar uma camada carregada no QGIS."
    )
    USE_SOURCE_FOLDER = (
        "Usa a mesma pasta da origem para montar o caminho de saída."
    )
    SUGGEST_PROJECT_FOLDER = (
        "Usa a pasta do projeto como sugestão para o caminho de saída."
    )
    OPEN_LOCATION = (
        "Abre a localização atual no Explorador de Arquivos."
    )
    COPY_PATH = (
        "Copia o caminho atual para a área de transferência."
    )
    CONFIRM_SELECTION = (
        "Confirma a seleção atual e fecha esta janela."
    )

    # Common labels
    PRECISION = "Precisao"
    CONTINUE_ANYWAY = "Continuar mesmo assim"
    MENU_SYSTEM = "Sistema"
    MENU_LAYOUTS = "Layouts"
    MENU_FOLDER = "Pasta"
    MENU_VECTOR = "Vetor"
    MENU_AGRICULTURE = "Agricultura"
    MENU_RASTER = "Raster"
    MENU_DEVELOPER = "Developer"
    OPTIONS = "Opções"
    OPTIONS_SECTION_TITLE = "Opções"
    SAVING = "Salvamento"
    STYLES = "Estilos"
    WARNING = "Aviso"
    ERROR = "Erro"
    ADVANCED_PARAMETERS = "Parâmetros Avançados"
    APP_PREFERENCES = "Preferências do Aplicativo"
    OPEN_PREFERENCES_FOLDER = "Abrir Pasta de Preferências"
    FILE_TYPES = "Tipos de Arquivo"
    ROOT_FOLDER = "Pasta raiz:"
    OUTPUT_FOLDER = "Pasta de saída:"
    INPUT_LINE_LAYER = "Linhas:"
    SOURCE_LAYER = "Camada de Origem:"
    TARGET_LAYER = "Camada de Destino:"
    RANGE = "Intervalo"
    IMPLEMENT_SIZE = "Tamanho implemento: (sempre em metros)"
    VECTOR_CALCULATION_METHOD = "Método de Cálculo Vetorial"
    VECTOR_FIELDS_PRECISION = "Precisão de campos vetoriais (casas decimais):"
    ASYNC_THRESHOLD = "Limiar assíncrono (nº de feições):"
    CALCULATION_METHOD_LABEL = "Método de cálculo vetorial:"
    SEARCH_TEXT = "Texto a buscar:"
    REPLACE_WITH_NEW_TEXT = "Texto a substituir:"
    SOURCE_LAYER_ATTRIBUTES = "Atributos da camada origem"
    ATTRIBUTES = "Atributos"
    USE_ALL_ATTRIBUTES = "Usar todos os atributos"
    EXPORT_OPTIONS = "Opções de Exportação"
    MAX_WIDTH_PNG = "Max Width para PNG (px):"
    DPI_OUTPUT = "DPI de saída:"
    DPI_OUTPUT_DESC = (
        "Define a resolução dos arquivos exportados em pontos por polegada (DPI).\n"
        "Use 0 para manter o DPI configurado em cada layout.\n"
        "Valores maiores podem gerar arquivos mais detalhados e maiores."
    )
    USE_PROJECT_FOLDER = "Usar pasta do projeto"
    EXPORT_PDF = "Exportar PDF"
    EXPORT_PNG = "Exportar PNG"
    EXPORT_SVG = "Exportar SVG"
    GEOREFERENCE_PDF = "PDF com geolocalização"
    GEOREFERENCE_PDF_DESC = (
        "Adiciona a localização do mapa ao PDF exportado.\n"
        "Assim, softwares GIS podem posicionar o PDF corretamente sobre o mapa."
    )
    MERGE_PDFS_FINAL = "Unir PDFs em PDF final"
    MERGE_PNGS_FINAL = "Unir PNGs em PDF final"
    REPLACE_EXISTING_FILES = "Substituir arquivos existentes"
    WGS84_EPSG4326 = "WGS 84 (EPSG:4326)"
    UTM_SIRGAS_2000 = "UTM SIRGAS 2000"
    ALTIMETRY_OPENTOPO = "Altimetria (OpenTopoData)"
    APPROX_ALTITUDE_METERS = "Altitude aproximada (m)"
    LATITUDE_DECIMAL = "Latitude (Decimal)"
    LONGITUDE_DECIMAL = "Longitude (Decimal)"
    LATITUDE_DMS = "Latitude (DMS)"
    LONGITUDE_DMS = "Longitude (DMS)"
    EASTING_X = "Easting (X)"
    NORTHING_Y = "Northing (Y)"
    WGS84_COORDINATES_DESC = (
        "Mostra o ponto no sistema geográfico WGS 84 (EPSG:4326), "
        "usado como referência global de latitude e longitude."
    )
    LATITUDE_DECIMAL_DESC = (
        "Latitude em graus decimais: indica a posição norte-sul do ponto. "
        "Valores negativos ficam ao sul do Equador."
    )
    LONGITUDE_DECIMAL_DESC = (
        "Longitude em graus decimais: indica a posição leste-oeste do ponto. "
        "Valores negativos ficam a oeste do meridiano de Greenwich."
    )
    LATITUDE_DMS_DESC = (
        "Latitude no formato graus, minutos e segundos (DMS). "
        "É a mesma latitude decimal, apenas escrita em formato mais tradicional."
    )
    LONGITUDE_DMS_DESC = (
        "Longitude no formato graus, minutos e segundos (DMS). "
        "É a mesma longitude decimal, apenas escrita em formato mais tradicional."
    )
    UTM_COORDINATES_DESC = (
        "Mostra o ponto em coordenadas projetadas UTM no datum SIRGAS 2000. "
        "Os valores dependem da zona UTM do ponto."
    )
    EASTING_X_DESC = (
        "Easting (X) é a distância, em metros, em relação ao eixo leste-oeste "
        "da zona UTM."
    )
    NORTHING_Y_DESC = (
        "Northing (Y) é a distância, em metros, em relação ao Equador "
        "no sistema UTM."
    )
    UTM_REFERENCE_DESC = (
        "Informa o EPSG, a zona UTM e o hemisfério usados para calcular "
        "as coordenadas projetadas do ponto."
    )
    ALTIMETRY_OPENTOPO_DESC = (
        "A altitude é consultada no serviço OpenTopoData usando o modelo "
        "SRTM 90 m; o resultado é uma estimativa e depende da disponibilidade do serviço."
    )
    APPROX_ALTITUDE_DESC = (
        "Altitude aproximada do ponto obtida por consulta ao OpenTopoData/SRTM 90 m. "
        "Não é uma leitura direta do aparelho no momento do clique."
    )
    ADDRESS_OSM = "Endereço (OSM):"
    COPY_WGS84_FULL = "Copiar WGS 84 (Completo)"
    COPY_UTM_FULL = "Copiar UTM (Completo)"
    COPY_LOCATION_FULL = "Copiar Localização (Completo)"
    POINT_COORDINATES = "Coordenadas do Ponto"
    ZONE = "Zona"
    HEMISPHERE = "Hemisfério"
    CITY = "Município"
    FILE_NOT_FOUND = "Arquivo não encontrado"
    INTERMEDIATE_REGION = "Região Intermediária"
    STATE = "Estado"
    REGION = "Região"
    COUNTRY = "País"
    MUNICIPALITY_DESC = (
        "Município identificado pelo serviço BigDataCloud de geocodificação reversa "
        "a partir das coordenadas do ponto."
    )
    INTERMEDIATE_REGION_DESC = (
        "Região intermediária identificada pelo serviço BigDataCloud de geocodificação reversa."
    )
    STATE_DESC = (
        "Estado identificado pelo serviço BigDataCloud de geocodificação reversa "
        "a partir das coordenadas do ponto."
    )
    REGION_DESC = (
        "Região ou estado maior identificado pelo serviço BigDataCloud de geocodificação reversa."
    )
    COUNTRY_DESC = (
        "País identificado pelo serviço BigDataCloud de geocodificação reversa "
        "a partir das coordenadas do ponto."
    )
    LOADING = "Carregando..."
    LOADING_LOWER = "carregando..."
    UNAVAILABLE = "Indisponível"
    NO_PATH_SELECTED = "Nenhum caminho selecionado"
    FILES_SELECTED = "arquivo(s) selecionado(s)"
    ITEMS_SELECTED = "item(s)"
    ONLY_SELECTED_FEATURES = "Somente feições selecionadas"
    ONLY_SELECTED_FEATURES_DESC = (
        "Limita o processamento às feições marcadas na camada; "
        "sem marcação, a camada inteira é considerada."
    )
    APPLY_QML_STYLE = "Aplicar estilo QML"
    QML_LABEL = "QML:"
    SAVE_TO_FILE = "Salvar em arquivo:"
    SELECT_PATH = "Selecionar Caminho"
    BUTTON = "Botão"
    SAVE_FILE = "Salvar arquivo"
    SELECT_FILE = "Selecionar arquivo"
    POINTS = "Pontos"
    TRACK = "Rastro"

    # Common option labels
    CASE_SENSITIVE = "Diferenciar maiúsculas/minúsculas"
    FULL_LABEL_REPLACE = "Substituir o label inteiro quando encontrar o texto"
    LOAD_ONLY_MISSING_FILES = "Carregar apenas arquivos ainda NÃO carregados no projeto"
    PRESERVE_FOLDER_STRUCTURE = "Criar grupos conforme estrutura de pastas/subpastas"
    DO_NOT_GROUP_LAST_FOLDER = "Não agrupar a última pasta"
    CREATE_PROJECT_BACKUP_IF_SAVED = (
        "Criar backup do projeto antes de carregar (somente se salvo)"
    )
    ROOT_FOLDER_DESC = (
        "Escolha a pasta onde o Cadmus deve procurar arquivos para carregar no projeto."
    )
    LOAD_ONLY_MISSING_FILES_DESC = (
        "Quando marcado, ignora os arquivos que já estão carregados no projeto."
    )
    PRESERVE_FOLDER_STRUCTURE_DESC = (
        "Cria grupos no painel de camadas seguindo as pastas e subpastas encontradas."
    )
    DO_NOT_GROUP_LAST_FOLDER_DESC = (
        "Quando marcado, não cria um grupo para o último nível da pasta encontrada."
    )
    CREATE_PROJECT_BACKUP_IF_SAVED_DESC = (
        "Antes de carregar os arquivos, cria uma cópia do projeto atual se ele já estiver salvo."
    )
    FILE_TYPE_SELECTION_DESC = (
        "Marque para incluir arquivos deste formato na busca pela pasta selecionada."
    )
    START_LOADING_FOLDER_FILES = (
        "Procura os formatos marcados na pasta escolhida e adiciona os arquivos encontrados ao projeto."
    )

    # Common messages
    SUCCESS_MESSAGE = "Processamento executado com sucesso."
    ERROR_LAYER_NOT_FOUND = "Erro: Camada não encontrada."
    SELECT_VALID_FOLDER = "Selecione uma pasta válida."
    SELECT_AT_LEAST_ONE_FILE_TYPE = "Selecione pelo menos um tipo de arquivo."
    SELECT_AT_LEAST_ONE_EXPORT_FORMAT = "Selecione pelo menos um formato (PDF ou PNG)"
    SELECT_VALID_LINE_LAYER = "Selecione uma camada de linhas válida."
    INVALID_SOURCE_LAYER = "Camada de origem inválida"
    INVALID_TARGET_LAYER = "Camada de destino inválida"
    INVALID_INPUT_LAYER = "Camada de entrada inválida."
    FINAL_LAYER_NOT_FOUND = "Erro: camada final não encontrada no contexto."
    BUFFER_CANNOT_BE_ZERO = "Buffer não pode ser 0"
    ASYNC_STARTED = "Execução em background iniciada. Verifique o log para progresso."
    ASYNC_START_ERROR = "Erro iniciando execução assíncrona:"
    ASYNC_FINISHED = "Execução assíncrona concluída."
    ASYNC_EXECUTION_ERROR = "Erro na execução assíncrona:"
    FILES_LOADED_PREFIX = "Foram carregados"
    FILES_SUFFIX = "arquivos."
    SETTINGS_SAVED_TITLE = "Configurações Salvas"
    SETTINGS_SAVED_MESSAGE = "As configurações foram salvas com sucesso."
    PREFERENCES_FOLDER_NOT_FOUND = "Pasta de preferências não encontrada:"
    ENTER_TEXT_TO_SEARCH = "Informe o texto a buscar."
    CONFIRM_REPLACEMENTS = "Confirme substituições"
    SEARCH_LABEL = "Buscar:"
    REPLACE_WITH_LABEL = "Substituir por:"
    DESTRUCTIVE_OPERATION_WARNING = "Atenção - operação destrutiva"
    LAYOUTS_ANALYZED = "Layouts analisados:"
    CHANGES_APPLIED = "Substituições aplicadas:"
    REPLACEMENT_COMPLETED_TITLE = "Substituição concluída"
    PROJECT_BACKUP_INFO = "Backup: será criada uma cópia do projeto (.qgz) na pasta backup ao lado do arquivo do projeto."
    LAYER_MUST_BE_EDITABLE = "A camada precisa estar em edição"
    NO_ATTRIBUTE_SELECTED = "Nenhum atributo selecionado"
    ATTRIBUTES_COPIED_SUCCESS = "Atributos copiados com sucesso (alterações não salvas)"
    REQUIRED_LIBRARY = "Biblioteca necessária"
    PYPDF2_REQUIRED_MESSAGE = "Para unir PDFs é necessário instalar o pacote PyPDF2.\n\nDeseja instalar agora?"
    PILLOW_REQUIRED_MESSAGE = "Para unir PNGs em PDF é necessário instalar o pacote Pillow.\n\nDeseja instalar agora?"
    EXPORTING_LAYOUTS = "Exportando layouts..."
    FAILED_EXPORT_PDF = "Falha ao exportar PDF:"
    FAILED_EXPORT_PNG = "Falha ao exportar PNG:"
    ERROR_EXPORTING = "Erro exportando"
    FAILED_MERGE_PDFS = "Falha ao unir PDFs:"
    FAILED_MERGE_PNGS = "Falha ao unir PNGs:"
    ERRORS_FOUND = "Erros encontrados:"
    LAYOUTS_EXPORTED_SUCCESS = "layout(s) exportado(s) com sucesso!"
    PDFS_MERGED = "PDFs unidos"
    PNGS_MERGED = "PNGs unidos"
    EXPORT_LAYOUTS_COMPLETED = "Exportação de Layouts Concluída"
    LOCATION_COPIED_TO_CLIPBOARD = "Localização copiada para a área de transferência"
    ADDRESS_COPIED_TO_CLIPBOARD = "Endereço copiado para a área de transferência"

    SELECT_VECTOR_LAYER = "Selecione uma camada vetorial"
    SELECT_EDITABLE_VECTOR_LAYER = "Selecione uma camada vetorial editável"
    LAYER_HAS_NO_FEATURES = "A camada não possui feições"
    OPERATION_CANCELLED_BY_USER = "Operação cancelada pelo usuário"
    GEOMETRY_TYPE_NOT_SUPPORTED = "Tipo de geometria não suportado"
    ERROR_IN_PREPARATION = "Erro na preparação:"
    KML_FILES_ARE_NOT_EDITABLE = "Arquivos KML não são editáveis."
    CONVERT_LAYER_TO_GPKG_OR_SHP_BEFORE_USING = "Converta a camada para GeoPackage (.gpkg) ou Shapefile (.shp) antes de usar esta ferramenta."
    LAYER_USES_GEOGRAPHIC_CRS = "Camada usa CRS Geográfico"
    CARTESIAN_MODE_RESULTS_IN_DEGREES2 = (
        "Modo 'Cartesiano' resultaria em valores em graus²."
    )
    CALCULATING_BOTH_MODES_AUTOMATICALLY = "Calculando ambos os modos automaticamente."
    XY_FIELDS_CALCULATED_SUCCESS = "Campos X/Y calculados com sucesso"
    LINE_LENGTH_CALCULATED_SUCCESS = "Comprimento de linhas calculado com sucesso"
    POLYGON_AREA_CALCULATED_SUCCESS = "Área de polígonos calculada com sucesso"
    ERROR_STARTING_CALCULATION = "Erro ao iniciar cálculo:"
    UNKNOWN_ERROR = "Erro desconhecido"
    CALCULATION_FAILED = "Falha no cálculo:"
    GEOMETRIES_CONVERTED_TO_MULTIPART_NOT_SAVED = (
        "Geometrias convertidas para multipart (não salvas)"
    )
    CONVERT_SELECTED_FEATURES_TO_MULTIPART = (
        "Converter apenas as feições selecionadas para multipart?"
    )
    CONVERT_ALL_FEATURES_TO_MULTIPART = "Converter todas as feições para multipart?"

    # Dependencies
    INSTALLING_DEPENDENCY = "Instalando dependência..."
    INSTALLING_DEPENDENCIES = "Instalando dependências"
    DEPENDENCY = "Dependência"
    INSTALLED_SUCCESSFULLY = "instalada com sucesso."
    SUCCESS = "Sucesso"
    INSTALL_DEPENDENCY_FAILED = "Falha ao iniciar a instalação da biblioteca."
    KML_FIELDS_REMOVED_SUCCESS = "Campos KML removidos com sucesso"
    NO_KML_FIELDS_FOUND = "Nenhum campo KML encontrado para remover"
    ERROR_REMOVING_KML_FIELDS = "Erro ao remover campos KML:"

    RASTERS = "Rasters"
    INPUT_POINTS = "Pontos de entrada"
    REPROJECT_OUTPUT_LAYER_OPTIONAL = "Reprojetar camada de saída (opcional)"
    SAMPLED_VALUES = "Valores_Amostrados"
    OPEN_OUTPUT_FOLDER = "Abrir pasta de saída"
    DISPLAY_HELP_FIELD = "Exibir campo de ajuda (Necessario executar e reiniciar)"
    OUTPUT_CRS_LABEL = "CRS de saída:"
    NONE = "None"
    FILE_SAVED_IN = "Arquivo salvo em:"
    RASTER_MASS_SAMPLER_TITLE = "Amostragem Massiva de Rasters"
    RASTER_WEIGHTED_AVERAGE_TITLE = "Média Ponderada de Rasters"
    RASTER_MASS_CLIPPER_TITLE = "Recorte Massivo de Rasters"
    RASTER_MASK_CLIPPER_TITLE = "Recortar Raster por Máscara de Feições"
    SEPARATE_FEATURES = "Separar feições"
    RASTER_MASK_CLIPPER_TOOLTIP = (
        "Recorta um raster usando uma camada poligonal como máscara.\n"
        "Quando 'Separar feições' está marcado, gera um raster por feição\n"
        "usando o campo 'name' (quando existir) para nomear os arquivos,\n"
        "com suporte a prefixo e sufixo personalizados."
    )
    RASTER_MASS_SAMPLER_TOOLTIP = (
        "Executa amostragem em lote de vários rasters sobre uma camada vetorial de pontos.\n"
        "Lê o valor de cada raster na posição de cada ponto, acrescenta os valores\n"
        "à camada de saída e permite definir o CRS final no Processing."
    )
    POINT_LAYER_FOR_SAMPLING_DESC = (
        "Selecione a camada vetorial de pontos onde os valores dos rasters\n"
        "serão consultados."
    )
    RASTERS_FOR_SAMPLING_DESC = (
        "Selecione um ou mais rasters. Cada raster será amostrado na posição\n"
        "de cada ponto e terá um campo correspondente na camada de saída."
    )
    SAMPLED_VALUES_OUTPUT_DESC = (
        "Escolha o destino da camada de pontos com os atributos originais\n"
        "e os valores amostrados dos rasters."
    )
    RASTER_MASS_CLIPPER_TOOLTIP = (
        "Recorta em lote vários rasters usando uma camada poligonal como máscara.\n"
        "Permite aplicar o recorte à camada inteira ou gerar uma saída por feição,\n"
        "aplicar uma correção de borda e escolher a pasta de saída no Processing."
    )
    POLYGON_MASK_INPUT_DESC = (
        "Selecione a camada vetorial de polígonos usada como máscara do recorte."
    )
    INPUT_RASTERS_DESC = (
        "Selecione um ou mais rasters que serão recortados pela camada máscara."
    )
    CLIP_PER_EACH_POLYGON_DESC = (
        "Quando marcado, gera um raster separado para cada polígono; desmarcado, "
        "gera um raster usando a camada máscara inteira."
    )
    CORRECTION_BUFFER_DESC = (
        "Amplia levemente a máscara usando 1,1 vez o tamanho do pixel para reduzir "
        "bordas sem dados no recorte."
    )
    OPEN_OUTPUT_FOLDER_DESC = (
        "Quando marcado, abre a pasta de saída no Explorador ao terminar o "
        "processamento."
    )
    DISPLAY_HELP_DESC = (
        "Quando marcado, exibe as instruções da ferramenta no painel de ajuda do "
        "Processing."
    )
    RASTER_DIFFERENCE_STATISTICS_TITLE = "Processar Diferença de Rasters"
    INPUT_MASK_POLYGON_LAYER = "Camada máscara (polígono)"
    CLIP_PER_EACH_POLYGON = "Recortar por cada polígono"
    APPLY_CORRECTION_BUFFER_PIXEL_1_1 = "Aplicar buffer de correção (pixel * 1.1)"
    RASTER_FOLDER_OR_SELECT_RASTER_LAYERS = (
        "Pasta de rasters ou selecione camadas raster"
    )
    QGIS_RASTER_LAYERS_OR_SELECT_RASTER_FOLDER = (
        "Camadas de raster QGIS ou selecione pasta de rasters"
    )
    OUTPUT_FOLDER_FOR_GENERATED_RASTERS = "Pasta de saída para rasters gerados"
    NO_OUTPUT_FOLDER_PROVIDED_USING_TEMP = (
        "Nenhuma pasta de saída informada. Usando temporária:"
    )
    INVALID_FOLDER = "Pasta inválida"
    NO_RASTER_FOUND_IN_SPECIFIED_FOLDER = (
        "Nenhum raster encontrado na pasta especificada."
    )
    INVALID_RASTER_IGNORED = "Raster inválido ignorado"
    PROCESSING_RASTER_DIFFERENCE_BY_FOLDER_OR_LAYERS = (
        "Processando diferença de rasters por pasta/camadas..."
    )
    INFORM_RASTER_FOLDER_OR_SELECT_LAYER = (
        "Informe uma pasta de rasters ou selecione ao menos uma camada raster."
    )
    AT_LEAST_2_RASTERS_REQUIRED = (
        "É necessário ao menos 2 rasters para calcular diferenças."
    )
    FOUND_RASTER_COMBINATIONS_FOR_DIFFERENCE = (
        "Encontradas combinações de rasters para diferenciação:"
    )
    PROCESSING = "Processando"
    NO_OVERLAP_BETWEEN = "Sem sobreposição entre"
    AND = "e"
    SKIPPING = "Pulando"
    CALCULATION_ERROR_FOR = "Erro no cálculo para"
    DIFFERENCE_RASTER_CREATED = "Raster diferença criado:"
    STATS_GENERATED_FOR = "Stats gerados para"
    FAILED_TO_GENERATE_STATS_FOR = "Falha ao gerar stats para"
    CONSOLIDATED_REPORT_GENERATED = "Relatório consolidado gerado:"
    DIFFERENCE_STATISTICS_SUMMARY_TITLE = (
        "Resumo de Estatísticas de Diferença de Rasters"
    )
    TOTAL_PROCESSED_PAIRS = "Total de pares processados:"
    RASTER = "Raster"
    STATISTICS = "Estatísticas"
    VECTOR = "Vetor"
    INTERVAL = "Intervalo"
    GEOMETRY_LINE_FROM_POINTS_TITLE = "Linha de Diferença entre Pontos"
    POINT_LAYER_MODE1_FIRST_LAYER_MODE2 = (
        "Camada de Pontos (Modo 1) / Primeira Camada (Modo 2)"
    )
    BASE_ATTRIBUTE_LAYER_A = "Atributo base - camada A"
    USE_SECOND_LAYER_MODE2 = "Usar segunda camada (modo 2)"
    SECOND_POINT_LAYER_MODE2_OPTIONAL = "Segunda Camada de Pontos (Modo 2 - opcional)"
    BASE_ATTRIBUTE_LAYER_B_MODE2 = "Atributo base - camada B (modo 2)"
    DIFFERENCE_LINES = "Linhas de diferenças"
    INVALID_LAYER_A = "Camada A inválida."
    MODE2_REQUIRES_SECOND_POINT_LAYER = "Modo 2 requisita uma segunda camada de pontos."
    MODE2_INFORM_GROUP_FIELD_LAYER_B = (
        "No modo 2 informe o campo de agrupamento da camada B."
    )
    ERROR_CREATING_OUTPUT_LAYER = "Erro ao criar camada de saída."
    PROCESS_COMPLETED_LINES_GENERATED_SUCCESS = (
        "Processo concluído: linhas geradas com sucesso."
    )
    GRID_GENERATOR_TITLE = "Gerador de Grade"
    GRID_GENERATOR_INPUT_LAYER = "Camada de Entrada (Polígono)"
    HORIZONTAL_SPACING = "Espaçamento Horizontal"
    VERTICAL_SPACING = "Espaçamento Vertical"
    GRID_TYPE = "Tipo de Grade"
    OUTPUT_GRID = "Grade de Saída"
    VERBOSE_LOG = "Log Detalhado"
    ATTRIBUTE_STATISTICS_TITLE = "Estatísticas de Atributos"
    INPUT_LAYER = "Camada de entrada"
    EXCLUDE_FIELDS_OPTIONAL = "Campos a excluir (opcional)"
    PRECISION_DECIMAL_PLACES = "Precisão (casas decimais)"
    LOAD_CSV_AUTOMATICALLY_AFTER_EXECUTION = (
        "Carregar CSV automaticamente após execução"
    )
    FORCE_CSV_PTBR_FORMAT = "Forçar CSV no formato PT-BR (usar ; e ,)"
    CALCULATE = "Calcular"
    OUTPUT_CSV_FILE = "Arquivo CSV de saída"
    INVALID_LAYER = "Camada inválida."
    NO_NUMERIC_FIELD_FOUND = "Nenhum campo numérico encontrado."
    FIELD = "Campo"
    COUNT = "Contagem"
    ERROR_SAVING_CSV = "Erro ao salvar CSV:"
    FILE_LOADED_AS_LAYER = "Arquivo carregado como camada:"
    CSV_FILE_GENERATED = "Arquivo CSV gerado:"
    MEAN = "Media"
    MEAN_ABSOLUTE = "Media Absoluta"
    STD_POP = "Desvio Padrao (Pop.)"
    STD_SAMPLE = "Desvio Padrao (Amostra)"
    MINIMUM = "Minimo"
    MAXIMUM = "Maximo"
    MEDIAN = "Mediana"
    PERCENTILE_5 = "Percentil 5%"
    PERCENTILE_95 = "Percentil 95%"
    MODE = "Moda"
    VARIANCE = "Variancia"
    SUM = "Soma"
    COEFFICIENT_OF_VARIATION = "Coeficiente de Variação"
    SKEWNESS = "Assimetria"
    KURTOSIS = "Curtose"
    DIFFERENCE_FIELDS_TITLE = "Gerador de Diferenças entre Campos"
    POINT_LAYER = "Camada de Pontos"
    BASE_FIELD_SUBTRAHEND = "Campo Base (subtraendo)"
    FIELDS_TO_EXCLUDE_FROM_CALCULATION = "Campos a EXCLUIR do cálculo"
    PREFIX_FOR_NEW_FIELDS = "Prefixo para novos campos"
    DIFFERENCE = "Diferenca"
    NO_EXCLUDED_FIELD_USING_ALL_NUMERIC = (
        "Nenhum campo excluído → usando todos os campos numéricos."
    )
    BASE = "Base"
    EXCLUDED_FIELDS = "Campos EXCLUÍDOS"
    FIELDS_USED_IN_CALCULATION = "Campos utilizados no cálculo"
    PREFIX = "Prefixo"
    PROCESS_FINISHED_SUCCESS = "Processo finalizado com sucesso."

    # plugins/DeveloperTestTool.py
    DEVELOPER_TEST_TOOL_TITLE = "Developer Test Tool"
    DEVELOPER_TEST_TOOL_TOOLTIP = (
        "Ferramenta oficial de testes do Cadmus.\n"
        "Permite testar widgets, componentes e demais\n"
        "recursos do sistema em um ambiente controlado."
    )

    # plugins/DroneCoordinates.py
    DRONE_COORDINATES_TITLE = "DJI Coordenadas de Drone"
    DRONE_COORDINATES_TOOLTIP = (
        "Processa arquivos MRK do voo para gerar a camada de pontos e o rastro.\n"
        "Permite cruzar os registros com metadados das imagens, escolher os campos,\n"
        "salvar as saídas vetoriais, aplicar estilos QML e gerar um relatório HTML."
    )
    RECURSIVE_SEARCH = "Vasculhar subpastas"
    RECURSIVE_SEARCH_DESC = (
        "Quando marcado, procura arquivos relacionados também dentro das subpastas\n"
        "da pasta selecionada."
    )
    USE_MRK_DATA = "Obter dados MRK"
    USE_MRK_DATA_DESC = (
        "Usa os atributos dos arquivos MRK para complementar os registros do voo.\n"
        "Desmarque para processar somente os metadados das fotos."
    )
    PHOTOS_METADATA = "Cruzar com metadados das fotos"
    PHOTOS_METADATA_DESC = (
        "Extrai e cruza dados EXIF, XMP e campos derivados das imagens encontradas.\n"
        "Essa opção requer a biblioteca Pillow."
    )
    PHOTOS_METADATA_REQUIRED_MESSAGE = "Para cruzar com metadados das fotos é necessário instalar o pacote Pillow.\n\nDeseja instalar agora?"
    GENERATE_REPORT = "Gerar relatório"
    GENERATE_REPORT_DESC = (
        "Gera um relatório HTML com as informações de metadata do voo ao final\n"
        "do processamento."
    )
    MRK_FOLDER = "Pasta MRK:"
    MRK_FOLDER_DESC = (
        "Selecione a pasta que contém os arquivos MRK e, quando necessário,\n"
        "as fotos relacionadas ao voo."
    )
    DRONE_OPTIONS_DESC = (
        "Reúne as opções que controlam a busca de arquivos, o enriquecimento\n"
        "dos registros e a geração do relatório."
    )
    LOGO_DESC = (
        "Selecione um arquivo de logotipo opcional para identificar o projeto\n"
        "nos resultados e no relatório."
    )
    PROJECT_TITLE_DESC = (
        "Informe o título que identifica o projeto ou o voo nos resultados\n"
        "gerados pela ferramenta."
    )
    EXIF_FIELDS = "Campos EXIF"
    EXIF_FIELDS_DESC = (
        "Selecione os campos EXIF das imagens que devem ser incluídos\n"
        "na camada de pontos gerada."
    )
    DJI_FIELDS = "Campos DJI"
    DJI_FIELDS_DESC = (
        "Selecione os campos XMP específicos do DJI que devem ser incluídos\n"
        "na camada de pontos gerada."
    )
    CUSTOM_FIELDS = "Campos personalizados"
    CUSTOM_FIELDS_DESC = (
        "Selecione os campos derivados calculados a partir dos metadados\n"
        "das imagens para incluí-los na camada de pontos."
    )
    INITIAL_FIELDS = "Campos iniciais"
    INITIAL_FIELDS_DESC = (
        "Reúne os campos básicos de identificação e posição disponíveis\n"
        "no catálogo de metadata do voo."
    )
    MRK_FIELDS = "Campos MRK"
    MRK_FIELDS_DESC = (
        "Selecione os atributos de contexto lidos dos arquivos MRK\n"
        "para incluí-los na camada de pontos."
    )
    SAVE_POINTS_CHECKBOX = "Salvar pontos MRK em arquivo?"
    SAVE_IN = "Salvar em:"
    SAVE_TRACK_CHECKBOX = "Salvar rastro em arquivo?"
    USE_LOGO = "Usar logotipo?"
    LOGO_LABEL = "Logotipo:"
    PROJECT_TITLE = "Título do Projeto"
    PROJECT_TITLE_HINT = "Ex: Fazenda Esperança"
    APPLY_STYLE_POINTS = "Aplicar estilo (QML) nos pontos?"
    QML_POINTS = "QML pontos:"
    APPLY_STYLE_TRACK = "Aplicar estilo (QML) no rastro?"
    QML_TRACK = "QML:"
    STYLES_DESC = (
        "Defina arquivos QML opcionais para personalizar as camadas\n"
        "de pontos e rastro geradas."
    )
    START_DRONE_COORDINATES_DESC = (
        "Inicia o processamento dos arquivos, a criação das camadas\n"
        "e as saídas opcionais configuradas acima."
    )
    MRK_DROP_START = "Arquivo MRK detectado. Iniciando conversao."
    CONVERT_FILE_SUCCESS = "Arquivo convertido com sucesso."
    LOADED_EXISTING_GPKG = "Saidas GPKG existentes carregadas com sucesso."
    CONVERT_FILE_ERROR = "Falha ao converter arquivo."
    REPORT_METADATA_TITLE = "Relatorio de Metadata"
    REPORT_METADATA_TOOLTIP = (
        "Lista os JSONs temporários de metadata gerados pelo Cadmus e permite "
        "regenerar o relatório HTML.\n"
        "Também permite vetorizar o voo selecionado e abrir as pastas de JSONs e "
        "relatórios."
    )
    REFRESH_JSON_LIST = "Atualizar JSON"
    OPEN_REPORTS_FOLDER = "Abrir relatorios"
    OPEN_JSONS_FOLDER = "Abrir JSONs"
    JSON_METADATA_FILE_DESC = (
        "Selecione um JSON temporário de metadata para vetorizar o voo ou gerar "
        "novamente "
        "o relatório."
    )
    REFRESH_JSON_LIST_DESC = "Atualiza a lista de JSONs temporários disponíveis."
    OPEN_REPORTS_FOLDER_DESC = "Abre a pasta onde os relatórios HTML são gerados."
    OPEN_JSONS_FOLDER_DESC = "Abre a pasta onde os JSONs temporários são armazenados."
    REGENERATE_HTML_REPORT_DESC = (
        "Gera novamente o relatório HTML usando o JSON temporário selecionado."
    )
    VECTOR_WITHOUT_MRK_BLOCK_TITLE = "Gerar Vetor Sem MRK"
    VETORIZE_FLIGHT = "Vetorizar voo"
    VETORIZE_FLIGHT_TOOLTIP = (
        "Gera camada vetorial de pontos e rastro a partir do JSON de metadata selecionado.\n"
        "Equivalente a executar o pipeline de coordenadas de drone apenas com o JSON."
    )
    NO_JSON_FOUND = "Nenhum JSON temporario encontrado."

    # plugins/SettingsPlugin.py
    SETTINGS_TITLE = "Configurações Cadmus"
    SETTINGS_TOOLTIP = (
        "Abre as configurações do Cadmus.\n"
        "Aqui você define pasta de projetos, SRC padrão, idioma, tema,\n"
        "categorias visíveis e parâmetros dos cálculos vetoriais."
    )
    GENERAL = "Geral"
    DEFAULT_CRS = "SRC padrao"
    PROJECTS_FOLDER = "Pasta de projetos"
    TOOLBAR_VISIBLE_CATEGORIES = "Toolbar - Categorias Visiveis"
    VECTOR_CALCULATIONS_PLUGIN = "Plugin de Calculos Vetoriais"
    CARTESIAN_SUFFIX = "Sulfixo Cartesiano"
    ELLIPSOIDAL_SUFFIX = "Sulfixo Elipsoidal"
    AREA_SUFFIXES_CANNOT_MATCH = (
        "Os sulfixos cartesiano e elipsoidal nao podem ser iguais."
    )
    ELLIPSOIDAL = "Elipsoidal"
    CARTESIAN = "Cartesiana"
    BOTH = "Ambos"

    # Tooltips/descrições dos widgets do SettingsPlugin
    PROJECTS_FOLDER_DESC = (
        "Pasta raiz onde os projetos do Cadmus são criados e organizados.\n"
        "Usada como local padrão para novos projetos e para localizar\n"
        "arquivos de entrada/saída das ferramentas."
    )
    DEFAULT_CRS_DESC = (
        "Sistema de Referência de Coordenadas (SRC) padrão usado\n"
        "quando nenhum SRC é especificado. O WGS84 (EPSG:4326) é o padrão\n"
        "recomendado para dados geográficos globais."
    )
    PLUGIN_LANGUAGE_DESC = (
        "Idioma da interface do Cadmus.\n"
        "Escolha 'Auto-detectar' para usar o idioma do QGIS,\n"
        "ou selecione um idioma específico manualmente."
    )
    VECTOR_FIELDS_PRECISION_DESC = (
        "Número de casas decimais usadas nos campos vetoriais calculados\n"
        "(área, comprimento, coordenadas X/Y).\n"
        "Valores maiores aumentam a precisão, mas geram campos mais longos."
    )
    ASYNC_THRESHOLD_DESC = (
        "Número mínimo de feições para que o processamento seja executado\n"
        "em segundo plano (assíncrono). Camadas com menos feições que este\n"
        "limiar são processadas de forma síncrona (bloqueante)."
    )
    TOOLBAR_VISIBLE_CATEGORIES_DESC = (
        "Controla quais categorias de ferramentas aparecem na toolbar do Cadmus.\n"
        "Desmarque uma categoria para ocultar seus botões da toolbar."
    )
    VECTOR_CALCULATIONS_PLUGIN_DESC = (
        "Configurações do plugin de cálculo de campos vetoriais.\n"
        "Define o método de cálculo (elipsoidal/cartesiano), os sufixos\n"
        "dos campos de área e comprimento."
    )
    ASK_BEFORE_REPLACING_FIELDS = "Perguntar ao substituir campos existentes"
    ASK_BEFORE_REPLACING_FIELDS_DESC = (
        "Quando marcado, o Cadmus pergunta antes de substituir campos com nome\n"
        "já existente na camada durante o cálculo de campos vetoriais.\n"
        "Desmarque para substituir automaticamente sem perguntar."
    )
    ELLIPSOIDAL_DESC = (
        "Calcula áreas e comprimentos sobre a superfície curva do elipsoide\n"
        "da Terra (ex: WGS84). Ideal para camadas em SRC geográfico (lat/lon)\n"
        "como WGS84 (EPSG:4326). Resultados em metros/m² independente do SRC.\n"
        "Mais preciso para grandes áreas e altas latitudes."
    )
    CARTESIAN_DESC = (
        "Calcula áreas e comprimentos no plano cartesiano do SRC da camada.\n"
        "Ideal para SRC projetados como UTM, onde as unidades são metros.\n"
        "Rápido e simples, mas em SRC geográfico resultaria em graus/graus²\n"
        "(valores sem sentido físico)."
    )
    BOTH_DESC = (
        "Calcula ambos os métodos (elipsoidal e cartesiano) simultaneamente.\n"
        "Gera dois campos separados para cada métrica, usando os sufixos\n"
        "configurados abaixo. Útil para comparar resultados."
    )
    CARTESIAN_SUFFIX_DESC = (
        "Sufixo adicionado ao nome dos campos calculados em modo cartesiano.\n"
        "Ex: campo 'area' com sufixo '' vira 'area'.\n"
        "Deixe vazio para não adicionar sufixo."
    )
    CARTESIAN_SUFFIX_PLACEHOLDER = "Ex.: _cart"
    ELLIPSOIDAL_SUFFIX_DESC = (
        "Sufixo adicionado ao nome dos campos calculados em modo elipsoidal.\n"
        "Ex: campo 'area' com sufixo '_eli' vira 'area_eli'.\n"
        "O padrão é '_eli' para diferenciar dos campos cartesianos."
    )
    ELLIPSOIDAL_SUFFIX_PLACEHOLDER = "Ex.: _eli"
    SAVE_DESC = "Salva todas as configurações e fecha a janela."
    OPEN_PREFERENCES_FOLDER_DESC = (
        "Abre a pasta onde as preferências do Cadmus são armazenadas."
    )
    REG_TITLE_DESC = "Abre o gerenciador de licenças/registro do Cadmus."

    # plugins/ReplaceInLayouts.py
    REPLACE_IN_LAYOUTS_TITLE = "Substituir Texto em Layouts"
    REPLACE_IN_LAYOUTS_TOOLTIP = (
        "Procura textos nos labels dos layouts do projeto\n"
        "e substitui pelo novo valor informado.\n"
        "Pode fazer substituição parcial ou trocar o conteúdo\n"
        "inteiro do label quando houver correspondência."
    )
    ORIGINAL_TEXT_TO_REPLACE = (
        "Informe o texto que deve ser encontrado nos labels dos layouts."
    )
    SEARCH_TEXT_PLACEHOLDER = "Ex.: texto atual do layout"
    NEW_TEXT_TO_USE = (
        "Informe o texto que substituirá o conteúdo encontrado. "
        "Deixe vazio para apagar o texto encontrado."
    )
    REPLACEMENT_TEXT_PLACEHOLDER = "Ex.: texto novo do layout"
    CASE_SENSITIVE_SEARCH = (
        "Diferencia letras maiúsculas de minúsculas durante a busca. "
        "Exemplo: 'Mapa' e 'mapa' serão tratados como textos diferentes."
    )
    REPLACE_ENTIRE_LABEL = (
        "Substitui o label inteiro quando o texto for encontrado. "
        "Se desmarcado, substitui somente o trecho correspondente."
    )
    BACKUP_BEFORE_REPLACEMENT = (
        "Antes da alteração, cria uma cópia do projeto salvo na pasta de backup."
    )
    SWAP_TEXT_FIELDS = (
        "Troca o texto de busca pelo texto de substituição e vice-versa."
    )
    START_LAYOUT_REPLACEMENT = (
        "Procura o texto nos layouts e aplica a substituição conforme as opções escolhidas."
    )
    REPLACE_IN_LAYOUTS_SWAP = "Inverter"
    REPLACE_IN_LAYOUTS_RUN = "Executar"

    # plugins/LoadFolderLayers.py
    LOAD_FOLDER_LAYERS_TITLE = "Carregar Pasta de Arquivos"
    CREATE_PROJECT_TITLE = "Novo Projeto"
    CREATE_PROJECT = "Novo Projeto"
    CREATE_PROJECT_TOOLTIP = (
        "Cria um novo projeto QGIS em uma pasta própria.\n"
        "Se a pasta padrão ainda não estiver definida, pede para você escolhê-la.\n"
        "Depois solicita o nome do projeto e cria o arquivo .qgz\n"
        "com as subpastas de vetores e rasters."
    )
    DEFAULT_PROJECTS_FOLDER_TITLE = "Pasta padrao dos projetos"
    DEFAULT_PROJECTS_FOLDER_PROMPT = (
        "Escolha a pasta padrão onde o Cadmus deverá criar os novos projetos."
    )
    PROJECT_NAME_TITLE = "Novo projeto"
    PROJECT_NAME_PROMPT = (
        "Informe o nome do novo projeto. Se deixar em branco, será usado o nome sugerido."
    )
    CREATE_PROJECT_IN_CONFIGURED_FOLDER = (
        "Confirma o nome informado e cria o projeto na pasta padrão escolhida."
    )
    CONFIRM_DEFAULT_PROJECTS_FOLDER = (
        "Confirma a pasta onde os novos projetos serão criados."
    )
    PROJECT_NAME_LABEL = "Nome do projeto"
    PROJECTS_DEFAULT_FOLDER_MISSING = (
        "Nenhuma pasta padrao para projetos foi definida.\n\n"
        "Deseja definir uma pasta padrao agora?"
    )
    PROJECTS_DEFAULT_FOLDER_MISSING_TITLE = "Pasta padrao nao definida"
    PROJECT_FOLDER_ALREADY_EXISTS = "A pasta do projeto ja existe:"
    PROJECT_FOLDER_CREATE_ERROR = "Nao foi possivel criar a estrutura do projeto:"
    PROJECT_FILE_CREATE_ERROR = "Nao foi possivel criar o projeto QGIS:"
    PROJECT_DEFAULT_FOLDER_PREPARE_ERROR = "Nao foi possivel preparar a pasta padrao:"
    PROJECT_DEFAULT_FOLDER_ACCESS_ERROR = "Nao foi possivel acessar a pasta padrao:"
    CURRENT_PROJECT_SAVE_TO_NEW_DESTINATION_ERROR = (
        "O QGIS nao conseguiu salvar o projeto atual no novo destino."
    )
    NEW_PROJECT_FILE_WRITE_ERROR = "O QGIS nao conseguiu gravar o novo arquivo .qgz."
    OPEN_NEW_QGIS_WINDOW_ERROR = (
        "O projeto foi criado, mas nao foi possivel abrir outra janela do QGIS."
    )
    PROJECT_CREATED_TITLE = "Projeto criado"
    PROJECT_CREATED_SUCCESS = "Projeto '{project_name}' criado com sucesso"
    PROJECT_CREATED_OPENED_NEW_WINDOW = (
        "Projeto '{project_name}' criado e aberto em outra janela"
    )
    LOAD_FOLDER_LAYERS_TOOLTIP = (
        "Procura arquivos vetoriais e raster na pasta escolhida e em suas subpastas.\n"
        "Marque os formatos que deseja carregar e escolha como organizar as camadas.\n"
        "A ferramenta pode ignorar arquivos já carregados e criar grupos pela estrutura de pastas."
    )

    # plugins/GenerateTrailPlugin.py
    GENERATE_TRAIL_TITLE = "Gerar Rastro de Máquinas"
    GENERATE_TRAIL_TOOLTIP = (
        "Gera a faixa ocupada por um implemento a partir de uma camada de linhas.\n"
        "Converte a largura informada para a unidade da camada,\n"
        "aplica buffer usando metade desse valor e cria\n"
        "uma nova camada com o rastro resultante."
    )

    QML_STYLE = "Estilo QML"
    SAVE_TRAIL_IN = "Salvar rastro em:"
    LINE_LAYER_INPUT_DESC = (
        "Selecione uma camada vetorial de linhas que represente o percurso do "
        "implemento."
    )
    TRAIL_OUTPUT_DESC = (
        "Informe um arquivo GeoPackage ou uma pasta onde a camada de rastro será "
        "salva. "
        "Sem um caminho, o resultado permanece apenas no projeto."
    )
    IMPLEMENT_SIZE_DESC = (
        "Informe a largura total do implemento em metros. A ferramenta usa metade "
        "desse "
        "valor para criar o buffer de cada linha."
    )
    ADVANCED_PARAMETERS_DESC = (
        "Reúne opções adicionais da camada de rastro, como a aplicação de um "
        "estilo QML."
    )
    QML_STYLE_DESC = (
        "Selecione um arquivo QML opcional para aplicar o estilo à camada de "
        "saída gerada."
    )
    START_TRAIL_GENERATION_DESC = (
        "Gera a faixa ocupada pelo implemento a partir da camada de linhas escolhida e "
        "cria a camada resultante."
    )

    # plugins/CopyAttributesPlugin.py
    COPY_ATTRIBUTES_TITLE = "Copiar Atributos de Vetor"
    COPY_ATTRIBUTES_TOOLTIP = (
        "Copia a estrutura de campos de uma camada vetorial de origem\n"
        "para uma camada vetorial de destino.\n"
        "Permite selecionar quais atributos criar e tratar conflitos\n"
        "de nome quando um campo já existe na camada destino."
    )
    COPY_TARGET_LAYER_DESC = (
        "Escolha a camada vetorial que receberá a estrutura dos campos. "
        "A camada de destino precisa estar editável."
    )
    COPY_SOURCE_LAYER_DESC = (
        "Escolha a camada vetorial de origem. "
        "Os campos disponíveis nela serão listados abaixo para seleção."
    )
    SOURCE_LAYER_ATTRIBUTES_DESC = (
        "Lista os campos encontrados na camada de origem para que você escolha "
        "quais serão criados na camada de destino."
    )
    USE_ALL_ATTRIBUTES_DESC = (
        "Quando marcado, copia a estrutura de todos os campos da camada de origem. "
        "Desmarque para escolher os campos individualmente."
    )
    ATTRIBUTE_TO_COPY_DESC = (
        "Marque este campo para criar sua estrutura na camada de destino. "
        "Os valores das feições não são copiados."
    )
    START_COPY_ATTRIBUTES = (
        "Cria na camada de destino a estrutura dos campos escolhidos. "
        "Se já existir um campo com o mesmo nome, a ferramenta pedirá como tratar o conflito."
    )

    # plugins/ExportAllLayouts.py
    EXPORT_ALL_LAYOUTS_TITLE = "Exportar Todos os Layouts"
    EXPORT_ALL_LAYOUTS_TOOLTIP = (
        "Exporta os layouts do projeto para PDF, PNG ou SVG.\n"
        "Escolha os layouts, os formatos e a pasta de saída.\n"
        "Também permite definir a resolução, georreferenciar PDFs,\n"
        "unir arquivos e controlar a substituição de arquivos existentes."
    )
    EXPORT_SELECTED_LAYOUTS_PDF = (
        "Marque para criar um arquivo PDF para cada layout selecionado."
    )
    EXPORT_SELECTED_LAYOUTS_PNG = (
        "Marque para criar uma imagem PNG para cada layout selecionado."
    )
    EXPORT_SELECTED_LAYOUTS_SVG = (
        "Marque para criar um arquivo SVG vetorial para cada layout selecionado."
    )
    MERGE_EXPORTED_PDFS = (
        "Marque para juntar todos os PDFs exportados em um único arquivo final. "
        "Essa opção precisa do pacote PyPDF2."
    )
    MERGE_EXPORTED_PNGS_TO_PDF = (
        "Marque para converter e juntar os PNGs exportados em um único PDF. "
        "Essa opção precisa do pacote Pillow."
    )
    REPLACE_EXISTING_FILES_DESC = (
        "Marque para substituir arquivos com o mesmo nome. "
        "Se desmarcado, a ferramenta cria outro nome para preservar o arquivo existente."
    )
    MAX_WIDTH_MERGED_PNG = (
        "Define a largura máxima, em pixels, ao juntar PNGs em um PDF. "
        "Imagens maiores são reduzidas proporcionalmente."
    )
    OUTPUT_FOLDER_DESC = (
        "Escolha a pasta base onde os arquivos exportados serão salvos."
    )
    START_EXPORT = (
        "Inicia a exportação usando os layouts, formatos e opções escolhidos."
    )
    SELECT_LAYOUTS = "Layouts"
    SELECT_LAYOUTS_DESC = (
        "Abre a lista de layouts. Marque os que deseja exportar; "
        "se nenhum ficar marcado, todos os layouts do projeto serão usados."
    )
    SELECT_LAYOUT_ITEM = "Marque este layout para incluí-lo na exportação."
    SELECT_LAYOUTS_TITLE = "Selecionar Layouts"
    SELECT_LAYOUTS_HINT = (
        "Marque os layouts que deseja exportar. Se nenhum ficar marcado, todos serão usados."
    )
    INVERT_SELECTION = "Inverter"
    NO_LAYOUTS_SELECTED = "Nenhum layout selecionado para exportação."
    LAYOUTS_SELECTED_COUNT = "{count} layout(s) selecionado(s)"

    # plugins/VectorMultipartPlugin.py
    CONVERTER_MULTIPART_TITLE = "Converter Multipart"
    CONVERTER_MULTIPART_TOOLTIP = (
        "Separa cada parte de uma feição multipart em uma feição simples.\n"
        "Atua apenas nas feições selecionadas quando houver seleção;\n"
        "caso contrário, processa toda a camada e preserva os atributos."
    )

    # plugins/CoordClickTool.py
    COORD_CLICK_TOOL_TITLE = "Capturar Coordenadas"
    COORD_CLICK_TOOL_TOOLTIP = (
        "Permite clicar em um ponto do mapa para consultar suas coordenadas.\n"
        "Abre uma janela com WGS84, UTM, altitude aproximada\n"
        "e endereço estimado, além de opções para copiar os resultados."
    )

    # plugins/RasterSamplerTool.py
    RASTER_SAMPLER_TITLE = "Amostrar Valores de Rasters"
    RASTER_SAMPLER_TOOLTIP = (
        "Seleciona rasters do projeto e permite clicar no mapa para consultar\n"
        "o valor de cada raster no ponto clicado. Exibe os valores e as diferenças\n"
        "entre rasters selecionados, com casas decimais configuráveis."
    )
    RASTER_SAMPLER_SELECT_RASTERS = "Rasters para amostragem"
    SELECT_RASTERS_FOR_SAMPLING_DESC = (
        "Abre a lista de rasters do projeto para marcar quais serão consultados\n"
        "a cada clique no mapa."
    )
    RASTER_SAMPLING_SELECTION_HINT = (
        "Marque os rasters que deseja consultar no ponto clicado."
    )
    RASTER_SAMPLING_ITEM_DESC = (
        "Marca este raster para consultar seu valor nos pontos clicados."
    )
    RASTER_SAMPLER_VALUES = "Valores no ponto"
    RASTER_SAMPLER_NO_RASTERS = "Nenhum raster selecionado"
    RASTER_SAMPLER_DECIMALS = "Casas decimais"
    SAMPLED_VALUES_DECIMALS_DESC = (
        "Define quantas casas decimais serão exibidas nos valores e nas diferenças\n"
        "entre os rasters selecionados."
    )
    RASTER_SAMPLER_CLICK_CANVAS_HINT = (
        "Selecione ao menos um raster e clique no mapa\n"
        "para consultar os valores no ponto."
    )
    RASTER_SAMPLING_HINT_DESC = (
        "Orienta a seleção dos rasters e o clique no mapa para iniciar a consulta."
    )
    RASTER_SAMPLING_VALUE_DESC = (
        "Exibe o valor do raster no último ponto clicado; diferenças entre rasters\n"
        "aparecem entre parênteses quando houver dados disponíveis."
    )

    # core/ToolRegistry.py
    RESTART_QGIS_TITLE = "Salvar, Fechar e Reabrir Projeto"
    RESTART_QGIS_TOOLTIP = (
        "Salva o projeto atual, fecha o QGIS e reabre o mesmo arquivo.\n"
        "Use esta ação para recuperar a sessão ou corrigir problemas visuais.\n"
        "Se o projeto ainda não estiver salvo, a ferramenta pedirá um local para salvá-lo."
    )
    LOGCAT_TITLE = "Logcat Viewer"
    LOGCAT_TOOLTIP = (
        "Abre o visualizador de logs do plugin.\n"
        "Permite inspecionar mensagens, erros e eventos internos\n"
        "registrados pelo Cadmus."
    )
    ABOUT_DIALOG_TOOLTIP = (
        f"Abre a janela {ABOUT_CADMUS} do {APP_NAME}.\n"
        "Mostra a versão instalada, autoria, links do projeto\n"
        "e informações gerais sobre a distribuição do plugin."
    )
    LAYER_NOT_EDITABLE_ASK = "A camada '{layer_name}' não está no modo de edição.\n\nDeseja torná-la editável agora?"
    LAYER_NOW_EDITABLE = "Camada colocada em modo de edição automaticamente."
    VECTOR_FIELDS_TITLE = "Calcular Campos Vetoriais"
    VECTOR_FIELDS_TOOLTIP = (
        "Calcula campos de área, comprimento ou coordenadas X/Y\n"
        "na camada vetorial ativa, conforme a geometria e as configurações.\n"
        "Cria ou atualiza os campos necessários para cada feição."
    )
    REMOVE_KML_FIELDS_TITLE = "Remover Campos KML"
    REMOVE_KML_FIELDS_TOOLTIP = (
        "Remove da camada vetorial ativa os campos de atributos típicos de KML.\n"
        "A camada precisa estar no modo de edição para a operação ser executada.\n"
        "A ferramenta não salva a camada nem encerra o modo de edição."
    )
    COPY_COORDINATES_AND_ADDRESS_TO_CLIPBOARD = (
        "Copia todas as coordenadas e o endereço exibidos nesta janela "
        "para a área de transferência."
    )

    # plugins/VectorToSvgPlugin.py
    VECTOR_TO_SVG_TITLE = "Conversor de Vetor para SVG"
    VECTOR_TO_SVG_TOOLTIP = (
        "Converte uma camada vetorial em arquivo SVG.\n"
        "Escolha a camada, a pasta de saída e o estilo do desenho.\n"
        "Você também pode gerar um único SVG ou um arquivo separado para cada feição."
    )
    VECTOR_LAYER_LABEL = "Camada Vetorial"
    VECTOR_LAYER_INPUT_DESC = (
        "Selecione uma camada vetorial carregada no QGIS ou um arquivo vetorial externo. "
        "Use a opção de feições selecionadas para exportar somente o que estiver marcado."
    )
    SVG_OUTPUT_FOLDER_DESC = (
        "Escolha a pasta onde os arquivos SVG serão gravados. "
        "A ferramenta cria a subpasta de saída quando necessário."
    )
    BACKGROUND_COLOR = "Cor Fundo"
    BORDER_COLOR = "Cor Borda"
    BORDER_WIDTH = "Espessura Borda"
    BORDER_WIDTH_DESC = "Define a espessura da borda desenhada no SVG."
    LABEL_COLOR = "Cor Rotulo"
    LABEL_SIZE = "Tamanho Rotulo"
    LABEL_SIZE_DESC = "Define o tamanho do texto usado como rótulo no SVG."
    SELECT_FILL_COLOR = "Selecione a cor de preenchimento"
    SELECT_BORDER_COLOR = "Selecione a cor da borda"
    SELECT_LABEL_COLOR = "Selecione a cor do rotulo"
    TRANSPARENT_BACKGROUND = "Fundo transparente"
    TRANSPARENT_BACKGROUND_DESC = (
        "Quando marcado, não preenche o fundo do SVG com uma cor."
    )
    SHOW_BORDER = "Mostrar Borda"
    SHOW_BORDER_DESC = "Quando marcado, desenha a borda das geometrias no SVG."
    SHOW_LABEL = "Mostrar Rotulo"
    SHOW_LABEL_DESC = "Quando marcado, inclui o nome da camada ou da feição no SVG."
    GENERATE_SVG_FOR_EACH_FEATURE = "Gerar SVG para cada feicao"
    GENERATE_SVG_FOR_EACH_FEATURE_DESC = (
        "Quando marcado, cria um arquivo SVG separado para cada feição exportada."
    )
    START_SVG_EXPORT = "Gera os arquivos SVG usando a camada e as opções escolhidas."
    SVGS_GENERATED_SUCCESS = "SVG(s) gerado(s) com sucesso."
    DIVIDE_POINTS_BY_STRIPS_TITLE = "Dividir Vetor de Pontos por Faixas"
    DIVIDE_POINTS_BY_STRIPS_TOOLTIP = (
        "Prepara a configuração para segmentar uma camada de pontos em faixas.\n"
        "Nesta primeira etapa a ferramenta cadastra a interface,\n"
        "organiza os parâmetros operacionais e de sensibilidade\n"
        "e deixa a execução pronta para a lógica da próxima fase."
    )
    DIVIDE_POINTS_BY_STRIPS_INTRO = (
        "Configure a camada de pontos e os parâmetros iniciais da divisão por faixas."
    )
    DIVIDE_POINTS_BY_STRIPS_INTRO_DESC = (
        "Resume o objetivo da ferramenta: separar pontos em faixas usando os campos e parâmetros abaixo."
    )
    DIVIDE_POINTS_INPUT_DESC = (
        "Selecione uma camada vetorial de pontos do projeto ou um arquivo de pontos para processar."
    )
    DIVIDE_POINTS_SELECTED_FEATURES_LABEL = "Usar apenas feições selecionadas"
    DIVIDE_POINTS_SELECTED_FEATURES_DESC = ONLY_SELECTED_FEATURES_DESC
    OPERATIONAL_PARAMETERS = "Parâmetros Operacionais"
    OPERATIONAL_PARAMETERS_DESC = (
        "Reúne os campos e valores básicos usados para identificar e separar os pontos em faixas."
    )
    SENSITIVITY_PARAMETERS = "Parâmetros de Sensibilidade"
    SENSITIVITY_PARAMETERS_DESC = (
        "Controla como mudanças de direção, tempo e caminho influenciam a detecção de quebras."
    )
    ATTRIBUTES_DESC = (
        "Escolha quais campos calculados pela segmentação serão incluídos nas camadas de saída."
    )
    SAVING_DESC = (
        "Defina opcionalmente onde salvar a camada de pontos processada e o rastro gerado."
    )
    UNIQUE_SEQUENTIAL_ID_FIELD = "Campo ID único/sequencial"
    UNIQUE_SEQUENTIAL_ID_FIELD_DESC = (
        "Escolha o campo que identifica cada ponto em uma sequência sem valores repetidos."
    )
    GROUP_FIELD = "Agrupar por Campo (opcional)"
    GROUP_FIELD_DESC = (
        "Opcionalmente agrupa os pontos pelo valor deste campo antes de executar a segmentação."
    )
    TIMESTAMP_FIELD = "Campo de timestamp"
    TIMESTAMP_FIELD_DESC = (
        "Escolha o campo de data e hora usado para ordenar os pontos e avaliar intervalos temporais."
    )
    JUDGE_MODE = "Modo de Processamento"
    JUDGE_MODE_DESC = (
        "Escolha o algoritmo que avaliará continuidade, direção e pontuação para identificar as quebras."
    )
    CURVE_PATH_DESC = (
        "Considera o caminho como uma trajetória curva ao avaliar a continuidade dos pontos."
    )
    STRAIGHT_PATH_DESC = (
        "Considera o caminho como uma trajetória reta ao avaliar a continuidade dos pontos."
    )
    BOTH_PATH_DESC = (
        "Permite que a avaliação considere trajetórias curvas e retas."
    )
    SAVE_POINTS_OUTPUT_DESC = (
        "Informe um arquivo de saída opcional para salvar a camada de pontos gerada."
    )
    SAVE_TRACK_OUTPUT_DESC = (
        "Informe um arquivo de saída opcional para salvar o rastro linear gerado."
    )
    START_DIVIDE_POINTS_BY_STRIPS = (
        "Executa a segmentação dos pontos usando os campos, parâmetros e saídas escolhidos."
    )
    EXPECTED_POINT_FREQUENCY_SECONDS = "Frequência (s)"
    EXPECTED_POINT_FREQUENCY_SECONDS_DESC = (
        "Informe o intervalo esperado, em segundos, entre pontos consecutivos do levantamento."
    )
    EXPECTED_LATERAL_WIDTH_METERS = "Largura (m)"
    EXPECTED_LATERAL_WIDTH_METERS_DESC = (
        "Informe a largura lateral esperada da faixa, em metros, para apoiar a separação dos pontos."
    )
    AZIMUTH_MOVING_WINDOW = "Janela de azimute"
    AZIMUTH_MOVING_WINDOW_DESC = (
        "Define quantos pontos vizinhos entram no cálculo da direção média antes da detecção de mudança de rumo."
    )
    LIGHT_AZIMUTH_DEVIATION_THRESHOLD = "Limiar leve (°)"
    LIGHT_AZIMUTH_DEVIATION_THRESHOLD_DESC = (
        "Desvio angular inicial que sinaliza uma possível mudança de direção."
    )
    SEVERE_AZIMUTH_DEVIATION_THRESHOLD = "Limiar grave (°)"
    SEVERE_AZIMUTH_DEVIATION_THRESHOLD_DESC = (
        "Desvio angular alto que indica uma mudança de direção mais clara."
    )
    MINIMUM_BREAK_SCORE = "Pontuação mínima"
    MINIMUM_BREAK_SCORE_DESC = (
        "Pontuação mínima para aceitar o desvio como uma quebra real de faixa."
    )
    MINIMUM_POINT_COUNT = "Pontos mínimos"
    MINIMUM_POINT_COUNT_DESC = (
        "Quantidade mínima de pontos que um trecho precisa ter para ser considerado válido."
    )
    TIME_TOLERANCE_MULTIPLIER = "Tolerância de tempo"
    TIME_TOLERANCE_MULTIPLIER_DESC = (
        "Multiplica o intervalo de tempo aceito entre fotos para evitar que pequenas variações criem uma quebra."
    )
    MAX_DEVIATION_POINTS = "Número máximo de pontos desviantes"
    MAX_DEVIATION_POINTS_DESC = (
        "Limita quantos pontos fora do padrão podem ser ignorados antes de confirmar uma quebra."
    )
    MAX_DISTANCE_BETWEEN_POINTS = "Distância máxima entre pontos"
    MAX_DISTANCE_BETWEEN_POINTS_DESC = (
        "Define a distância máxima entre pontos para que ainda possam pertencer ao mesmo trecho."
    )

    # Descrições dos campos calculados exibidos na seleção de saída.
    SHOT_ID_FIELD_DESC = "Identificador único do segmento de tiro ou faixa."
    OLD_SHOT_ID_FIELD_DESC = (
        "Identificador original do segmento antes da validação do tamanho do grupo."
    )
    SHOT_VALID_FIELD_DESC = (
        "Indica se o segmento possui pontos suficientes para ser considerado válido."
    )
    SCORE_FIELD_DESC = "Pontuação da quebra combinando direção e continuidade."
    SCORE_DIRECTION_FIELD_DESC = "Componente da pontuação causada pela mudança de direção."
    SCORE_CONTINUITY_FIELD_DESC = (
        "Componente da pontuação causada por descontinuidade temporal ou espacial."
    )
    SEGMENT_TYPE_FIELD_DESC = "Classificação do segmento, como faixa ou bordadura."
    INSTANT_AZIMUTH_FIELD_DESC = "Azimute calculado entre pontos consecutivos."
    MEAN_AZIMUTH_FIELD_DESC = "Média circular do azimute, ponderada pela velocidade."
    AZIMUTH_DELTA_FIELD_DESC = (
        "Diferença angular entre o azimute instantâneo e a média."
    )
    TIME_DELTA_FIELD_DESC = "Diferença de tempo, em segundos, entre pontos consecutivos."
    DISTANCE_DELTA_FIELD_DESC = "Distância, em metros, entre pontos consecutivos."
    INSTANT_VELOCITY_FIELD_DESC = "Velocidade instantânea, em metros por segundo."
    PREVIOUS_AZIMUTH_FIELD_DESC = "Azimute do segmento anterior (i-1 → i)."
    NEXT_AZIMUTH_FIELD_DESC = "Azimute do segmento seguinte (i → i+1)."
    PREVIOUS_AZIMUTH_DELTA_FIELD_DESC = (
        "Diferença angular entre o azimute instantâneo e o azimute anterior."
    )
    NEXT_AZIMUTH_DELTA_FIELD_DESC = (
        "Diferença angular entre o azimute instantâneo e o azimute seguinte."
    )
    SELECT_POINT_VECTOR_LAYER = "Selecione uma camada vetorial de pontos."
    SELECT_FILE_BASED_POINT_LAYER = "Selecione uma camada de pontos baseada em arquivo."
    SELECT_REQUIRED_FIELDS = "Selecione os campos obrigatórios de ID e timestamp."
    SAVE_AND_STOP_EDITING_LAYER = (
        "Salve e encerre a edição da camada antes de executar esta ferramenta."
    )
    SHOT_SEGMENTATION_COMPLETED = "Segmentação concluída. Pontos: {total_points} | Tiros: {total_shots} | Válidos: {valid_shots} | Inválidos: {invalid_shots}"
    SHOT_SEGMENTATION_BUFFER_COMPLETED = "Segmentação concluída no buffer de edição. Pontos: {total_points} | Tiros: {total_shots} | Válidos: {valid_shots} | Inválidos: {invalid_shots}"
    DIVIDE_POINTS_BY_STRIPS_UI_ONLY_MESSAGE = "A interface foi criada. A rotina de divisão por faixas será implementada na próxima etapa."

    # processing/RasterOptimizer.py
    RASTER_OPTIMIZER_TITLE = "Otimizar Raster (Overviews)"
    RASTER_OPTIMIZER_TOOLTIP = (
        "Cria ou reconstrói pirâmides (overviews) em rasters TIFF.\n"
        "Permite selecionar pasta com rasters ou camadas individuais,\n"
        "escolher os níveis de overview, método de reamostragem\n"
        "e algoritmo de compressão (LZW, DEFLATE, ZSTD)."
    )
    INPUT_RASTER_LAYERS = "Camadas Raster de Entrada"
    INPUT_RASTER_FOLDER = "Pasta com Rasters"
    OVERVIEW_LEVELS = "Níveis de Overview"
    RESAMPLING_METHOD = "Método de Reamostragem"
    COMPRESS_OVERVIEW = "Compressão das Overviews"
    PREDICTOR = "Predictor"
    ZLEVEL = "ZLevel (compressão)"
    DELETE_EXISTING_OVERVIEWS = "Deletar overviews existentes antes de recriar"
    OVERVIEWS_CREATED_SUCCESS = "Overviews criadas/atualizadas com sucesso."
    OVERVIEWS_ERROR = "Erro ao criar overviews: {error}"
    RASTER_OPTIMIZER_COMPLETED = "Otimização de rasters concluída."
    USE_RECURSIVE_SEARCH = "Incluir subpastas"
    SEARCHING_RASTERS = "Buscando rasters..."
    BIGTIFF_YES = "Forçar BIGTIFF (necessário para arquivos >4GB)"
    RGB_MOSAIC_CREATOR_TITLE = "Criador de Mosaico RGB"
    INPUT_RASTER_RED_BAND = "Raster Banda Vermelha (R)"
    INPUT_RASTER_GREEN_BAND = "Raster Banda Verde (G)"
    INPUT_RASTER_BLUE_BAND = "Raster Banda Azul (B)"
    BAND_RED_LABEL = "Banda R"
    BAND_GREEN_LABEL = "Banda G"
    BAND_BLUE_LABEL = "Banda B"
    CREATE_ALPHA_BAND = "Criar banda alpha para NoData"
    ALPHA_NODATA_VALUE = "Valor NoData para alpha"
    RGB_COMPOSITE = "Composicao RGB"
    NDVI_CALCULATOR_TITLE = "Calculadora NDVI"
    INPUT_RASTER_NIR = "Raster Infravermelho Proximo (NIR)"
    INPUT_RASTER_RED = "Raster Vermelho (RED)"
    BAND_NIR = "Banda NIR"
    BAND_RED = "Banda RED"
    SENTINEL_BANDS_INFO = "Sentinel-2: Banda 8 (NIR) e Banda 4 (Red)"
    LANDSAT_BANDS_INFO = "Landsat 8/9: Banda 5 (NIR) e Banda 4 (Red) | Landsat 5/7: Banda 4 (NIR) e Banda 3 (Red)"
    NDVI = "NDVI"
    NDRE_CALCULATOR_TITLE = "Calculadora NDRE (Red Edge)"
    INPUT_RASTER_NIR_NDRE = "Raster Infravermelho Proximo (NIR) para NDRE"
    INPUT_RASTER_REDEDGE = "Raster Borda Vermelha (RedEdge)"
    BAND_REDEDGE = "Banda RedEdge"
    NDRE = "NDRE"
    CALCULATE_CHM_TITLE = "Calcular CHM (MDS - MDT)"
    MDS = "Raster MDS (Modelo Digital de Superfície)"
    MDT = "Raster MDT (Modelo Digital do Terreno)"
    CHM = "Raster CHM (Modelo de Altura de Copas)"
    RASTER_MEAN_ADJUST_TITLE = "Ajustar Média Raster"
    TARGET_MEAN = "Média desejada"
    OUTPUT = "Saída"
    GLI_CALCULATOR_TITLE = "Calculadora GLI (Green Leaf Index)"
    INPUT_RASTER_RGB_GLI = "Raster RGB de entrada (3 ou 4 bandas)"
    GLI = "GLI"
    GLI_STYLE_PATH = "Caminho do estilo QML GLI"
    GLI_INTERPRETATION = """Interpretacao dos valores GLI:
  -1.0 a 0.0  : Solo exposto, agua, superficies nao vegetadas
   0.0 a 0.2  : Vegetacao esparsa ou estressada
   0.2 a 0.5  : Vegetacao moderada
   0.5 a 1.0  : Vegetacao densa e saudavel"""
    RGB_STYLE_STANDARDIZER_TITLE = "Padronizar Estilo RGB (Percentil)"
    INPUT_RASTER_RGB = "Raster RGB de entrada"
    RGB_STANDARDIZER_OUTPUT = "Raster RGB padronizado"
    SEGMENTATION_MODE = "Modo de Segmentação"
    CURVE = "Curva"
    STRAIGHT = "Reta"
    BOTH_PATH = "Ambas"

    PATH = "Path"

    # plugins/PathExtensionPlugin.py
    PATH_EXTENSION_TITLE = "Remover/Restaurar Extensão"
    PATH_EXTENSION_TOOLTIP = (
        "Remove ou restaura a extensão dos arquivos indicados pelos paths das feições. "
        "Também permite compactar os arquivos em ZIP ou extrair arquivos ZIP.\n"
        "O caminho resultante de cada operação é gravado no campo NewPath da camada."
    )
    MODE_REMOVE = "Remover extensão"
    MODE_RESTORE = "Restaurar extensão"
    MODE_ZIP = "Zipar arquivos"
    MODE_UNZIP = "Deszipar arquivos"
    VECTOR_LAYER_WITH_PATHS_DESC = (
        "Selecione uma camada vetorial carregada no QGIS ou um arquivo vetorial "
        "externo que contenha os caminhos dos arquivos a processar."
    )
    FILE_PATH_FIELD_DESC = (
        "Selecione o campo de atributos que armazena os caminhos físicos dos arquivos "
        "a serem processados."
    )
    REMOVE_FILE_EXTENSION_DESC = (
        "Remove o ponto e a extensão do nome físico do arquivo e grava o novo caminho "
        "no campo NewPath."
    )
    RESTORE_FILE_EXTENSION_DESC = (
        "Restaura o ponto e a extensão do arquivo físico e grava o novo caminho "
        "no campo NewPath."
    )
    ZIP_REFERENCED_FILES_DESC = (
        "Agrupa em um ZIP os arquivos apontados pelas feições da mesma pasta e remove "
        "os arquivos originais após a compactação."
    )
    UNZIP_REFERENCED_FILES_DESC = (
        "Extrai o ZIP da pasta dos arquivos apontados e remove o ZIP após a extração."
    )
    START_PATH_FILE_OPERATION_DESC = (
        "Inicia o processamento dos arquivos apontados. O resultado de cada operação "
        "é gravado no campo NewPath da camada."
    )

    # Registry
    REG_TITLE = "Gerenciar"
    REGISTRY_SAVED_SUCCESS = "Salvo e validado com sucesso."
    REGISTRY_DELETED_SUCCESS = "Removido com sucesso."
    REGISTRY_INVALID = "Inválido."
    REGISTRY_EMPTY = "Preencha o campo."
    NO_KEY = "sem chave"
    EXPIRATION_DATE = "Validade"
    REMAINING_DAYS = "dias restantes"
    STATUS = "Status"
    LEVEL = "Nível"
    ACTIVE = "Ativa"
    INACTIVE = "Inativa"
    VALIDATE = "Validar"
    RESTORE_DISTRIBUTION = "Restaurar Registro"
    SELECT_DIST_FILE = "Selecione um arquivo .dist primeiro."
    DIST_FILE_NOT_FOUND = "Seletor de registro não encontrado."
    LICENSE_KEY = "Chave"

    # plugins/SaveTemporaryLayersPlugin.py
    SAVE_TEMPORARY_LAYER_TITLE = "Salvar Temporárias"
    SAVE_TEMPORARY_LAYER_TOOLTIP = (
        "Salva camadas temporárias (memory) do projeto em arquivos permanentes no disco"
    )
    PREFIX = "Prefixo"
    PREFIX_DESC = "Texto acrescentado antes do nome original das camadas salvas."
    SUFFIX = "Sufixo"
    SUFFIX_DESC = "Texto acrescentado depois do nome original das camadas salvas."
    EXTENSION_VECTOR = "Extensão Vetor"
    EXTENSION_RASTER = "Extensão Raster"
    VECTORS_FOLDER = "Pasta de Vetores"
    RASTERS_FOLDER = "Pasta de Rasters"
    SEPARATOR = "Separador"
    VECTOR_EXTENSIONS = "Extensões Vetor"
    VECTOR_EXTENSIONS_DESC = (
        "Formato usado para salvar as camadas vetoriais temporárias encontradas no projeto."
    )
    RASTER_EXTENSIONS = "Extensões Raster"
    RASTER_EXTENSIONS_DESC = (
        "Formato usado para salvar as camadas raster temporárias encontradas no projeto."
    )
    SAVE_TEMPORARY_OUTPUT_FOLDER_DESC = (
        "Escolha a pasta base onde serão criadas as subpastas de vetores e rasters."
    )
    START_SAVE_TEMPORARY_LAYERS = (
        "Localiza as camadas temporárias e grava vetores e rasters nos formatos escolhidos."
    )
    OUTPUT_CONFIG = "Configuração de Saída"
    CONVERTER_FILE_TYPE = "Tipo de Arquivo"
    SELECT_OUTPUT_FOLDER = "Selecionar Pasta de Saída"
    USE_PROJECT_FOLDER = "Usar Pasta do Projeto"
    OPEN_OUTPUT_FOLDER = "Abrir Pasta de Saída"

    # plugins/ImageryDownloaderPlugin.py
    IMAGERY_DOWNLOADER_TITLE = "Downloader de Imagens de Satélite"
    IMAGERY_DOWNLOADER_TOOLTIP = (
        "Busca e baixa cenas (Sentinel-2) por bbox, datas e % de nuvens"
    )
    IMAGERY_SETTINGS_DESC = (
        "Define a extensão, o período, o limite de nuvens, o processamento "
        "e a pasta dos arquivos."
    )
    START_DATE = "Data inicial"
    START_DATE_DESC = "Define a data inicial usada para buscar cenas no catálogo."
    END_DATE = "Data final"
    END_DATE_DESC = "Define a data final usada para buscar cenas no catálogo."
    DATE_PERIOD = "Período"
    CLOUD_MAX = "% Máximo de Nuvens"
    CLOUD_MAX_DESC = (
        "Limita a busca a cenas com cobertura de nuvens até o percentual informado."
    )
    BANDS_ASSETS = "Bandas e Composições"
    BANDS_ASSETS_DESC = "Selecione bandas e composições a baixar"
    BAND_ASSET_ITEM_DESC = "Marca esta banda/asset para incluí-la no download."
    COMPOSITION_ITEM_DESC = (
        "Marca a composição pronta; as bandas usadas por ela também serão selecionadas."
    )
    SETTINGS = "Configurações"
    OPTIONS = "Opções de Processamento"
    OPTIONS_DESC = (
        "Aplica recorte, reprojeção, conversão de escala e remoção dos arquivos originais."
    )
    CLIP_BY_POLYGON = "Recortar pelo polígono"
    CLIP_BY_POLYGON_DESC = (
        "Recorta pelo polígono desenhado ou pela camada de polígono; "
        "sem polígono, recorta pelo boundary da extensão"
    )
    REPROJECT_OUTPUT = "Reprojetar saída"
    REPROJECT_OUTPUT_DESC = (
        "Reprojeção apenas se o CRS de origem diferir do CRS de saída"
    )
    CONVERT_UINT16 = "Converter uint16 (÷10000 → float32)"
    CONVERT_UINT16_DESC = "Divide por 10000 e salva como float32 (_refl.tif)"
    DELETE_ORIGINALS = "Apagar originais"
    DELETE_ORIGINALS_DESC = "Remove os arquivos uint16 após conversão"
    EPSG_OUTPUT = "EPSG de saída"
    EPSG_OUTPUT_DESC = "Define o CRS usado para gravar as imagens baixadas."
    SOURCE = "Fonte"
    IMAGERY_SOURCE_DESC = "Fonte do catálogo de imagens consultado para listar as cenas."
    BBOX_SOURCE = "Extensão da Busca"
    BBOX_SOURCE_DESC = "Define a área de busca (camada, tela ou desenho no mapa)"
    BBOX_CAPTURE_SCREEN = "Tela"
    BBOX_CAPTURE_SCREEN_DESC = "Usa a extensão do mapa atual (canvas)"
    BBOX_DRAW_MAP = "Desenhar"
    BBOX_DRAW_MAP_DESC = (
        "Desenha a área no mapa (clique para os vértices; "
        "botão direito ou duplo clique conclui)"
    )
    SEARCH_SCENES = "Buscar Cenas"
    SEARCH_SCENES_DESC = (
        "Busca no catálogo as cenas que atendem à extensão, ao período e à cobertura de nuvens."
    )
    SCENES_FOUND = "cenas encontradas"
    NO_SCENES_FOUND = "Nenhuma cena encontrada para os filtros informados"
    SELECT_SCENES = "Selecionar cenas para download"
    SCENE_RESULTS_STATUS_DESC = (
        "Mostra quantas cenas foram encontradas e informa o carregamento das miniaturas."
    )
    SCENE_SELECTION_LIST_DESC = (
        "Marque as cenas que deseja baixar; cada cartão mostra data, tile, plataforma e cobertura de nuvens."
    )
    SCENE_ITEM_DESC = (
        "Marca esta cena para incluí-la no download; confira os dados e a miniatura antes de confirmar."
    )
    DOWNLOAD_SELECTED = "Baixar Selecionadas"
    DOWNLOAD_SELECTED_SCENES_DESC = (
        "Confirma a seleção e inicia o download das cenas marcadas."
    )
    NO_SCENE_SELECTED = "Selecione pelo menos uma cena"
    CLOUD_COVER = "nuvens"
    NO_THUMBNAIL = "sem thumbnail"
    DOWNLOAD_FINISHED = "Download concluído"
    PARALLEL_INFO = "Download de {n} datas em paralelo (ParallelStep)"
    PARALLEL_NOT_POSSIBLE = (
        "Execução sequencial (paralelismo exige 2+ datas independentes)"
    )
    DEPENDENCY_MISSING_IMAGERY = (
        "A biblioteca PySTACClient é necessária. Deseja instalá-la agora?"
    )
    VALIDATION_EXTENT = (
        "Defina a extensão da busca (camada, tela ou desenho no mapa)."
    )
    VALIDATION_DATES = "A data inicial deve ser menor ou igual à data final."
    VALIDATION_BANDS = "Selecione pelo menos uma banda ou composição."
    VALIDATION_CLIP = (
        "A opção de recorte exige uma camada de polígono ou uma extensão válida."
    )
    TEMP_FOLDER_HINT = (
        "Os arquivos foram salvos na pasta temporária do Cadmus."
    )
