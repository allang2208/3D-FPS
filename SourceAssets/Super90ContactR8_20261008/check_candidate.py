from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];review=P/'Saved/Super90R7Review20261008'
code=(review/'check_surface.py').read_text()
start=code.index("script=__file__");end=code.index('def cuts(')
setup="exec(compile(Path(r'%s').read_text().split('items=[]')[0],r'%s','exec'))\nO=Path(r'%s')\n"%(review/'render_saved.py',review/'render_saved.py',O/'Diagnostics')
code=code[:start]+setup+code[end:]
code=code.replace("p=actual_pose(row);apply(p)","p=s['pose'](f,7,kind.startswith('empty'))[0];apply(p)")
code=code.replace("('empty_7',146)","('empty_7',139),('empty_7',146),('empty_7',158),('empty_7',165)")
ns={'__file__':str(review/'render_saved.py'),'Path':Path}
exec(compile(code,__file__,'exec'),ns)
