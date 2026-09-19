from pathlib import Path
exec(compile((Path(__file__).parent.parent/'build_family.py').read_text(),str(Path(__file__).parent.parent/'build_family.py'),'exec'))
