from pathlib import Path
exec(compile((Path(__file__).parent.parent/'build_family.py').read_text(encoding='utf-8'),str(Path(__file__).parent.parent/'build_family.py'),'exec'))
