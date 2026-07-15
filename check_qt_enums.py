# -*- coding: utf-8 -*-
"""
Script de verificação de enumerações Qt5/Qt6.

Escaneia todos os arquivos .py do projeto e gera um relatório txt
com todos os pontos onde existem enums que precisam ser atualizados
para compatibilidade Qt5/Qt6.

Uso:
    python check_qt_enums.py

Gera:
    qt_enum_errors_report.txt
"""

import os
import re
import sys
from pathlib import Path


# Mapeamento de enums antigos (Qt5) -> novos (Qt6)
# Cada entry: (regex_pattern, correcao_sugerida)
ENUM_PATTERNS = [
    # --- Qt namespace enums ---
    (r'Qt\.\bAlignLeft\b',        'Qt.AlignmentFlag.AlignLeft'),
    (r'Qt\.\bAlignRight\b',       'Qt.AlignmentFlag.AlignRight'),
    (r'Qt\.\bAlignHCenter\b',     'Qt.AlignmentFlag.AlignHCenter'),
    (r'Qt\.\bAlignTop\b',         'Qt.AlignmentFlag.AlignTop'),
    (r'Qt\.\bAlignBottom\b',      'Qt.AlignmentFlag.AlignBottom'),
    (r'Qt\.\bAlignVCenter\b',     'Qt.AlignmentFlag.AlignVCenter'),
    (r'Qt\.\bAlignCenter\b',      'Qt.AlignmentFlag.AlignCenter'),
    (r'Qt\.\bAlignJustify\b',     'Qt.AlignmentFlag.AlignJustify'),
    (r'Qt\.\bAlignAbsolute\b',    'Qt.AlignmentFlag.AlignAbsolute'),

    (r'Qt\.\bChecked\b',          'Qt.CheckState.Checked'),
    (r'Qt\.\bUnchecked\b',        'Qt.CheckState.Unchecked'),
    (r'Qt\.\bPartiallyChecked\b', 'Qt.CheckState.PartiallyChecked'),

    (r'Qt\.\bScrollBarAsNeeded\b',   'Qt.ScrollBarPolicy.ScrollBarAsNeeded'),
    (r'Qt\.\bScrollBarAlwaysOff\b',  'Qt.ScrollBarPolicy.ScrollBarAlwaysOff'),
    (r'Qt\.\bScrollBarAlwaysOn\b',   'Qt.ScrollBarPolicy.ScrollBarAlwaysOn'),

    (r'Qt\.\bPointingHandCursor\b', 'Qt.CursorShape.PointingHandCursor'),
    (r'Qt\.\bArrowCursor\b',        'Qt.CursorShape.ArrowCursor'),
    (r'Qt\.\bCrossCursor\b',        'Qt.CursorShape.CrossCursor'),
    (r'Qt\.\bWaitCursor\b',         'Qt.CursorShape.WaitCursor'),
    (r'Qt\.\bIBeamCursor\b',        'Qt.CursorShape.IBeamCursor'),
    (r'Qt\.\bSizeVerCursor\b',      'Qt.CursorShape.SizeVerCursor'),
    (r'Qt\.\bSizeHorCursor\b',      'Qt.CursorShape.SizeHorCursor'),
    (r'Qt\.\bSizeBDiagCursor\b',    'Qt.CursorShape.SizeBDiagCursor'),
    (r'Qt\.\bSizeFDiagCursor\b',    'Qt.CursorShape.SizeFDiagCursor'),
    (r'Qt\.\bSizeAllCursor\b',      'Qt.CursorShape.SizeAllCursor'),
    (r'Qt\.\bBlankCursor\b',        'Qt.CursorShape.BlankCursor'),
    (r'Qt\.\bBusyCursor\b',         'Qt.CursorShape.BusyCursor'),
    (r'Qt\.\bForbiddenCursor\b',    'Qt.CursorShape.ForbiddenCursor'),
    (r'Qt\.\bOpenHandCursor\b',     'Qt.CursorShape.OpenHandCursor'),
    (r'Qt\.\bClosedHandCursor\b',   'Qt.CursorShape.ClosedHandCursor'),
    (r'Qt\.\bWhatsThisCursor\b',    'Qt.CursorShape.WhatsThisCursor'),
    (r'Qt\.\bSplitHCursor\b',       'Qt.CursorShape.SplitHCursor'),
    (r'Qt\.\bSplitVCursor\b',       'Qt.CursorShape.SplitVCursor'),

    (r'Qt\.\bSmoothTransformation\b',       'Qt.TransformationMode.SmoothTransformation'),
    (r'Qt\.\bFastTransformation\b',         'Qt.TransformationMode.FastTransformation'),

    (r'Qt\.\bKeepAspectRatio\b',            'Qt.AspectRatioMode.KeepAspectRatio'),
    (r'Qt\.\bIgnoreAspectRatio\b',          'Qt.AspectRatioMode.IgnoreAspectRatio'),
    (r'Qt\.\bKeepAspectRatioByExpanding\b', 'Qt.AspectRatioMode.KeepAspectRatioByExpanding'),

    (r'Qt\.\bTransparentMode\b',     'Qt.BGMode.TransparentMode'),
    (r'Qt\.\bOpaqueMode\b',          'Qt.BGMode.OpaqueMode'),

    (r'Qt\.\bPenStyle\b',            'Qt.PenStyle.SolidLine'),  # CUIDADO: generico demais, trataremos separadamente
    (r'Qt\.\bSolidLine\b',           'Qt.PenStyle.SolidLine'),
    (r'Qt\.\bDashLine\b',            'Qt.PenStyle.DashLine'),
    (r'Qt\.\bDotLine\b',             'Qt.PenStyle.DotLine'),
    (r'Qt\.\bDashDotLine\b',         'Qt.PenStyle.DashDotLine'),
    (r'Qt\.\bDashDotDotLine\b',      'Qt.PenStyle.DashDotDotLine'),
    (r'Qt\.\bNoPen\b',               'Qt.PenStyle.NoPen'),

    (r'Qt\.\bFlatCap\b',     'Qt.PenCapStyle.FlatCap'),
    (r'Qt\.\bSquareCap\b',   'Qt.PenCapStyle.SquareCap'),
    (r'Qt\.\bRoundCap\b',    'Qt.PenCapStyle.RoundCap'),

    (r'Qt\.\bMiterJoin\b',  'Qt.PenJoinStyle.MiterJoin'),
    (r'Qt\.\bBevelJoin\b',  'Qt.PenJoinStyle.BevelJoin'),
    (r'Qt\.\bRoundJoin\b',  'Qt.PenJoinStyle.RoundJoin'),

    (r'Qt\.\bNoBrush\b',    'Qt.BrushStyle.NoBrush'),
    (r'Qt\.\bSolidPattern\b',   'Qt.BrushStyle.SolidPattern'),

    (r'Qt\.\bHorizontal\b',   'Qt.Orientation.Horizontal'),
    (r'Qt\.\bVertical\b',     'Qt.Orientation.Vertical'),

    (r'Qt\.\bLeftButton\b',   'Qt.MouseButton.LeftButton'),
    (r'Qt\.\bRightButton\b',  'Qt.MouseButton.RightButton'),
    (r'Qt\.\bMiddleButton\b', 'Qt.MouseButton.MiddleButton'),
    (r'Qt\.\bNoButton\b',     'Qt.MouseButton.NoButton'),

    (r'Qt\.\bKey_Return\b',   'Qt.Key.Key_Return'),
    (r'Qt\.\bKey_Enter\b',    'Qt.Key.Key_Enter'),
    (r'Qt\.\bKey_Escape\b',   'Qt.Key.Key_Escape'),
    (r'Qt\.\bKey_Tab\b',      'Qt.Key.Key_Tab'),
    (r'Qt\.\bKey_Backtab\b',  'Qt.Key.Key_Backtab'),
    (r'Qt\.\bKey_Space\b',    'Qt.Key.Key_Space'),
    (r'Qt\.\bKey_Delete\b',   'Qt.Key.Key_Delete'),
    (r'Qt\.\bKey_Up\b',       'Qt.Key.Key_Up'),
    (r'Qt\.\bKey_Down\b',     'Qt.Key.Key_Down'),
    (r'Qt\.\bKey_Left\b',     'Qt.Key.Key_Left'),
    (r'Qt\.\bKey_Right\b',    'Qt.Key.Key_Right'),
    (r'Qt\.\bKey_Home\b',     'Qt.Key.Key_Home'),
    (r'Qt\.\bKey_End\b',      'Qt.Key.Key_End'),
    (r'Qt\.\bKey_PageUp\b',   'Qt.Key.Key_PageUp'),
    (r'Qt\.\bKey_PageDown\b', 'Qt.Key.Key_PageDown'),
    (r'Qt\.\bKey_Shift\b',    'Qt.Key.Key_Shift'),
    (r'Qt\.\bKey_Control\b',  'Qt.Key.Key_Control'),
    (r'Qt\.\bKey_Alt\b',      'Qt.Key.Key_Alt'),
    (r'Qt\.\bKey_Meta\b',     'Qt.Key.Key_Meta'),

    (r'Qt\.\bControlModifier\b',   'Qt.KeyboardModifier.ControlModifier'),
    (r'Qt\.\bShiftModifier\b',     'Qt.KeyboardModifier.ShiftModifier'),
    (r'Qt\.\bAltModifier\b',       'Qt.KeyboardModifier.AltModifier'),
    (r'Qt\.\bNoModifier\b',        'Qt.KeyboardModifier.NoModifier'),
    (r'Qt\.\bMetaModifier\b',      'Qt.KeyboardModifier.MetaModifier'),
    (r'Qt\.\bGroupSwitchModifier\b','Qt.KeyboardModifier.GroupSwitchModifier'),
    (r'Qt\.\bKeypadModifier\b',    'Qt.KeyboardModifier.KeypadModifier'),

    (r'Qt\.\bWhite\b',        'Qt.GlobalColor.white'),
    (r'Qt\.\bBlack\b',        'Qt.GlobalColor.black'),
    (r'Qt\.\bRed\b',          'Qt.GlobalColor.red'),
    (r'Qt\.\bDarkRed\b',      'Qt.GlobalColor.darkRed'),
    (r'Qt\.\bGreen\b',        'Qt.GlobalColor.green'),
    (r'Qt\.\bDarkGreen\b',    'Qt.GlobalColor.darkGreen'),
    (r'Qt\.\bBlue\b',         'Qt.GlobalColor.blue'),
    (r'Qt\.\bDarkBlue\b',     'Qt.GlobalColor.darkBlue'),
    (r'Qt\.\bCyan\b',         'Qt.GlobalColor.cyan'),
    (r'Qt\.\bDarkCyan\b',     'Qt.GlobalColor.darkCyan'),
    (r'Qt\.\bMagenta\b',      'Qt.GlobalColor.magenta'),
    (r'Qt\.\bDarkMagenta\b',  'Qt.GlobalColor.darkMagenta'),
    (r'Qt\.\bYellow\b',       'Qt.GlobalColor.yellow'),
    (r'Qt\.\bDarkYellow\b',   'Qt.GlobalColor.darkYellow'),
    (r'Qt\.\bGray\b',         'Qt.GlobalColor.gray'),
    (r'Qt\.\bDarkGray\b',     'Qt.GlobalColor.darkGray'),
    (r'Qt\.\bLightGray\b',    'Qt.GlobalColor.lightGray'),
    (r'Qt\.\bTransparent\b',  'Qt.GlobalColor.transparent'),
    (r'Qt\.\bColor0\b',       'Qt.GlobalColor.color0'),
    (r'Qt\.\bColor1\b',       'Qt.GlobalColor.color1'),

    # --- QSizePolicy ---
    (r'QSizePolicy\.\bFixed\b',          'QSizePolicy.Policy.Fixed'),
    (r'QSizePolicy\.\bMinimum\b',        'QSizePolicy.Policy.Minimum'),
    (r'QSizePolicy\.\bMaximum\b',        'QSizePolicy.Policy.Maximum'),
    (r'QSizePolicy\.\bPreferred\b',      'QSizePolicy.Policy.Preferred'),
    (r'QSizePolicy\.\bExpanding\b',      'QSizePolicy.Policy.Expanding'),
    (r'QSizePolicy\.\bMinimumExpanding\b','QSizePolicy.Policy.MinimumExpanding'),
    (r'QSizePolicy\.\bIgnored\b',        'QSizePolicy.Policy.Ignored'),

    # --- QFrame / QScrollArea ---
    (r'QFrame\.\bNoFrame\b',      'QFrame.Shape.NoFrame'),
    (r'QFrame\.\bBox\b',          'QFrame.Shape.Box'),
    (r'QFrame\.\bPanel\b',        'QFrame.Shape.Panel'),
    (r'QFrame\.\bStyledPanel\b',  'QFrame.Shape.StyledPanel'),
    (r'QFrame\.\bHLine\b',        'QFrame.Shape.HLine'),
    (r'QFrame\.\bVLine\b',        'QFrame.Shape.VLine'),
    (r'QFrame\.\bWinPanel\b',     'QFrame.Shape.WinPanel'),

    (r'QFrame\.\bPlain\b',        'QFrame.Shadow.Plain'),
    (r'QFrame\.\bRaised\b',       'QFrame.Shadow.Raised'),
    (r'QFrame\.\bSunken\b',       'QFrame.Shadow.Sunken'),

    # --- QDialog/QProgressDialog etc ---
    (r'(?<![a-zA-Z.])QDialog\.\bAccepted\b',   'QDialog.DialogCode.Accepted'),
    (r'(?<![a-zA-Z.])QDialog\.\bRejected\b',   'QDialog.DialogCode.Rejected'),

    # --- QListWidget ---
    (r'QListWidget\.\bSingleSelection\b',     'QListWidget.SelectionMode.SingleSelection'),
    (r'QListWidget\.\bContiguousSelection\b',  'QListWidget.SelectionMode.ContiguousSelection'),
    (r'QListWidget\.\bExtendedSelection\b',    'QListWidget.SelectionMode.ExtendedSelection'),
    (r'QListWidget\.\bMultiSelection\b',       'QListWidget.SelectionMode.MultiSelection'),
    (r'QListWidget\.\bNoSelection\b',          'QListWidget.SelectionMode.NoSelection'),

    # --- QAbstractItemView ---
    (r'QAbstractItemView\.\bSingleSelection\b',     'QAbstractItemView.SelectionMode.SingleSelection'),
    (r'QAbstractItemView\.\bContiguousSelection\b',  'QAbstractItemView.SelectionMode.ContiguousSelection'),
    (r'QAbstractItemView\.\bExtendedSelection\b',    'QAbstractItemView.SelectionMode.ExtendedSelection'),
    (r'QAbstractItemView\.\bMultiSelection\b',       'QAbstractItemView.SelectionMode.MultiSelection'),
    (r'QAbstractItemView\.\bNoSelection\b',          'QAbstractItemView.SelectionMode.NoSelection'),

    # --- QStyle ---
    (r'QStyle\.\bSP_',         'QStyle.StandardPixmap.SP_ (check specific enum)'),

    # --- QColor ---
    (r'QColor\.\bHexArgb\b',   'QColor.NameFormat.HexArgb'),
    (r'QColor\.\bHexRgb\b',    'QColor.NameFormat.HexRgb'),

    # --- QEasingCurve ---
    (r'QEasingCurve\.\bLinear\b',         'QEasingCurve.Type.Linear'),
    (r'QEasingCurve\.\bInQuad\b',         'QEasingCurve.Type.InQuad'),
    (r'QEasingCurve\.\bOutQuad\b',        'QEasingCurve.Type.OutQuad'),
    (r'QEasingCurve\.\bInOutQuad\b',      'QEasingCurve.Type.InOutQuad'),
    (r'QEasingCurve\.\bOutInQuad\b',      'QEasingCurve.Type.OutInQuad'),
    (r'QEasingCurve\.\bInCubic\b',        'QEasingCurve.Type.InCubic'),
    (r'QEasingCurve\.\bOutCubic\b',       'QEasingCurve.Type.OutCubic'),
    (r'QEasingCurve\.\bInOutCubic\b',     'QEasingCurve.Type.InOutCubic'),
    (r'QEasingCurve\.\bOutInCubic\b',     'QEasingCurve.Type.OutInCubic'),
    (r'QEasingCurve\.\bInQuart\b',        'QEasingCurve.Type.InQuart'),
    (r'QEasingCurve\.\bOutQuart\b',       'QEasingCurve.Type.OutQuart'),
    (r'QEasingCurve\.\bInOutQuart\b',     'QEasingCurve.Type.InOutQuart'),
    (r'QEasingCurve\.\bOutInQuart\b',     'QEasingCurve.Type.OutInQuart'),
    (r'QEasingCurve\.\bInQuint\b',        'QEasingCurve.Type.InQuint'),
    (r'QEasingCurve\.\bOutQuint\b',       'QEasingCurve.Type.OutQuint'),
    (r'QEasingCurve\.\bInOutQuint\b',     'QEasingCurve.Type.InOutQuint'),
    (r'QEasingCurve\.\bOutInQuint\b',     'QEasingCurve.Type.OutInQuint'),
    (r'QEasingCurve\.\bInSine\b',         'QEasingCurve.Type.InSine'),
    (r'QEasingCurve\.\bOutSine\b',        'QEasingCurve.Type.OutSine'),
    (r'QEasingCurve\.\bInOutSine\b',      'QEasingCurve.Type.InOutSine'),
    (r'QEasingCurve\.\bOutInSine\b',      'QEasingCurve.Type.OutInSine'),
    (r'QEasingCurve\.\bInExpo\b',         'QEasingCurve.Type.InExpo'),
    (r'QEasingCurve\.\bOutExpo\b',        'QEasingCurve.Type.OutExpo'),
    (r'QEasingCurve\.\bInOutExpo\b',      'QEasingCurve.Type.InOutExpo'),
    (r'QEasingCurve\.\bOutInExpo\b',      'QEasingCurve.Type.OutInExpo'),
    (r'QEasingCurve\.\bInCirc\b',         'QEasingCurve.Type.InCirc'),
    (r'QEasingCurve\.\bOutCirc\b',        'QEasingCurve.Type.OutCirc'),
    (r'QEasingCurve\.\bInOutCirc\b',      'QEasingCurve.Type.InOutCirc'),
    (r'QEasingCurve\.\bOutInCirc\b',      'QEasingCurve.Type.OutInCirc'),
    (r'QEasingCurve\.\bInElastic\b',      'QEasingCurve.Type.InElastic'),
    (r'QEasingCurve\.\bOutElastic\b',     'QEasingCurve.Type.OutElastic'),
    (r'QEasingCurve\.\bInOutElastic\b',   'QEasingCurve.Type.InOutElastic'),
    (r'QEasingCurve\.\bOutInElastic\b',   'QEasingCurve.Type.OutInElastic'),
    (r'QEasingCurve\.\bInBack\b',         'QEasingCurve.Type.InBack'),
    (r'QEasingCurve\.\bOutBack\b',        'QEasingCurve.Type.OutBack'),
    (r'QEasingCurve\.\bInOutBack\b',      'QEasingCurve.Type.InOutBack'),
    (r'QEasingCurve\.\bOutInBack\b',      'QEasingCurve.Type.OutInBack'),
    (r'QEasingCurve\.\bInBounce\b',       'QEasingCurve.Type.InBounce'),
    (r'QEasingCurve\.\bOutBounce\b',      'QEasingCurve.Type.OutBounce'),
    (r'QEasingCurve\.\bInOutBounce\b',    'QEasingCurve.Type.InOutBounce'),
    (r'QEasingCurve\.\bOutInBounce\b',    'QEasingCurve.Type.OutInBounce'),

    # --- QgsMapLayerProxyModel ---
    (r'QgsMapLayerProxyModel\.\bPointLayer\b',           'QgsMapLayerProxyModel.Filter.PointLayer'),
    (r'QgsMapLayerProxyModel\.\bLineLayer\b',            'QgsMapLayerProxyModel.Filter.LineLayer'),
    (r'QgsMapLayerProxyModel\.\bPolygonLayer\b',         'QgsMapLayerProxyModel.Filter.PolygonLayer'),
    (r'QgsMapLayerProxyModel\.\bVectorLayer\b',          'QgsMapLayerProxyModel.Filter.VectorLayer'),
    (r'QgsMapLayerProxyModel\.\bRasterLayer\b',          'QgsMapLayerProxyModel.Filter.RasterLayer'),
    (r'QgsMapLayerProxyModel\.\bNoGeometry\b',           'QgsMapLayerProxyModel.Filter.NoGeometry'),
    (r'QgsMapLayerProxyModel\.\bHasGeometry\b',          'QgsMapLayerProxyModel.Filter.HasGeometry'),
    (r'QgsMapLayerProxyModel\.\bMeshLayer\b',            'QgsMapLayerProxyModel.Filter.MeshLayer'),

    # --- QgsWkbTypes (QGIS) ---
    (r'QgsWkbTypes\.\bPoint\b',              'QgsWkbTypes.GeometryType.Point'),
    (r'QgsWkbTypes\.\bLine\b',               'QgsWkbTypes.GeometryType.Line'),
    (r'QgsWkbTypes\.\bPolygon\b',            'QgsWkbTypes.GeometryType.Polygon'),
    (r'QgsWkbTypes\.\bMultiPoint\b',         'QgsWkbTypes.GeometryType.MultiPoint'),
    (r'QgsWkbTypes\.\bMultiLine\b',          'QgsWkbTypes.GeometryType.MultiLine'),
    (r'QgsWkbTypes\.\bMultiPolygon\b',       'QgsWkbTypes.GeometryType.MultiPolygon'),
    (r'QgsWkbTypes\.\bUnknownGeometry\b',    'QgsWkbTypes.GeometryType.UnknownGeometry'),
    (r'QgsWkbTypes\.\bNoGeometry\b',         'QgsWkbTypes.GeometryType.NoGeometry'),
    (r'QgsWkbTypes\.\bNullGeometry\b',       'QgsWkbTypes.GeometryType.NullGeometry'),
]


def find_python_files(root_dir: str) -> list:
    """Retorna lista de arquivos .py recursivamente."""
    py_files = []
    for root, dirs, files in os.walk(root_dir):
        # Ignora diretórios comuns que não devem ser escaneados
        dirs[:] = [d for d in dirs if not d.startswith(('.', '__pycache__', 'node_modules'))]
        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.join(root, f))
    return sorted(py_files)


def scan_file(filepath: str) -> list:
    """
    Escaneia um arquivo .py e retorna lista de tuplas:
    (linha, coluna, codigo_antigo, correcao_sugerida, linha_texto)
    """
    results = []
    filename = os.path.basename(filepath)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return [(0, 0, f"ERRO LEITURA: {e}", "", "")]

    for line_no, line in enumerate(lines, start=1):
        for pattern, correction in ENUM_PATTERNS:
            for match in re.finditer(pattern, line):
                col = match.start() + 1  # 1-based column
                old_code = match.group()
                # Pega um trecho da linha para contexto
                line_stripped = line.rstrip('\n\r')
                results.append((filepath, line_no, col, old_code, correction, line_stripped.strip()))

    return results


def generate_report(results: list, output_file: str, total_scanned: int):
    """Gera o arquivo de relatório txt."""
    
    # Agrupa resultados por arquivo
    from collections import defaultdict
    by_file = defaultdict(list)
    for r in results:
        by_file[r[0]].append(r)
    
    total_errors = len(results)
    total_files_with_errors = len(by_file)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 90 + "\n")
        f.write("RELATORIO DE VERIFICACAO DE ENUMS QT5/QT6\n")
        f.write(f"Gerado em: {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write("=" * 90 + "\n\n")
        
        f.write(f"Total de arquivos escaneados: {total_scanned}\n")
        f.write(f"Total de erros encontrados: {total_errors}\n")
        f.write(f"Total de arquivos com erros: {total_files_with_errors}\n\n")
        f.write("-" * 90 + "\n\n")
        
        if total_errors == 0:
            f.write("NENHUM ERRO DE ENUM QT ENCONTRADO!\n")
            f.write("Todos os enums estao no formato Qt6.\n\n")
            return
        
        for filepath in sorted(by_file.keys()):
            relpath = os.path.relpath(filepath, start=os.path.dirname(os.path.abspath(__file__)))
            # ou usa o caminho relativo ao projeto
            f.write(f"Arquivo: {relpath}\n")
            f.write("-" * 90 + "\n")
            
            file_results = by_file[filepath]
            for r in file_results:
                _, line_no, col, old_code, correction, line_text = r
                f.write(f"  Linha {line_no}, Coluna {col}\n")
                f.write(f"    Codigo antigo: {old_code}\n")
                f.write(f"    Sugestao:      {correction}\n")
                f.write(f"    Contexto:      {line_text}\n")
                f.write("\n")
            
            f.write("-" * 90 + "\n\n")
        
        # Resumo consolidado por tipo de erro
        f.write("\n" + "=" * 90 + "\n")
        f.write("RESUMO POR TIPO DE ENUM\n")
        f.write("=" * 90 + "\n\n")
        
        from collections import Counter
        type_counter = Counter()
        for r in results:
            _, _, _, old_code, correction, _ = r
            # Pega o prefixo do enum
            base = old_code.split('.')[0]
            type_counter[base] += 1
        
        for base, count in type_counter.most_common():
            f.write(f"  {base:<30s} {count:>4d} ocorrencias\n")
        
        f.write("\n")
        f.write("=" * 90 + "\n")
        f.write("FIM DO RELATORIO\n")
        f.write("=" * 90 + "\n")


if __name__ == '__main__':
    # Diretório raiz do projeto (assumindo que o script está na raiz)
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    print(f"Escaneando projeto em: {project_root}")
    print("Procurando arquivos .py...")
    
    all_files = find_python_files(project_root)
    print(f"Encontrados {len(all_files)} arquivos .py")
    
    print("Escaneando enums Qt...")
    all_results = []
    for i, filepath in enumerate(all_files):
        if i % 50 == 0 and i > 0:
            print(f"  Progresso: {i}/{len(all_files)} arquivos...")
        results = scan_file(filepath)
        all_results.extend(results)
    
    print(f"Escaneamento concluido. {len(all_results)} possiveis erros encontrados.")
    
    output_file = os.path.join(project_root, "qt_enum_errors_report.txt")
    generate_report(all_results, output_file, len(all_files))
    
    print(f"Relatorio gerado: {output_file}")
    print("Fim.")