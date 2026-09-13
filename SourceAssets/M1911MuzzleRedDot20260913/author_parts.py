"""Targeted panoramic dot/base edits and reuse of the existing game muzzle brake."""
import bpy,bmesh,json,math,ast
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent
bpy.context.preferences.filepaths.save_version=0
# Reuse the contact/UV construction helpers without rerunning older authoring.
tree=ast.parse((S/'M1911CompactFit20260913/author_optics_muzzle.py').read_text())
names={'select','finish','mesh_object','coating_uv','tube'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'<M1911 author helpers>','exec'))
report={}

def export_part(ob,key,uv_index,sockets,details):
    select(ob);coating_uv(ob,uv_index)
    ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
    for name,point in sockets.items():
        socket=bpy.data.objects.new('SOCKET_'+name,None);bpy.context.collection.objects.link(socket)
        socket.parent=ob;socket.location=point;socket.select_set(True)
    file=O/('SM_M1911_'+key+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',
                            bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    coords=[v.co.copy() for v in ob.data.vertices]
    report[key]={'fbx':str(file),'coating_uv':uv_index,'slots':[m.name for m in ob.data.materials],
                 'bounds_author_m':{'min':[min(v[i] for v in coords) for i in range(3)],'max':[max(v[i] for v in coords) for i in range(3)]},**details}
    ob.hide_render=False;ob.hide_set(False)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/('M1911_'+key+'_Editable.blend')))

bpy.ops.wm.open_mainfile(filepath=str(S/'M1911CompactFit20260913/M1911_CompactOptics_Editable.blend'))
ob=bpy.data.objects['M1911_panoramic_red_dot'];select(ob)
for other in list(bpy.context.scene.objects):
    if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
mesh=ob.data
reticle_slot=next(i for i,m in enumerate(mesh.materials) if 'Reticle' in m.name)
adapter_slot=next(i for i,m in enumerate(mesh.materials) if 'AdapterSteel' in m.name)
dot={vi for f in mesh.polygons if f.material_index==reticle_slot for vi in f.vertices}
adapter={vi for f in mesh.polygons if f.material_index==adapter_slot for vi in f.vertices}
# Joined parts retain disconnected islands: identify the wide plate independently
# of the curved feet. Keep the upper optical frame and its original normals intact.
neighbors={vi:set() for vi in adapter}
for edge in mesh.edges:
    a,b=edge.vertices
    if a in adapter and b in adapter:neighbors[a].add(b);neighbors[b].add(a)
remaining=set(adapter);plate=set()
while remaining:
    seed=remaining.pop();island={seed};stack=[seed]
    while stack:
        for vi in neighbors[stack.pop()]:
            if vi in remaining:remaining.remove(vi);island.add(vi);stack.append(vi)
    if max(abs(mesh.vertices[vi].co.y) for vi in island)>.013:plate.update(island)
original_normals=[normal.vector.copy() for normal in mesh.corner_normals]
aim=Vector((.013175,0,.02015));dot_scale=2.5;plate_scale=.025/.035
for vi in dot:
    p=mesh.vertices[vi].co;p.y=aim.y+(p.y-aim.y)*dot_scale;p.z=aim.z+(p.z-aim.z)*dot_scale
for vi in plate:mesh.vertices[vi].co.y*=plate_scale
for li,loop in enumerate(mesh.loops):
    n=original_normals[li]
    if loop.vertex_index in plate:n.y/=plate_scale
    elif loop.vertex_index in dot:n.y/=dot_scale;n.z/=dot_scale
    n.normalize()
mesh.update();mesh.normals_split_custom_set(original_normals)
export_part(ob,'panoramic_red_dot',3,{'MountForward':(.03,0,0),'MountUp':(0,0,.03),'AimCenter':aim},
            {'source':'M1911CompactFit20260913/M1911_CompactOptics_Editable.blend',
             'reticle_diameter_scale':dot_scale,'reticle_diameter_m':.0009*.62*dot_scale,'plate_width_m':.025,
             'mount_root_m':[0,.030,.0495],'aim_center_ue_cm':[1.3175,0,2.015]})

bpy.ops.wm.open_mainfile(filepath=str(S/'M4Muzzles20260910/brake-editable.blend'))
ob=bpy.data.objects['SM_M4_brake'];select(ob)
for other in list(bpy.context.scene.objects):
    if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
ob.name='M1911_brake'
# Keep all three port groups and the open interior. Reshape the exterior and
# passage separately so the pistol fitting does not collapse the visible bore.
for vertex in ob.data.vertices:
    p=vertex.co;r=math.hypot(p.x,p.z)
    if r>0:
        radius=r*(.0065/.006) if r<=.006 else .0065+(r-.006)*(.012-.0065)/(.0162-.006)
        p.x*=radius/r;p.z*=radius/r
    p.y=(p.y+.010)*(.040/.078)-.006
if ob.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
for edge in bm.edges:edge.smooth=edge.is_manifold and edge.calc_face_angle(0)<.6
bm.to_mesh(ob.data);bm.free()
adapter=bpy.data.materials.new('M1911_AdapterSteel')
collar=tube('M1911_BrakeCollar',[(-.0064,.0104),(-.0055,.0106),(-.0038,.0115),(-.002,.0115),(-.002,.0065),(-.0064,.0065)],adapter)
select(ob);collar.select_set(True);bpy.ops.object.join()
export_part(ob,'brake',2,{'MountForward':(0,.03,0),'MountUp':(0,0,.03),'Muzzle':(0,.034,0)},
            {'source':'M4Muzzles20260910/brake-editable.blend','body_length_m':.040,'outer_diameter_m':.024,
             'mount_root_m':[0,-.16187465,.02898],'muzzle_tip_ue_cm':[0,-3.4,0],'axis_ue':[0,-1,0]})
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M1911_MUZZLE_REDDOT_AUTHORED',flush=True)
