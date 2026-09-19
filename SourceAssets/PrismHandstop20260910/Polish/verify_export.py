from pathlib import Path
P=Path(__file__).parent
exec(compile((P.parent/'verify_export.py').read_text(encoding='utf-8'),str(P/'verify_generated.py'),'exec'))
