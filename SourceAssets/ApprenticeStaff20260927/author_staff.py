"""Meshy master -> centimetre UE meshes and six independent modification interfaces.
Run in Blender background. No renders, engine launch or validation runs.
"""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
# Current user-selected reference design; the old sphere-head branch below is archival.
import runpy
runpy.run_path(str(ROOT/'BarkRebuildV21/author_model.py'),run_name='__main__')
raise SystemExit(0)
OUT = ROOT / 'Export'
OUT.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'Meshy/staff/downloads/model_urls_glb.glb'))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
master = bpy.context.object
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
lo = Vector([min(v.co[i] for v in master.data.vertices) for i in range(3)])
hi = Vector([max(v.co[i] for v in master.data.vertices) for i in range(3)])
axis = max(range(3), key=lambda i: hi[i]-lo[i])
rot = Vector([int(i==axis) for i in range(3)]).rotation_difference(Vector((0,0,1)))
for v in master.data.vertices: v.co = rot @ v.co
zlo = min(v.co.z for v in master.data.vertices)
zhi = max(v.co.z for v in master.data.vertices)
mid = (zhi+zlo)*.5
# Wider end is the sphere. Preserve the generated shape and UVs.
top = max((v.co.xy.length for v in master.data.vertices if v.co.z > zhi-(zhi-zlo)*.15), default=0)
bottom = max((v.co.xy.length for v in master.data.vertices if v.co.z < zlo+(zhi-zlo)*.15), default=0)
scale = 160/(zhi-zlo)
center = Vector(((lo.x+hi.x)*.5,(lo.y+hi.y)*.5,0)) if axis==2 else Vector((0,0,0))
for v in master.data.vertices:
    v.co = Vector(((v.co.x-center.x)*scale,(v.co.y-center.y)*scale,(v.co.z-mid)*scale*(1 if top>=bottom else -1)))
master.name='SM_Staff_Base'
objects=[master]

def sliced(name, minimum, maximum):
    obj=master.copy(); obj.data=master.data.copy(); bpy.context.collection.objects.link(obj); obj.name=name
    bm=bmesh.new(); bm.from_mesh(obj.data)
    for z,normal in [(minimum,(0,0,1)),(maximum,(0,0,-1))]:
        cut=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.0001,
            plane_co=(0,0,z),plane_no=normal,clear_inner=True,clear_outer=False)
        edges=[e for e in cut['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
        if edges: bmesh.ops.holes_fill(bm,edges=edges,sides=0)
    bm.to_mesh(obj.data); bm.free(); objects.append(obj); return obj

GRIP_Z=32.0
low=sliced('SM_Staff_Body',-81,GRIP_Z-10)
upper=sliced('BodyUpper',GRIP_Z+10,62)
bpy.ops.object.select_all(action='DESELECT');low.select_set(True);upper.select_set(True)
bpy.context.view_layer.objects.active=low;bpy.ops.object.join();objects.remove(upper)
sliced('SM_Staff_head_crystal_false',62,81)
sliced('SM_Staff_grip_lining_false',GRIP_Z-10,GRIP_Z+10)

# Surface-fitted V2 parts; the Meshy master and factory splits above remain authoritative.
import sys
sys.path.insert(0,str(ROOT))
from staff_modular_parts import build_modifications
factory_grip=next(o for o in objects if o.name=='SM_Staff_grip_lining_false')
objects.extend(build_modifications(master,factory_grip,GRIP_Z))

bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
# The artist source remains editable; FBX vertices are explicitly centimetres.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'apprentice_staff_modular.blend'))
manifest=[]
for o in objects:
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    bpy.ops.export_scene.fbx(filepath=str(OUT/(o.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='OFF',use_tspace=False,
        apply_scale_options='FBX_SCALE_ALL',path_mode='AUTO',embed_textures=False,add_leaf_bones=False)
    manifest.append({'name':o.name,'fbx':str(OUT/(o.name+'.fbx')),'materials':[m.name for m in o.data.materials if m]})
(OUT/'meshes.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'anchors.json').write_text(json.dumps({'units':'cm','length':160,'grip':[0,0,GRIP_Z],
    'head_interface':[0,0,62],'crown':[0,0,63],'shaft_rune':[0,0,52.5],
    'grip_lining':[0,0,GRIP_Z],'grip_limits_z':[GRIP_Z-10,GRIP_Z+10],
    'tail_charm':[0,0,-64],'mana_line':[0,0,35],'interface_revision':3,
    'crown_mount_z':[62.55,64.25],'head_neck_source':'Meshy master surface',
    'grip_profile':'exact factory grip mesh and cut rings',
    'rune_raise_cm':0.105,'mana_raise_cm':0.1,
    'mana_lane_angles_deg':[45,225]},indent=2),encoding='utf-8')
