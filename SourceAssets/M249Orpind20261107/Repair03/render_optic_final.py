from pathlib import Path
script=Path(__file__).parents[1]/'Repair02/render_optic_final.py'
exec(compile(script.read_text(encoding='utf8'),str(script),'exec'))
