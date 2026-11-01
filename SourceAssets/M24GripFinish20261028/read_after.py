from pathlib import Path
O=Path(__file__).resolve().parent
code=(O/'read_assets.py').read_text()
code=code.replace("exec(compile(code,str(old/'read_assets.py'),'exec'))", "code=code.replace('ue_before.json','ue_after.json').replace('frames=list(range(count))', 'frames=sorted({0,count-1,*[f for f in (7,10,16,24,35,43,52,59,77,95,104) if f<count]})');exec(compile(code,str(old/'read_assets.py'),'exec'))")
exec(compile(code,'read_saved_layers','exec'))
