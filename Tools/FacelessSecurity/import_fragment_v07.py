"""Import the fragment-free assembly without replacing current animations."""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/import_uniform_v04.py').read_text(encoding='utf-8').replace('V04','V07')
src=src.replace('torso-only belt; no side pouches; front-only collar panels; continuous garment and trim weights',
    'Removed two disconnected trousers islands: 182 vertices / 356 triangles; remaining garment data preserved')
src=src.replace('waist protrusion and garment spike repair; V03 zombie motions retained',
    'Remove pelvis-bound loose triangles embedded inside trousers; V06 geometry and motions otherwise retained')
src=src.replace('Preserved existing V03 references and values','Preserved existing V06 references and values')
src=src.replace('Existing intact V03 body asset retained','Existing intact V06 body asset retained')
exec(compile(src,__file__,'exec'))
