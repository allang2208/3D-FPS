from pathlib import Path
path=Path(__file__).parent/'render_refinement_grip.py'
code=path.read_text(encoding='utf-8').replace("OUT=ROOT/'Refinement20260922'","OUT=ROOT/'DrapeGrip20260922'")
exec(compile(code,str(path),'exec'))
