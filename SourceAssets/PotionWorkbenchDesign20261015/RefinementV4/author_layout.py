"""Measure the authored utensils and make their physical countertop rests. No render."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
BASE=ROOT.parent
sys.path.insert(0,str(BASE/'ModelV1/Scripts'))
import geometry as g
bpy.ops.wm.open_mainfile(filepath=str(BASE/'RuntimeV2/Authored/PotionWorkbench_Runtime.blend'),load_ui=False,use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
g.MATS['atlas']=bpy.data.materials['PW_SurfaceAtlas']
deps=bpy.context.evaluated_depsgraph_get()
def points(component):
    out=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH' or ob.get('component')!=component:continue
        ev=ob.evaluated_get(deps);me=ev.to_mesh()
        out.extend(ev.matrix_world@v.co for v in me.vertices);ev.to_mesh_clear()
    if not out:raise RuntimeError('Missing authored component '+component)
    return out
top=94.43
local={name:points('SM_Alchemy'+name) for name in ('Stirrer','Ladle','Dose','Hourglass')}
rests={}
for name,y in [('Stirrer',-29.),('Ladle',-60.)]:
    z=top-min(v.x for v in local[name])
    rests[name]=[148.,y,z]
rests['Dose']=[145.,-45.,top-min(v.z for v in local['Dose'])]
rests['Hourglass']=[164.,-45.,top-min(v.z for v in local['Hourglass'])]
layout={'table_top_cm':top,'rests':rests,'stir_pickup_seconds':.6,'return_seconds':.45,
        'mortar':[45,-50,100],'book':[118,-45,94.43],'cauldron':[225,-106,119.05]}
(ROOT/'layout.json').write_text(json.dumps(layout,indent=2),encoding='utf-8')
header='#pragma once\n#include "CoreMinimal.h"\n// Generated from the authored mesh contact surfaces by RefinementV4/author_layout.py.\nnamespace AlchemyLayout\n{\n'
header+=f'inline constexpr float PrepTop={top:.8f}f;\ninline constexpr float StirPickupSeconds=.6f;\n'
for name,xyz in rests.items():header+=f'inline const FVector {name}Rest({xyz[0]:.8f},{xyz[1]:.8f},{xyz[2]:.8f});\n'
header+='inline const FQuat ToolRestRotation=FRotator(90,0,0).Quaternion();\ninline const FVector Book(118,-45,PrepTop);\ninline const FVector Cauldron(225,-106,119.05);\ninline const FVector Mortar(45,-50,100);\n}\n'
(PROJECT/'Source/FPSGAME/Building/AlchemyWorkbenchLayout.h').write_text(header,encoding='utf-8')

g.group('ToolRests')
for name,radius in [('Stirrer',.72),('Ladle',.73)]:
    x,y,z=rests[name];x-=4;y=-y
    height=z-radius-top
    g.box(name+' ceramic saddle',(x,y,top+height/2),(3,3.6,height),'ceramic',.12)
    for sign in (-1,1):g.box(name+' saddle shoulder',(x,y+sign*1.45,top+height+.38),(3,.55,.76),'ceramic',.12)
    g.box(name+' brass foot',(x,y,top+.08),(3.2,3.8,.16),'brass',.05)
new=list(g.PARTS)
bpy.ops.object.select_all(action='DESELECT')
for ob in new:ob.select_set(True)
bpy.context.view_layer.objects.active=new[0]
bpy.ops.object.convert(target='MESH');bpy.ops.object.join()
obj=bpy.context.object;obj.name='SM_AlchemyToolRests'
bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
# All parts share the original surface atlas; collapse duplicate slots only.
obj.data.materials.clear();obj.data.materials.append(g.MATS['atlas'])
for face in obj.data.polygons:face.material_index=0
(ROOT/'Export').mkdir(exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/SM_AlchemyToolRests.fbx'),use_selection=True,object_types={'MESH'},
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,path_mode='STRIP')
for ob in list(bpy.context.scene.objects):
    if ob!=obj:bpy.data.objects.remove(ob,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'AlchemyToolRests.blend'))

# Requested geometry inspection: actual authored vertices at the final UE rest pose.
checks=[];boxes={}
for name,vertices in local.items():
    origin=Vector(rests[name]);flat=name in ('Stirrer','Ladle')
    placed=[origin+(Vector((-p.z,-p.y,p.x)) if flat else Vector((p.x,-p.y,p.z))) for p in vertices]
    lo=[min(v[i] for v in placed) for i in range(3)];hi=[max(v[i] for v in placed) for i in range(3)]
    boxes[name]=(lo,hi)
    checks.append({'part':name,'bounds_cm':[lo,hi],'table_contact_gap_cm':lo[2]-top,
        'on_main_counter':lo[0]>=0 and hi[0]<=260 and lo[1]>=-70 and hi[1]<=0,
        'contact_ok':abs(lo[2]-top)<.001})
boxes['UtensilCup']=([178.8,-39.2,94],[187.2,-30.8,108.3])
boxes['OpenBook']=([102.481,-57.093,top],[133.519,-32.907,top+4])
overlaps=[]
for i,a in enumerate(boxes):
    for b in list(boxes)[i+1:]:
        if all(min(boxes[a][1][k],boxes[b][1][k])-max(boxes[a][0][k],boxes[b][0][k])>0 for k in (0,1)):
            overlaps.append([a,b])
report={'checks':checks,'xy_overlaps':overlaps,'old_hourglass_cup_center_distance_cm':math.hypot(181-183,-38+35),
        'new_hourglass_cup_center_distance_cm':math.hypot(164-183,-45+35),'rendered':False,'runtime_tested':False}
(ROOT/'geometry-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if overlaps or not all(c['contact_ok'] and c['on_main_counter'] for c in checks):raise RuntimeError('Countertop layout inspection failed')
print('ALCHEMY_LAYOUT_SAVED '+json.dumps(report),flush=True)
