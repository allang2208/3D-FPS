"""Extend the approved Denys pipeline; preserve authored motion and skin topology."""
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'modern-zombie-v01-20260906'
variant=sys.argv[sys.argv.index('--')+1]
assert variant in ('miner','runner')
OUT=HERE/variant;OUT.mkdir(exist_ok=True)
snapshot=HERE/'base_pipeline.py'
if not snapshot.exists():snapshot.write_text((SOURCE/'build_modern_zombie.py').read_text(),encoding='utf8')
code=snapshot.read_text()
def change(old,new):
 global code
 assert old in code,old
 code=code.replace(old,new)
change('R=Path(__file__).resolve().parent',f'R=Path({str(OUT)!r}); SOURCE=Path({str(SOURCE)!r})')
change("R/'denys-A-motions.gltf'","SOURCE/'denys-A-motions.gltf'")
change("R/'ual-mannequin.glb'","SOURCE/'ual-mannequin.glb'")
change("alias('walk_limp_60f','Walk')",f"alias({'slowWalk_85f' if variant=='miner' else 'running_58f'!r},'Walk')")
change('for frame in range(61):','for frame in range(round(bpy.data.actions[\'Walk\'].frame_range[1])+1):')
change('if .08<speed<1.5:', 'if .04<speed<6.0:')
change("regions=['Skin','Shirt','Trousers','Hair','Leather','DriedBlood','Eyes']", "regions=['Skin','Shirt','Trousers','Hair','Leather','DriedBlood','Eyes','HardHat','Reflective','Metal','Lamp']")
change("face_regions.append(regions.index(region))", """if region=='DriedBlood' and abs(co.x)<5 and 96<co.z<134:region='Shirt'
 if VARIANT=='runner' and region=='Shirt' and abs(co.x)>25 and co.z>127:region='Skin'
 face_regions.append(regions.index(region))""")
code='VARIANT='+repr(variant)+'\n'+code
hook=(HERE/'geometry_hook.py').read_text()
change("bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body",hook+"\nbpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body")
change('channels=[];materials=list(body.data.materials)', """base.update({'HardHat':((.11,.068,.012),(.38,.25,.055),.65),'Reflective':((.22,.25,.18),(.52,.56,.39),.42),'Metal':((.012,.019,.023),(.045,.058,.06),.6),'Lamp':((.55,.42,.16),(.85,.75,.45),.27)})
if VARIANT=='miner':
 base.update({'Shirt':((.045,.017,.004),(.24,.09,.015),.93),'Trousers':((.012,.02,.028),(.042,.057,.072),.94),'Skin':((.035,.051,.044),(.20,.23,.17),.80)})
else:
 base.update({'Shirt':((.027,.006,.008),(.11,.035,.041),.95),'Trousers':((.014,.021,.026),(.05,.068,.079),.90),'Skin':((.10,.095,.068),(.38,.35,.25),.74),'DriedBlood':((.018,.002,.003),(.14,.018,.015),.63)})
channels=[];materials=list(body.data.materials)""")
change("'ModernZombie_'+", "VARIANT+'_'+")
change("'ModernZombie_PBR'", "VARIANT+'_PBR'")
change("body.name='ModernZombie'", "body.name=VARIANT.title()+'Zombie'")
change("'modern-zombie-v01.blend'", "(VARIANT+'-zombie-v01.blend')")
change("'modern-zombie-v01.glb'", "(VARIANT+'-zombie-v01.glb')")
# Save the generated execution source so this build can be reviewed independently.
(OUT/'resolved_pipeline.py').write_text(code,encoding='utf8')
exec(compile(code,str(OUT/'resolved_pipeline.py'),'exec'),{'__file__':str(OUT/'resolved_pipeline.py')})
