"""Place existing ammunition packages without rebuilding their meshes, UVs or textures."""
import bpy,json,math,re
from pathlib import Path
from mathutils import Matrix,Vector

P=Path('D:/FPS3D/FPSGAME')
ROOT=P/'SourceAssets/GunWorkbenchAmmo20260928'
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE=P/'SourceAssets/GunWorkbenchLibraryTools20260928/Authored'
base=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
sources=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
layout=[
    {'id':'ammo_556','center':[-.80,-1.165],'width_m':.185,'label_direction_degrees':85},
    {'id':'ammo_762','center':[.92,-.86],'width_m':.21,'label_direction_degrees':177},
    {'id':'ammo_556','center':[.71,-1.13],'width_m':.185,'label_direction_degrees':192},
]
bpy.ops.wm.open_mainfile(filepath=str(BASE/'GunWorkbench_Editable.blend'))
bindings={};placements=[]
def bounds(obj):
    points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    return Vector(tuple(min(p[i] for p in points) for i in range(3))),Vector(tuple(max(p[i] for p in points) for i in range(3)))

for index,item in enumerate(layout):
    source=sources['ammo'][item['id']]
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=source['fbx'])
    imported=[o for o in bpy.data.objects if o not in before]
    objects=[o for o in imported if o.type=='MESH']
    if len(objects)!=1:raise RuntimeError('Expected one existing ammo mesh: '+item['id'])
    obj=objects[0];transform=obj.matrix_world.copy();obj.parent=None;obj.matrix_world=transform
    obj.name='LibraryAmmo_'+item['id']+'_'+str(index+1)
    for other in imported:
        if other!=obj:bpy.data.objects.remove(other,do_unlink=True)
    # The second original slot is the printed front panel. Orient the package by
    # its actual surface normal, independent of FBX export axis conventions.
    label_index=next(i for i,s in enumerate(source['materials']) if 'cardboard' in s['slot'].lower())
    front=Vector((0,0,0))
    for poly in obj.data.polygons:
        if poly.material_index==label_index:front+=poly.normal*poly.area
    front=obj.matrix_world.to_3x3().inverted().transposed()@front
    angle=math.radians(item['label_direction_degrees'])-math.atan2(front.y,front.x)
    lo,hi=bounds(obj);scale=item['width_m']/max(hi.x-lo.x,hi.y-lo.y)
    obj.matrix_world=Matrix.Rotation(angle,4,'Z')@Matrix.Scale(scale,4)@obj.matrix_world
    bpy.context.view_layer.update();lo,hi=bounds(obj)
    obj.matrix_world.translation+=Vector((*item['center'],.9380))-Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for slot,material in enumerate(obj.data.materials):
        alias='Ammo_'+item['id']+'_'+str(slot)
        existing=bpy.data.materials.get(alias)
        if not existing:existing=material.copy();existing.name=alias
        obj.data.materials[slot]=existing
        bindings[alias]=source['materials'][slot]['asset']
    obj['reused_ammo_asset']=source['mesh']
    lo,hi=bounds(obj)
    placements.append({**item,'mesh':source['mesh'],'scale':scale,'bounds_m':[list(lo),list(hi)],
        'vertices':len(obj.data.vertices),'polygons':len(obj.data.polygons),'geometry_rebuilt':False,'uv_rebuilt':False})

parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GunWorkbench_Editable.blend'))
copies=[]
for obj in parts:
    copy=obj.copy();copy.data=obj.data.copy();bpy.context.scene.collection.objects.link(copy);copies.append(copy)
bpy.ops.object.select_all(action='DESELECT')
for obj in copies:obj.select_set(True)
bpy.context.view_layer.objects.active=next(o for o in copies if o.name.startswith('Retained_Table'))
bpy.ops.object.join();mesh=bpy.context.object;mesh.name='SM_GunWorkbench'
tri=mesh.modifiers.new('Export triangles','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
fbx=OUT/'SM_GunWorkbench.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
    mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
manifest={**base,'fbx':str(fbx),'retained_base':str(BASE/'GunWorkbench_Editable.blend'),
    'ammo_materials':bindings,'ammo_placements':placements,'target_mesh':sources['bench'],
    'triangles':len(mesh.data.polygons),'tests_run':False,'renders_run':False}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('WORKBENCH_AMMO_PLACED '+json.dumps(placements))
