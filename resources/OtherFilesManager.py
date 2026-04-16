# -** coding: utf-8 -***-

import os


class OtherFilesManager:
    VECTOR_PATH = os.path.join(os.path.dirname(__file__), "vectors")
    LINE_VECTOR = 'line.gpkg'
    
    @classmethod
    def vector_path(cls, name: str) -> str:
        """
        Retorna o caminho completo do ícone a partir do nome do arquivo.
        """
        return os.path.join(cls.VECTOR_PATH, name)