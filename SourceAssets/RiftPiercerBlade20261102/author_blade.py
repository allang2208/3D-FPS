"""Rift Piercer: preserve the frost_hilt_v1 seat, author a lean continuous ridge."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector

P=Path(__file__).resolve().parent; OUT=P/'Export'; OUT.mkdir(exist_ok=True)
SOURCE=P.parent/'FrostSwordModules20260915/FrostSword_Modular_Editable.blend'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(SOURCE),link=False) as (src,dst):
    dst.objects=['SM_FrostSword_Blade_factory']
blade=dst.objects[0]; bpy.context.scene.collection.objects.link(blade)
blade.data=blade.data.copy(); original=[v.co.copy() for v in blade.data.vertices]
tip=max(v.z for v in original); seat=.105; new_tip=tip*1.10
# The original surface/UVs remain the material carrier, including red and polished finishes.
# Reduce the upper width and remove surface waviness into a continuous four-facet ridge.
bins=100
width=[0.0]*bins;depth=[0.0]*bins
for p in original:
    i=min(bins-1,max(0,int(p.z/tip*bins)))
    width[i]=max(width[i],abs(p.x));depth[i]=max(depth[i],abs(p.y))
for v,p in zip(blade.data.vertices,original):
    if p.z<=seat:continue
    t=(p.z-seat)/(tip-seat); blend=min(1,max(0,(p.z-seat)/.13));blend=blend*blend*(3-2*blend)
    i=min(bins-1,max(0,int(p.z/tip*bins)))
    w=max(width[max(0,i-1):min(bins,i+2)]);d=max(depth[max(0,i-1):min(bins,i+2)])
    theta=math.atan2(p.y/max(.00001,d),p.x/max(.00001,w))
    c,s=math.cos(theta),math.sin(theta)
    radius=1/max(.0001,abs(c)+abs(s))
    taper=(1-.31*t)*(1-.16*max(0,(t-.70)/.30))
    target_x=w*taper*c*radius
    target_y=max(.001,d*.82)*s*radius
    v.co.x=p.x*(1-blend)+target_x*blend
    v.co.y=p.y*(1-blend)+target_y*blend
    v.co.z=seat+t*(new_tip-seat)
blade.data.update()
blade.data.normals_split_custom_set([(0,0,0)]*len(blade.data.loops))
rows=[]
for level,ratio in enumerate([1,.48,.20]):
    obj=blade if level==0 else blade.copy()
    if level:
        obj.data=blade.data.copy();bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.objects.active=obj
        mod=obj.modifiers.new('RidgeLOD','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.name='SM_FrostSword_Blade_rift_piercer_LOD'+str(level)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    rows.append({'lod':level,'vertices':len(obj.data.vertices),'polygons':len(obj.data.polygons)})
    if level:obj.hide_render=True;obj.hide_set(True)
# One centimetre faceted mote, instanced in a bounded edge-particle field at runtime.
mesh=bpy.data.meshes.new('RiftPiercerMote')
mesh.from_pydata([(0,0,.012),(0,0,-.012),(.004,0,0),(0,.004,0),(-.004,0,0),(0,-.004,0)],[],[(0,2,3),(0,3,4),(0,4,5),(0,5,2),(1,3,2),(1,4,3),(1,5,4),(1,2,5)])
uv=mesh.uv_layers.new(name='UVMap')
for f in mesh.polygons:
    for j,li in enumerate(f.loop_indices):uv.data[li].uv=[(0,0),(1,0),(.5,1)][j]
mote=bpy.data.objects.new('SM_RiftPiercer_Mote',mesh);bpy.context.scene.collection.objects.link(mote)
bpy.ops.object.select_all(action='DESELECT');mote.select_set(True);bpy.context.view_layer.objects.active=mote
bpy.ops.export_scene.fbx(filepath=str(OUT/'SM_RiftPiercer_Mote.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
mote.hide_render=True;mote.hide_set(True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'RiftPiercer_Blade_Editable.blend'))
(P/'exports.json').write_text(json.dumps({'source':str(SOURCE),'interface':'frost_hilt_v1','seat_unchanged_below_cm':10.5,'original_tip_cm':tip*100,'visual_tip_cm':new_tip*100,'trace_base_cm':[0,0,3],'trace_tip_cm':[0,0,100],'rune_dimensions_cm':[10,10,69.3],'lods':rows,'gem_cores':0,'game_tested':False},indent=2),encoding='utf8')
print('RIFT_PIERCER_MODEL_EXPORTED',flush=True)
