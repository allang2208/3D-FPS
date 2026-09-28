"""Place existing workshop tools verbatim on the cleared gun workbench."""
import bpy,json,math,re
from pathlib import Path
from mathutils import Matrix,Vector

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/GunWorkbenchLibraryTools20260928'
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE=PROJECT/'SourceAssets/GunWorkbenchCleared20260928/Authored'
KIT=PROJECT/'SourceAssets/DungeonWorkbenchKit20260921'
base_manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
kit_manifest=json.loads((KIT/'Authored/manifest.json').read_text(encoding='utf-8'))
kit_assets=json.loads((KIT/'Receipts/asset-import.json').read_text(encoding='utf-8'))
components={e['id']:e for e in kit_manifest['components']}

# Metres; original dimensions are retained. Only the existing wall hammer is laid flat.
layout=[
    {'id':'Fab_Bench_Screwdriver','center':[-.74,-.84],'yaw':90,'lay_flat':False},
    {'id':'Fab_Bench_Pliers','center':[-.43,-1.015],'yaw':78,'lay_flat':False},
    {'id':'Fab_Bench_Wrench','center':[-.055,-.835],'yaw':92,'lay_flat':False},
    {'id':'Fab_Wall_Hammer','center':[-.43,-1.20],'yaw':0,'lay_flat':True},
    {'id':'Bottle_OilCan','center':[-1.055,-1.105],'yaw':-12,'lay_flat':False},
]
bpy.ops.wm.open_mainfile(filepath=str(BASE/'GunWorkbench_Editable.blend'))
names=[components[item['id']]['name'] for item in layout]
with bpy.data.libraries.load(str(KIT/'Authored/DungeonWorkbenchKit.blend'),link=False) as (source,target):
    target.objects=list(names)
bindings={};copies=[]
for obj,item in zip(target.objects,layout):
    if obj is None:raise RuntimeError('Existing tool object missing: '+item['id'])
    bpy.context.scene.collection.objects.link(obj);obj.hide_set(False);bpy.context.view_layer.update()
    source_matrix=obj.matrix_world.copy();obj.parent=None
    turn=Matrix.Rotation(math.radians(item['yaw']),4,'Z')
    if item['lay_flat']:turn=turn@Matrix.Rotation(math.pi/2,4,'Y')
    obj.matrix_world=turn@source_matrix
    # Rest on the actual lowest surface; do not rescale or edit the copied mesh.
    points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    center=Vector(((min(p.x for p in points)+max(p.x for p in points))/2,
                   (min(p.y for p in points)+max(p.y for p in points))/2,min(p.z for p in points)))
    obj.matrix_world.translation+=Vector((*item['center'],.9394))-center
    entry=components[item['id']]
    for i,material in enumerate(obj.data.materials):
        alias='Library_'+item['id']+'_'+str(i)
        copied=material.copy();copied.name=alias;obj.data.materials[i]=copied
        bindings[copied.name]={'mesh':kit_assets['meshes'][item['id']], 'slot':entry['materials'][i]}
    obj['existing_library_tool']=item['id']
    copies.append({'id':item['id'],'source_mesh':kit_assets['meshes'][item['id']],
        'source_object':entry['name'],'vertices':len(obj.data.vertices),'faces':len(obj.data.polygons),
        'placement':item,'geometry_edited':False,'uv_rebuilt':False,'decimation_applied':False})

parts=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GunWorkbench_Editable.blend'))
export_parts=[]
for obj in parts:
    copy=obj.copy();copy.data=obj.data.copy();bpy.context.scene.collection.objects.link(copy);export_parts.append(copy)
bpy.ops.object.select_all(action='DESELECT')
for obj in export_parts:obj.select_set(True)
bpy.context.view_layer.objects.active=next(obj for obj in export_parts if obj.name.startswith('Retained_Table'))
bpy.ops.object.join();mesh=bpy.context.object;mesh.name='SM_GunWorkbench'
tri=mesh.modifiers.new('Export triangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
fbx=OUT/'SM_GunWorkbench.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
    mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
def canon(name):return re.sub(r'[._][0-9]{3}$','',name)
material_paths={canon(m.name):base_manifest['material_paths'][canon(m.name)] for m in mesh.data.materials if canon(m.name) not in bindings}
manifest={'fbx':str(fbx),'material_paths':material_paths,'library_materials':bindings,'reused_tools':copies,
    'original_lamp_copies':base_manifest['lamp_copies'],'triangles':len(mesh.data.polygons),
    'retained_base':str(BASE/'GunWorkbench_Editable.blend'),
    'source_library':str(KIT/'Authored/DungeonWorkbenchKit.blend'),'tests_run':False,'renders_run':False}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('EXISTING_WORKBENCH_TOOLS_PLACED',json.dumps([item['id'] for item in layout]))
