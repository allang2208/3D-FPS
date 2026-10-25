"""Preserve four fitted head geometries and UV0; add native-rune UV1 and mask."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;FAMILY=P.parent
sys.path.insert(0,str(P))
from surface_authoring import activate,transfer_runes
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(FAMILY/'ModulesV1/RuneboundWarhammer_SharedParts_Editable.blend'),link=False) as (a,b):
    b.objects=['SM_RuneboundWarhammer_hammer_heads_'+key for key in ('heavy_forged','flanged_breaker','light_drum','pointed_hammer')]
for obj in b.objects:bpy.context.scene.collection.objects.link(obj)
bpy.context.preferences.filepaths.save_version=0
rows=[]
for option in ('heavy_forged','flanged_breaker','light_drum','pointed_hammer'):
    obj=bpy.data.objects['SM_RuneboundWarhammer_hammer_heads_'+option]
    # Materials are copied for bake nodes; donor/shared authoring stays intact.
    for slot in obj.material_slots:slot.material=slot.material.copy()
    activate(obj);uv=obj.data.uv_layers.new(name='NativeRuneUV');obj.data.uv_layers.active=uv
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.1,island_margin=.006,correct_aspect=True,scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    image=transfer_runes(obj,P/'common/Textures'/('T_NativeRune_'+option+'.png'),len(obj.data.uv_layers)-1)
    obj.name='SM_RuneboundWarhammer_hammer_heads_'+option+'_RuneV3'
    activate(obj);location=obj.location.copy();obj.location=Vector((0,0,0))
    out=P/'common/Export';out.mkdir(parents=True,exist_ok=True)
    fbx=out/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
    obj.location=location
    rows.append({'id':option,'mesh':obj.name,'fbx':str(fbx),'rune_texture':image.filepath_raw,
        'rune_uv_channel':len(obj.data.uv_layers)-1,'materials':[m.name for m in obj.data.materials]})
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'common/RuneboundHeads_NativeRunes_Editable.blend'))
(P/'common/production_receipt.json').write_text(json.dumps({'parts':rows,'tested':False},indent=2),encoding='utf-8')
print('FOUR_COMMON_HEAD_RUNES_AUTHORED',flush=True)
