"""Save the rebuilt armholes and preserve the current movement/combat clips."""
from pathlib import Path
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/import_uniform_v04.py').read_text(encoding='utf-8').replace('V04','V08')
src=src.replace('torso-only belt; no side pouches; front-only collar panels; continuous garment and trim weights',
    'Rebuilt oval armholes with shared torso/sleeve seam vertices and 12 graded sleeve-cap rings; V07 trouser cleanup retained')
src=src.replace('waist protrusion and garment spike repair; V03 zombie motions retained',
    'Axilla topology and upper-arm weighting rebuild; V06 zombie motions retained')
src=src.replace('Preserved existing V03 references and values','Preserved existing V06 references and values')
src=src.replace('Existing intact V03 body asset retained','Existing intact V06 body asset retained')
exec(compile(src,__file__,'exec'))
