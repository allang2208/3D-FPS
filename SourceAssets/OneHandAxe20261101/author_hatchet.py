"""Fit the selected Meshy source to the shared kukri grip frame; export without decimation."""
import bpy
import json
from pathlib import Path
from mathutils import Matrix, Vector

P = Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P/'Original/Meshy_AI_Tactical_Hatchet_1101133535_texture.glb'))
objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in objects: o.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
if len(objects)>1: bpy.ops.object.join()
obj=bpy.context.object
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
mesh=obj.data
source=[v.co.copy() for v in mesh.vertices]
# Blender updates custom split normals when coordinates deform. Capture the
# original corner normals before touching vertices, then transform exactly once.
source_normals=[n.vector.copy() for n in mesh.corner_normals]
height=max(v.z for v in source)-min(v.z for v in source)
scale=.42/height
band=[v for v in source if -.65<=v.z<=-.25]
origin=Vector(((min(v.x for v in band)+max(v.x for v in band))*.5,
               (min(v.y for v in band)+max(v.y for v in band))*.5,-.45))
width=(max(v.x for v in band)-min(v.x for v in band))*scale
thick=(max(v.y for v in band)-min(v.y for v in band))*scale
fitx=.033/width
fity=.0173/thick
normal_matrices=[]
for v,p in zip(mesh.vertices,source):
    # Smoothly release the measured fist-section fit into the unmodified head.
    t=max(0.,min(1.,p.z/.25)); smooth=t*t*(3.-2.*t)
    w=1.-smooth; dw=-(6.*t-6.*t*t)/.25 if 0.<p.z<.25 else 0.
    sx=1.+(fitx-1.)*w; sy=1.+(fity-1.)*w
    q=p-origin
    v.co=Vector((-q.x*sx,-q.y*sy,q.z))*scale
    jac=Matrix(((-sx,0.,-q.x*(fitx-1.)*dw),(0.,-sy,-q.y*(fity-1.)*dw),(0.,0.,1.)))
    normal_matrices.append(jac.inverted().transposed())
normals=[(normal_matrices[l.vertex_index]@n).normalized() for l,n in zip(mesh.loops,source_normals)]
mesh.update()
mesh.normals_split_custom_set(normals)
obj.name=mesh.name='SM_TacticalHatchet'
for material in mesh.materials: material.name='M_TacticalHatchet'
for image in bpy.data.images:
    if image.type!='IMAGE': continue
    index=0 if 'normal' in image.name.lower() else 2 if 'metallic' in image.name.lower() else 1
    image.filepath=str(P/'Textures'/('source_image_%02d.png'%index))
    image.reload()
    image.pack()
for d in ('Export','Icons'): (P/d).mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'TacticalHatchet_Editable.blend'))
bpy.ops.export_scene.fbx(filepath=str(P/'Export/SM_TacticalHatchet.fbx'),use_selection=True,
    object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_space_transform=False,
    use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
points=[v.co*100. for v in mesh.vertices]
head=[p for p in points if p.z>16.]
# The axe's own edge samples replace the knife tip/root in the shared trace executor.
lower=[p for p in head if 16.<p.z<20.]
upper=[p for p in head if p.z>27.]
root=max(lower,key=lambda p:p.x); tip=max(upper,key=lambda p:p.x)
info=dict(frame='UE cm: +Z toward head, +X cutting edge, origin=fist centre; WPN_root scale .01',
    length_cm=42.,source_scale=scale,source_grip_origin=list(origin),grip_fit_xy=[fitx,fity],
    grip_size_cm=[3.3,1.73],triangles=sum(len(p.vertices)-2 for p in mesh.polygons),
    bounds_cm={'min':[min(p[a] for p in points) for a in range(3)],'max':[max(p[a] for p in points) for a in range(3)]},
    trace_base_cm=[root.x,0.,root.z],trace_tip_cm=[tip.x,0.,tip.z],runtime_tested=False)
(P/'model.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
# Inventory art must use the actual UE assembly, PBR and shared studio.
# After importing/saving the assets, run export_inventory_icon.py. Grayscale
# modification-panel authoring is a separate workflow and must not overwrite it.
print('HATCHET_AUTHORED '+json.dumps(info),flush=True)
