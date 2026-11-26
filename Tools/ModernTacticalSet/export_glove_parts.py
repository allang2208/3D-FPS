"""Export the existing editable shell and protection parts independently."""
import sys,bpy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import prepare_delivery as io
for part in ['foundation','details']:
    bpy.ops.wm.open_mainfile(filepath=str(io.S/'Models/03_TacticalGloves.blend'))
    for ob in list(bpy.context.scene.objects):
        replaced=part=='details' and ob.name.startswith(('DorsalYoke_','SuedePalmReinforcement_','WristClosureStitch_'))
        if ob.type=='MESH' and (replaced or (ob.name=='Gloves_ContinuousNativeShell')!=(part=='foundation')):
            bpy.data.objects.remove(ob,do_unlink=True)
    ob=io.combine();d=io.export(ob);io.write(io.D/f'gloves_{part}_Jason.json',d)
    print('TS01_GLOVE_PART',part,len(d['positions']),flush=True)
