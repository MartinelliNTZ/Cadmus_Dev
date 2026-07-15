# -*- coding: utf-8 -*-
"""
Script para corrigir automaticamente todos os enums Qt5 -> Qt6
em todos os arquivos .py do projeto.

Uso:
    python fix_all_qt_enums.py
"""

import os
import re
import sys


# Mapeamento direto: regex pattern -> substituicao
REPLACEMENTS = [
    # Qt namespace enums -> fully qualified
    (r'Qt\.AlignLeft\b',        'Qt.AlignmentFlag.AlignLeft'),
    (r'Qt\.AlignRight\b',       'Qt.AlignmentFlag.AlignRight'),
    (r'Qt\.AlignHCenter\b',     'Qt.AlignmentFlag.AlignHCenter'),
    (r'Qt\.AlignTop\b',         'Qt.AlignmentFlag.AlignTop'),
    (r'Qt\.AlignBottom\b',      'Qt.AlignmentFlag.AlignBottom'),
    (r'Qt\.AlignVCenter\b',     'Qt.AlignmentFlag.AlignVCenter'),
    (r'Qt\.AlignCenter\b',      'Qt.AlignmentFlag.AlignCenter'),
    (r'Qt\.AlignJustify\b',     'Qt.AlignmentFlag.AlignJustify'),
    (r'Qt\.AlignAbsolute\b',    'Qt.AlignmentFlag.AlignAbsolute'),

    (r'Qt\.Checked\b',          'Qt.CheckState.Checked'),
    (r'Qt\.Unchecked\b',        'Qt.CheckState.Unchecked'),
    (r'Qt\.PartiallyChecked\b', 'Qt.CheckState.PartiallyChecked'),

    (r'Qt\.ScrollBarAsNeeded\b',   'Qt.ScrollBarPolicy.ScrollBarAsNeeded'),
    (r'Qt\.ScrollBarAlwaysOff\b',  'Qt.ScrollBarPolicy.ScrollBarAlwaysOff'),
    (r'Qt\.ScrollBarAlwaysOn\b',   'Qt.ScrollBarPolicy.ScrollBarAlwaysOn'),

    (r'Qt\.PointingHandCursor\b', 'Qt.CursorShape.PointingHandCursor'),
    (r'Qt\.ArrowCursor\b',        'Qt.CursorShape.ArrowCursor'),
    (r'Qt\.CrossCursor\b',        'Qt.CursorShape.CrossCursor'),
    (r'Qt\.WaitCursor\b',         'Qt.CursorShape.WaitCursor'),
    (r'Qt\.IBeamCursor\b',        'Qt.CursorShape.IBeamCursor'),
    (r'Qt\.SizeVerCursor\b',      'Qt.CursorShape.SizeVerCursor'),
    (r'Qt\.SizeHorCursor\b',      'Qt.CursorShape.SizeHorCursor'),
    (r'Qt\.SizeBDiagCursor\b',    'Qt.CursorShape.SizeBDiagCursor'),
    (r'Qt\.SizeFDiagCursor\b',    'Qt.CursorShape.SizeFDiagCursor'),
    (r'Qt\.SizeAllCursor\b',      'Qt.CursorShape.SizeAllCursor'),
    (r'Qt\.BlankCursor\b',        'Qt.CursorShape.BlankCursor'),
    (r'Qt\.BusyCursor\b',         'Qt.CursorShape.BusyCursor'),
    (r'Qt\.ForbiddenCursor\b',    'Qt.CursorShape.ForbiddenCursor'),
    (r'Qt\.OpenHandCursor\b',     'Qt.CursorShape.OpenHandCursor'),
    (r'Qt\.ClosedHandCursor\b',   'Qt.CursorShape.ClosedHandCursor'),
    (r'Qt\.WhatsThisCursor\b',    'Qt.CursorShape.WhatsThisCursor'),
    (r'Qt\.SplitHCursor\b',       'Qt.CursorShape.SplitHCursor'),
    (r'Qt\.SplitVCursor\b',       'Qt.CursorShape.SplitVCursor'),

    (r'Qt\.SmoothTransformation\b',       'Qt.TransformationMode.SmoothTransformation'),
    (r'Qt\.FastTransformation\b',         'Qt.TransformationMode.FastTransformation'),

    (r'Qt\.KeepAspectRatio\b',            'Qt.AspectRatioMode.KeepAspectRatio'),
    (r'Qt\.IgnoreAspectRatio\b',          'Qt.AspectRatioMode.IgnoreAspectRatio'),
    (r'Qt\.KeepAspectRatioByExpanding\b', 'Qt.AspectRatioMode.KeepAspectRatioByExpanding'),

    (r'Qt\.TransparentMode\b',  'Qt.BGMode.TransparentMode'),
    (r'Qt\.OpaqueMode\b',       'Qt.BGMode.OpaqueMode'),

    (r'Qt\.SolidLine\b',        'Qt.PenStyle.SolidLine'),
    (r'Qt\.DashLine\b',         'Qt.PenStyle.DashLine'),
    (r'Qt\.DotLine\b',          'Qt.PenStyle.DotLine'),
    (r'Qt\.DashDotLine\b',      'Qt.PenStyle.DashDotLine'),
    (r'Qt\.DashDotDotLine\b',   'Qt.PenStyle.DashDotDotLine'),
    (r'Qt\.NoPen\b',            'Qt.PenStyle.NoPen'),

    (r'Qt\.FlatCap\b',     'Qt.PenCapStyle.FlatCap'),
    (r'Qt\.SquareCap\b',   'Qt.PenCapStyle.SquareCap'),
    (r'Qt\.RoundCap\b',    'Qt.PenCapStyle.RoundCap'),

    (r'Qt\.MiterJoin\b',   'Qt.PenJoinStyle.MiterJoin'),
    (r'Qt\.BevelJoin\b',   'Qt.PenJoinStyle.BevelJoin'),
    (r'Qt\.RoundJoin\b',   'Qt.PenJoinStyle.RoundJoin'),

    (r'Qt\.NoBrush\b',     'Qt.BrushStyle.NoBrush'),
    (r'Qt\.SolidPattern\b','Qt.BrushStyle.SolidPattern'),

    (r'Qt\.Horizontal\b',   'Qt.Orientation.Horizontal'),
    (r'Qt\.Vertical\b',     'Qt.Orientation.Vertical'),

    (r'Qt\.LeftButton\b',   'Qt.MouseButton.LeftButton'),
    (r'Qt\.RightButton\b',  'Qt.MouseButton.RightButton'),
    (r'Qt\.MiddleButton\b', 'Qt.MouseButton.MiddleButton'),
    (r'Qt\.NoButton\b',     'Qt.MouseButton.NoButton'),

    (r'Qt\.ControlModifier\b',   'Qt.KeyboardModifier.ControlModifier'),
    (r'Qt\.ShiftModifier\b',     'Qt.KeyboardModifier.ShiftModifier'),
    (r'Qt\.AltModifier\b',       'Qt.KeyboardModifier.AltModifier'),
    (r'Qt\.NoModifier\b',        'Qt.KeyboardModifier.NoModifier'),
    (r'Qt\.MetaModifier\b',      'Qt.KeyboardModifier.MetaModifier'),
    (r'Qt\.GroupSwitchModifier\b','Qt.KeyboardModifier.GroupSwitchModifier'),
    (r'Qt\.KeypadModifier\b',    'Qt.KeyboardModifier.KeypadModifier'),

    # QSizePolicy
    (r'QSizePolicy\.Fixed\b',           'QSizePolicy.Policy.Fixed'),
    (r'QSizePolicy\.Minimum\b',         'QSizePolicy.Policy.Minimum'),
    (r'QSizePolicy\.Maximum\b',         'QSizePolicy.Policy.Maximum'),
    (r'QSizePolicy\.Preferred\b',       'QSizePolicy.Policy.Preferred'),
    (r'QSizePolicy\.Expanding\b',       'QSizePolicy.Policy.Expanding'),
    (r'QSizePolicy\.MinimumExpanding\b','QSizePolicy.Policy.MinimumExpanding'),
    (r'QSizePolicy\.Ignored\b',         'QSizePolicy.Policy.Ignored'),

    # QFrame / QScrollArea
    (r'QFrame\.NoFrame\b',      'QFrame.Shape.NoFrame'),
    (r'QFrame\.Box\b',          'QFrame.Shape.Box'),
    (r'QFrame\.Panel\b',        'QFrame.Shape.Panel'),
    (r'QFrame\.StyledPanel\b',  'QFrame.Shape.StyledPanel'),
    (r'QFrame\.HLine\b',        'QFrame.Shape.HLine'),
    (r'QFrame\.VLine\b',        'QFrame.Shape.VLine'),
    (r'QFrame\.WinPanel\b',     'QFrame.Shape.WinPanel'),

    (r'QFrame\.Plain\b',        'QFrame.Shadow.Plain'),
    (r'QFrame\.Raised\b',       'QFrame.Shadow.Raised'),
    (r'QFrame\.Sunken\b',       'QFrame.Shadow.Sunken'),

    # QDialog
    (r'(?<![a-zA-Z.])QDialog\.Accepted\b',   'QDialog.DialogCode.Accepted'),
    (r'(?<![a-zA-Z.])QDialog\.Rejected\b',   'QDialog.DialogCode.Rejected'),

    # QListWidget
    (r'QListWidget\.SingleSelection\b',     'QListWidget.SelectionMode.SingleSelection'),
    (r'QListWidget\.ContiguousSelection\b', 'QListWidget.SelectionMode.ContiguousSelection'),
    (r'QListWidget\.ExtendedSelection\b',   'QListWidget.SelectionMode.ExtendedSelection'),
    (r'QListWidget\.MultiSelection\b',      'QListWidget.SelectionMode.MultiSelection'),
    (r'QListWidget\.NoSelection\b',         'QListWidget.SelectionMode.NoSelection'),

    # QAbstractItemView
    (r'QAbstractItemView\.SingleSelection\b',     'QAbstractItemView.SelectionMode.SingleSelection'),
    (r'QAbstractItemView\.ContiguousSelection\b', 'QAbstractItemView.SelectionMode.ContiguousSelection'),
    (r'QAbstractItemView\.ExtendedSelection\b',   'QAbstractItemView.SelectionMode.ExtendedSelection'),
    (r'QAbstractItemView\.MultiSelection\b',      'QAbstractItemView.SelectionMode.MultiSelection'),
    (r'QAbstractItemView\.NoSelection\b',         'QAbstractItemView.SelectionMode.NoSelection'),
    (r'QAbstractItemView\.SelectRows\b',          'QAbstractItemView.SelectionBehavior.SelectRows'),

    # QColor
    (r'QColor\.HexArgb\b',   'QColor.NameFormat.HexArgb'),
    (r'QColor\.HexRgb\b',    'QColor.NameFormat.HexRgb'),

    # QEasingCurve
    (r'QEasingCurve\.Linear\b',         'QEasingCurve.Type.Linear'),
    (r'QEasingCurve\.InQuad\b',         'QEasingCurve.Type.InQuad'),
    (r'QEasingCurve\.OutQuad\b',        'QEasingCurve.Type.OutQuad'),
    (r'QEasingCurve\.InOutQuad\b',      'QEasingCurve.Type.InOutQuad'),
    (r'QEasingCurve\.OutInQuad\b',      'QEasingCurve.Type.OutInQuad'),
    (r'QEasingCurve\.InCubic\b',        'QEasingCurve.Type.InCubic'),
    (r'QEasingCurve\.OutCubic\b',       'QEasingCurve.Type.OutCubic'),
    (r'QEasingCurve\.InOutCubic\b',     'QEasingCurve.Type.InOutCubic'),
    (r'QEasingCurve\.OutInCubic\b',     'QEasingCurve.Type.OutInCubic'),
    (r'QEasingCurve\.InQuart\b',        'QEasingCurve.Type.InQuart'),
    (r'QEasingCurve\.OutQuart\b',       'QEasingCurve.Type.OutQuart'),
    (r'QEasingCurve\.InOutQuart\b',     'QEasingCurve.Type.InOutQuart'),
    (r'QEasingCurve\.OutInQuart\b',     'QEasingCurve.Type.OutInQuart'),
    (r'QEasingCurve\.InQuint\b',        'QEasingCurve.Type.InQuint'),
    (r'QEasingCurve\.OutQuint\b',       'QEasingCurve.Type.OutQuint'),
    (r'QEasingCurve\.InOutQuint\b',     'QEasingCurve.Type.InOutQuint'),
    (r'QEasingCurve\.OutInQuint\b',     'QEasingCurve.Type.OutInQuint'),
    (r'QEasingCurve\.InSine\b',         'QEasingCurve.Type.InSine'),
    (r'QEasingCurve\.OutSine\b',        'QEasingCurve.Type.OutSine'),
    (r'QEasingCurve\.InOutSine\b',      'QEasingCurve.Type.InOutSine'),
    (r'QEasingCurve\.OutInSine\b',      'QEasingCurve.Type.OutInSine'),
    (r'QEasingCurve\.InExpo\b',         'QEasingCurve.Type.InExpo'),
    (r'QEasingCurve\.OutExpo\b',        'QEasingCurve.Type.OutExpo'),
    (r'QEasingCurve\.InOutExpo\b',      'QEasingCurve.Type.InOutExpo'),
    (r'QEasingCurve\.OutInExpo\b',      'QEasingCurve.Type.OutInExpo'),
    (r'QEasingCurve\.InCirc\b',         'QEasingCurve.Type.InCirc'),
    (r'QEasingCurve\.OutCirc\b',        'QEasingCurve.Type.OutCirc'),
    (r'QEasingCurve\.InOutCirc\b',      'QEasingCurve.Type.InOutCirc'),
    (r'QEasingCurve\.OutInCirc\b',      'QEasingCurve.Type.OutInCirc'),
    (r'QEasingCurve\.InElastic\b',      'QEasingCurve.Type.InElastic'),
    (r'QEasingCurve\.OutElastic\b',     'QEasingCurve.Type.OutElastic'),
    (r'QEasingCurve\.InOutElastic\b',   'QEasingCurve.Type.InOutElastic'),
    (r'QEasingCurve\.OutInElastic\b',   'QEasingCurve.Type.OutInElastic'),
    (r'QEasingCurve\.InBack\b',         'QEasingCurve.Type.InBack'),
    (r'QEasingCurve\.OutBack\b',        'QEasingCurve.Type.OutBack'),
    (r'QEasingCurve\.InOutBack\b',      'QEasingCurve.Type.InOutBack'),
    (r'QEasingCurve\.OutInBack\b',      'QEasingCurve.Type.OutInBack'),
    (r'QEasingCurve\.InBounce\b',       'QEasingCurve.Type.InBounce'),
    (r'QEasingCurve\.OutBounce\b',      'QEasingCurve.Type.OutBounce'),
    (r'QEasingCurve\.InOutBounce\b',    'QEasingCurve.Type.InOutBounce'),
    (r'QEasingCurve\.OutInBounce\b',    'QEasingCurve.Type.OutInBounce'),

    # QgsMapLayerProxyModel
    (r'QgsMapLayerProxyModel\.PointLayer\b',           'QgsMapLayerProxyModel.Filter.PointLayer'),
    (r'QgsMapLayerProxyModel\.LineLayer\b',            'QgsMapLayerProxyModel.Filter.LineLayer'),
    (r'QgsMapLayerProxyModel\.PolygonLayer\b',         'QgsMapLayerProxyModel.Filter.PolygonLayer'),
    (r'QgsMapLayerProxyModel\.VectorLayer\b',          'QgsMapLayerProxyModel.Filter.VectorLayer'),
    (r'QgsMapLayerProxyModel\.RasterLayer\b',          'QgsMapLayerProxyModel.Filter.RasterLayer'),
    (r'QgsMapLayerProxyModel\.NoGeometry\b',           'QgsMapLayerProxyModel.Filter.NoGeometry'),
    (r'QgsMapLayerProxyModel\.HasGeometry\b',          'QgsMapLayerProxyModel.Filter.HasGeometry'),
    (r'QgsMapLayerProxyModel\.MeshLayer\b',            'QgsMapLayerProxyModel.Filter.MeshLayer'),

    # QgsWkbTypes
    (r'QgsWkbTypes\.Point\b',              'QgsWkbTypes.GeometryType.Point'),
    (r'QgsWkbTypes\.Line\b',               'QgsWkbTypes.GeometryType.Line'),
    (r'QgsWkbTypes\.Polygon\b',            'QgsWkbTypes.GeometryType.Polygon'),
    (r'QgsWkbTypes\.MultiPoint\b',         'QgsWkbTypes.GeometryType.MultiPoint'),
    (r'QgsWkbTypes\.MultiLine\b',          'QgsWkbTypes.GeometryType.MultiLine'),
    (r'QgsWkbTypes\.MultiPolygon\b',       'QgsWkbTypes.GeometryType.MultiPolygon'),
    (r'QgsWkbTypes\.UnknownGeometry\b',    'QgsWkbTypes.GeometryType.UnknownGeometry'),
    (r'QgsWkbTypes\.NoGeometry\b',         'QgsWkbTypes.GeometryType.NoGeometry'),
    (r'QgsWkbTypes\.NullGeometry\b',       'QgsWkbTypes.GeometryType.NullGeometry'),
]

# Esses padroes NAO devem ser substituidos (sao importacoes ou assinaturas de tipo)
# Importante: isso so exclui LINHAS INTEIRAS que sao exclusivamente imports/type hints
EXCLUDE_PATTERNS = [
    r'^from\s+qgis\.PyQt',
    r'^import\s+qgis\.PyQt',
]


def should_exclude(line: str) -> bool:
    """Verifica se a linha deve ser ignorada (import, type hint, etc)."""
    for pat in EXCLUDE_PATTERNS:
        if re.search(pat, line):
            return True
    return False


def fix_file(filepath: str) -> tuple:
    """
    Corrige enums em um arquivo.
    Retorna (modified: bool, changes: list)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines(keepends=True)
    except Exception as e:
        return False, [f"ERRO LEITURA: {e}"]

    modified = False
    changes = []

    new_lines = []
    for line_no, line in enumerate(lines, start=1):
        original_line = line
        if should_exclude(line):
            new_lines.append(line)
            continue
        
        # Aplica todas as substituicoes
        for pattern, replacement in REPLACEMENTS:
            new_line, count = re.subn(pattern, replacement, line)
            if count > 0:
                for m in re.finditer(pattern, line):
                    changes.append((line_no, m.group(), replacement, line.strip()))
                line = new_line
                modified = True
        
        new_lines.append(line)

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    return modified, changes


def find_python_files(root_dir: str) -> list:
    """Retorna lista de arquivos .py recursivamente."""
    py_files = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if not d.startswith(('.', '__pycache__', 'node_modules'))]
        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.join(root, f))
    return sorted(py_files)


if __name__ == '__main__':
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    print(f"Escaneando e corrigindo projeto em: {project_root}")
    
    all_files = find_python_files(project_root)
    print(f"Encontrados {len(all_files)} arquivos .py")
    
    total_changes = 0
    modified_files = 0
    
    report_lines = []
    report_lines.append("=" * 90)
    report_lines.append("RELATORIO DE CORRECAO DE ENUMS QT5/QT6")
    report_lines.append(f"Gerado em: {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    report_lines.append("=" * 90)
    report_lines.append("")
    
    for i, filepath in enumerate(all_files):
        if i % 50 == 0 and i > 0:
            print(f"  Progresso: {i}/{len(all_files)} arquivos...")
        
        modified, changes = fix_file(filepath)
        if modified:
            relpath = os.path.relpath(filepath, project_root)
            modified_files += 1
            total_changes += len(changes)
            
            report_lines.append(f"Arquivo: {relpath}")
            report_lines.append("-" * 90)
            for line_no, old, new, context in changes:
                report_lines.append(f"  Linha {line_no}: {old} -> {new}")
                report_lines.append(f"    Contexto: {context}")
            report_lines.append("")
    
    report_lines.append("=" * 90)
    report_lines.append(f"Total de arquivos modificados: {modified_files}")
    report_lines.append(f"Total de correcoes aplicadas: {total_changes}")
    report_lines.append("=" * 90)
    
    # Salva relatorio
    report_path = os.path.join(project_root, "qt_enum_fix_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\nConcluido!")
    print(f"Arquivos modificados: {modified_files}")
    print(f"Correcoes aplicadas: {total_changes}")
    print(f"Relatorio salvo em: {report_path}")