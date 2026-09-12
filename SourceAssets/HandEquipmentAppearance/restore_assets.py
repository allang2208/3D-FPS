"""Explicit full local rebuild from licensed sources and baked authoring maps."""
from pathlib import Path
OUT=Path(__file__).parent
for name in ('import_leather_textures.py','build_sleeve.py','build_material.py','apply_standard.py','verify_saved.py'):
    path=OUT/name
    exec(compile(path.read_text(),str(path),'exec'),{'__file__':str(path),'__name__':'__main__'})
