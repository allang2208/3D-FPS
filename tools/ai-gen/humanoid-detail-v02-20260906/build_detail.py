"""Detail revision of the accepted humanoid family, preserving action curves."""
import sys,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
kind=sys.argv[sys.argv.index('--')+1]
assert kind in ('modern','miner','runner')
OUT=HERE/kind;OUT.mkdir(exist_ok=True)
source=(HERE.parent/'modern-zombie-v01-20260906/build_modern_zombie.py') if kind=='modern' else HERE.parent/'humanoid-variants-v01-20260906'/kind/'resolved_pipeline.py'
snapshot=OUT/'source_pipeline.py'
if not snapshot.exists():snapshot.write_text(source.read_text(),encoding='utf8')
code=snapshot.read_text()
original=HERE.parent/'modern-zombie-v01-20260906'
if kind=='modern':
 code=code.replace('R=Path(__file__).resolve().parent',f'R=Path({str(OUT)!r}); SOURCE=Path({str(original)!r})')
 code=code.replace("R/'denys-A-motions.gltf'","SOURCE/'denys-A-motions.gltf'").replace("R/'ual-mannequin.glb'","SOURCE/'ual-mannequin.glb'")
 code='VARIANT="modern"\n'+code
else:
 code=re.sub(r'^R=Path\([^\n]+',lambda _:f'R=Path({str(OUT)!r}); SOURCE=Path({str(original)!r})',code,count=1,flags=re.M)
def replace(old,new):
 global code
 assert old in code,old
 code=code.replace(old,new)
replace('face_regions=[]',"regions += ['Tie']\nface_regions=[]")
hook=(HERE/'detail_geometry.py').read_text()
anchor="# Executed inside the baseline pipeline" if kind!='modern' else "bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body"
assert anchor in code
code=code.replace(anchor,hook+'\n'+anchor,1)
replace("base={'Skin':", "base={'Skin':")
replace('channels=[];materials=list(body.data.materials)',"""base.update({'Tie':((.028,.007,.009),(.10,.025,.025),.87)})
# Reduce the broad speckled noise of V01; microdetail is added separately below.
base['Skin']=((.11,.125,.095),(.24,.265,.19),.78) if VARIANT!='runner' else ((.15,.14,.105),(.30,.29,.22),.77)
channels=[];materials=list(body.data.materials)""")
replace("bump.inputs['Distance'].default_value=.11 if region=='Skin' else .18", "bump.inputs['Distance'].default_value=.016 if region=='Skin' else .035")
replace("channels.append((color,scalar.outputs[0],bs,output))",(HERE/'detail_material.py').read_text()+"\n channels.append((color,rough_output,bs,output))")
if kind=='modern':
 replace("'modern-zombie-v01.blend'","'modern-zombie-v02.blend'");replace("'modern-zombie-v01.glb'","'modern-zombie-v02.glb'")
else:
 replace("'-zombie-v01.blend'","'-zombie-v02.blend'");replace("'-zombie-v01.glb'","'-zombie-v02.glb'")
replace("(R/'build-report.json').write_text", "report['detail']=detail_report\n(R/'build-report.json').write_text")
(OUT/'resolved_pipeline.py').write_text(code,encoding='utf8')
exec(compile(code,str(OUT/'resolved_pipeline.py'),'exec'),{'__file__':str(OUT/'resolved_pipeline.py')})
