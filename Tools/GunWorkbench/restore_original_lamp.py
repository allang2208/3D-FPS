"""Copy the existing lamp at full fidelity; do not author or simplify it."""
import bpy,json,re,sys
from pathlib import Path
from mathutils import Matrix,Vector

PROJECT=Path('D:/FPS3D/FPSGAME')
remove_clutter='--remove-clutter' in sys.argv
ROOT=PROJECT/'SourceAssets'/('GunWorkbenchCleared20260928' if remove_clutter else 'GunWorkbenchLampRestore20260928')
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=PROJECT/'SourceAssets/GunWorkbenchPolish20260928/Authored/GunWorkbench_Editable.blend'
KIT=PROJECT/'SourceAssets/DungeonWorkbenchKit20260921/Authored/DungeonWorkbenchKit.blend'
STATE=json.loads((PROJECT/'SourceAssets/GunWorkbenchLampRestore20260928/source-state.json').read_text(encoding='utf-8'))
LAMP_NAMES=['SM_WBK_Bench_TaskLamp','SM_WBK_LampFlex']
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
removed=[]
for obj in list(bpy.data.objects):
    if obj.name in LAMP_NAMES:
        removed.append(obj.name);bpy.data.objects.remove(obj,do_unlink=True)
if len(removed)!=2:raise RuntimeError('Expected exactly the two derived lamp objects')

def canon(name):return re.sub(r'[._][0-9]{3}$','',name)
material_paths={canon(m['slot']):m['asset'] for m in STATE['palette_mesh']['materials']}
lamp_receipt=[]
with bpy.data.libraries.load(str(KIT),link=False) as (source,target):target.objects=list(LAMP_NAMES)
translation=Matrix.Translation(Vector((1.035,1.105,.939))-Vector((-.27,-.65,.939)))
for obj,original_name in zip(target.objects,LAMP_NAMES):
    if obj is None:raise RuntimeError('Original lamp source missing: '+original_name)
    bpy.context.scene.collection.objects.link(obj);obj.hide_set(False);bpy.context.view_layer.update()
    transform=obj.matrix_world.copy();obj.parent=None;obj.matrix_world=translation@transform
    slots=STATE['original_lamp'][original_name]['materials']
    paths={canon(s['slot']):s['asset'] for s in slots}
    for index,mat in enumerate(obj.data.materials):
        key=canon(mat.name)
        if key not in paths:raise RuntimeError('Original lamp material missing: '+key)
        alias='OriginalLamp_'+key
        copy=mat.copy();copy.name=alias;obj.data.materials[index]=copy
        material_paths[canon(copy.name)]=paths[key]
    obj['copy_original_lamp_unmodified']=True
    lamp_receipt.append({'object':original_name,'vertices':len(obj.data.vertices),'faces':len(obj.data.polygons),
        'uv_layers':[layer.name for layer in obj.data.uv_layers],
        'source_mesh':STATE['original_lamp'][original_name]['path'],'decimation_applied':False,'uv_rebuilt':False})

# Removing other rejected props is only enabled by the user's explicit choice.
if remove_clutter:
    for obj in list(bpy.data.objects):
        keep=(obj.name=='Retained_Table' or obj.name=='Silicone mat' or obj.name.startswith('Graduation')
              or obj.name=='Inset mat seam' or obj.get('copy_original_lamp_unmodified'))
        if not keep:removed.append(obj.name);bpy.data.objects.remove(obj,do_unlink=True)

parts=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GunWorkbench_Editable.blend'))
copies=[]
for obj in parts:
    copy=obj.copy();copy.data=obj.data.copy();bpy.context.scene.collection.objects.link(copy);copies.append(copy)
bpy.ops.object.select_all(action='DESELECT')
for obj in copies:obj.select_set(True)
bpy.context.view_layer.objects.active=next(obj for obj in copies if obj.name.startswith('Retained_Table'))
bpy.ops.object.join();merged=bpy.context.object;merged.name='SM_GunWorkbench'
# Only triangulation for export; no decimation, remeshing, UV unwrap or normal rewrite.
tri=merged.modifiers.new('Export triangles','TRIANGULATE');tri.keep_custom_normals=True
bpy.ops.object.modifier_apply(modifier=tri.name)
fbx=OUT/'SM_GunWorkbench.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
    mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
manifest={'fbx':str(fbx),'material_paths':material_paths,'lamp_copies':lamp_receipt,
    'removed_objects':removed,'other_clutter_removed':remove_clutter,'triangles':len(merged.data.polygons),
    'source':str(SOURCE),'original_lamp_source':str(KIT),'renders_run':False,'game_started':False}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('ORIGINAL_LAMP_COPIED',json.dumps(lamp_receipt), 'clutter_removed=',remove_clutter)
