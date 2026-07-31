# -*- coding: utf-8 -*-
"""Corrige W503 restante no GridComplexSelector."""
import io

path = "resources/new_widgets/grid/GridComplexSelector.py"
with io.open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = (
    '            # Features/checked state\n'
    '            if self._link_meta.get(key, {}).get("allow_features_check", False) or \\\n'
    "               hasattr(sel, '_allow_features_check') and sel._allow_features_check:\n"
    '                item["checked_state"] = sel.get_checked_state()\n'
)
new = (
    '            # Features/checked state\n'
    '            has_features = bool(\n'
    '                self._link_meta.get(key, {}).get("allow_features_check", False)\n'
    "                or getattr(sel, '_allow_features_check', False)\n"
    "                and sel._allow_features_check\n"
    '            )\n'
    '            if has_features:\n'
    '                item["checked_state"] = sel.get_checked_state()\n'
)

if old in content:
    content = content.replace(old, new, 1)
    print("W503 allow_features_check corrigido")
else:
    print("W503 allow_features_check NAO encontrado")
    # Mostrar trecho para debug
    idx = content.find("allow_features_check")
    if idx != -1:
        print(repr(content[idx-100:idx+200]))

with io.open(path, "w", encoding="utf-8") as f:
    f.write(content)