"""Search the full supported grip roll, preserving the accepted prop and hand."""
from pathlib import Path
O=Path(__file__).parent
source=O.parent/'Super90ContactR8_20261008/fit_loader_elbow.py'
code=source.read_text();code=code.replace("O=Path(__file__).parent;render=O/'render_saved.py'", "O=Path(__file__).parent;render=O.parent/'Super90ContactR8_20261008/render_saved.py'")
code=code.replace("itertools.product((75,90,105,120,135),(-20,0,20,30,40))", "itertools.product(range(-90,271,30),(-40,-20,0,20,40))")
code=code.replace("for f in (87,100,114,118,122)","for f in (87,100,114)")
code=code.replace("(O/'support_fit.json').write_text", "(O/'support_search.json').write_text")
exec(compile(code,__file__,'exec'))
