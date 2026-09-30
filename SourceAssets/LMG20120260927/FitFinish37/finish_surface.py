"""Complete the shared micro-roughness layer without rebuilding installed meshes."""
from pathlib import Path
p=Path(__file__).parent/'materials.py'
exec(compile(p.read_text(),str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
