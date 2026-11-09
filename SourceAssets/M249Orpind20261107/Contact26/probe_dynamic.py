from pathlib import Path
r=Path(__file__).resolve().parent
source=(r/'probe.py').read_text().replace("[('vertical','idle',0),('prism','idle',0),('angled','idle',0),('vertical','side_reload_empty',2.985096),('angled','side_reload',3.245998)]","[('vertical','side_reload_empty',2.985096),('angled','side_reload',3.245998)]")
exec(compile(source,str(r/'probe.py'),'exec'))
