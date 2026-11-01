"""Make an exclusive conductor seat using the factory's unchanged mounting faces."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;OUT=P/'Export';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
base=bpy.data.objects['SM_ThunderGodHammer_head_mount_factory']
for ob in list(bpy.context.scene.objects):
    if ob!=base:bpy.data.objects.remove(ob,do_unlink=True)
def material(name,color,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    n.inputs['Base Color'].default_value=(*color,1);n.inputs['Metallic'].default_value=metal;n.inputs['Roughness'].default_value=rough;return m
silver=material('M_ThunderThrowSilver',(.48,.53,.59),.95,.24)
blue=material('M_ThunderThrowRune',(.015,.18,.38),.65,.27)
parts=[base]
def rod(name,a,b,r,mat):
    a,b=Vector(a),Vector(b);bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=r,depth=(b-a).length,location=(a+b)*.5)
    o=bpy.context.object;o.name=name;o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();o.data.materials.append(mat)
    mod=o.modifiers.new('soft engraved edges','BEVEL');mod.width=.0007;mod.segments=2
    bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name);parts.append(o)
# Raised angular thunder conductors on front/back. Interfaces at X +/-6.5cm
# and the lower neck remain the original factory surfaces.
for sign in (-1,1):
    y=sign*.062
    for xsign in (-1,1):
        pts=[(xsign*.043,y,.864),(xsign*.053,y,.894),(xsign*.036,y,.918),(xsign*.052,y,.946),(xsign*.036,y,.984)]
        for a,b in zip(pts,pts[1:]):rod('Silver lightning conductor',a,b,.0034,silver)
        for a,b in zip(pts[1:-1],pts[2:]):rod('Blue inlaid conductor',(a[0],a[1]+sign*.003,a[2]),(b[0],b[1]+sign*.003,b[2]),.0013,blue)
    # Norse triangular interlace around the existing round central crest.
    for shift in (-.012,0,.012):
        pts=[(-.018+shift,y+sign*.005,.925),(.018+shift,y+sign*.005,.925),(shift,y+sign*.005,.956)]
        for a,b in zip(pts,pts[1:]+pts[:1]):rod('Interlaced silver crest',a,b,.0016,silver)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=base;bpy.ops.object.join();base.name='SM_ThunderHammer_GuanLeiSeat'
bpy.ops.export_scene.fbx(filepath=str(OUT/(base.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'GuanLeiSeat_Editable.blend'))
(P/'seat.json').write_text(json.dumps({'mesh':base.name,'materials':[m.name for m in base.data.materials],
    'source':'factory head_mount; native mounting faces retained','tested':False},indent=2),encoding='utf-8')
print('GUAN_LEI_SEAT_SAVED')
