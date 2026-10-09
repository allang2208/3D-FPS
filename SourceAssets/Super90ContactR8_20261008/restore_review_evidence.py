"""Restore R7 return data after the exploratory comparison reused its output."""
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];review=P/'Saved/Super90R7Review20261008'
script=review/'check_return.py';code=script.read_text()
code=code.replace("author.read_text().split('def local_rows(')[0]","Path(r'%s').read_text().split('def local_rows(')[0]"%(O/'Before/Source/author_speedloader.py'))
exec(compile(code,str(script),'exec'),{'__file__':str(script)})
