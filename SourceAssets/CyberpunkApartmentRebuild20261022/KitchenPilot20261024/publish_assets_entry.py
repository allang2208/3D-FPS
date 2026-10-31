"""One fresh-script invocation for MCP's retained Python host."""
from pathlib import Path
import runpy,sys
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R))
for name in list(sys.modules):
    if name.startswith('build_assets'):sys.modules.pop(name)
path=str(R/'build_assets.py')
exec(compile(Path(path).read_text(encoding='utf-8'),path,'exec'),{'__name__':'__main__','__file__':path})
print('KITCHEN_ENTRY_FINISHED',flush=True)
