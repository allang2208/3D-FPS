"""Read the requested device dimensions after the base DLL was rebuilt."""
import json
from pathlib import Path
p=Path(__file__).parent/'diagnose_scale.py'
source=p.read_text().replace('scale_before.json','scale_after_regular_build.json')
exec(compile(source,str(p),'exec'),{'__file__':str(p),'print':lambda *args:None})
result=json.loads((p.parent/'scale_after_regular_build.json').read_text())
print('FINAL_ACTORS',result['actors'])
print('FINAL_LENGTHS_CM',result['assets']['laser_ash']['size_cm'][0],result['assets']['flashlight_ash']['size_cm'][0])
