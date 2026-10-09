"""Read the final UE poses and evaluate skin against the actual saved gun mesh."""
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];review=P/'Saved/Super90R7Review20261008'
code=(review/'check_surface.py').read_text();start=code.index('script=__file__');end=code.index('def cuts(')
render=O/'render_saved.py'
code=code[:start]+"exec(compile(Path(r'%s').read_text().split('items=[]')[0],r'%s','exec'))\n"%(render,render)+code[end:]
code=code.replace('surface_check.json','saved_surface_check.json')
exec(compile(code,__file__,'exec'),{'__file__':str(render),'Path':Path})
