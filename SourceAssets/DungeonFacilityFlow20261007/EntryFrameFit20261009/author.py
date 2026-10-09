"""Extend the existing entrance reveal to meet the recessed grille and return walls."""
from pathlib import Path
import bpy,bmesh,json,hashlib
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
BASE='/Game/Dungeons/FacilityFlow20261007/EntryFrameFit20261009'
SOURCE=ROOT.parent/'FrontEntry20261008'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC'
with bpy.data.libraries.load(str(SOURCE/'Authored/FrontEntry.blend'),link=False) as (src,dst):dst.objects=['SM_FrontEntry_PortalFrames']
obj=dst.objects[0];bpy.context.collection.objects.link(obj);obj.name='SM_EntryFrameFit_PortalFrames'
# Preserve the east opening and hall-facing edge. Extend the rear edge of the
# west jambs/lintel behind the grille into the existing portico's solid return.
for vertex in obj.data.vertices:
    if vertex.co.x < -24.1:vertex.co.x=-24.79
obj.data.update();uv=obj.data.uv_layers.active
for face in obj.data.polygons:
    if face.center.x>=0:continue
    axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(face.normal[a]))]
    for li in face.loop_indices:
        q=obj.data.vertices[obj.data.loops[li].vertex_index].co;uv.data[li].uv=(q[axes[0]],q[axes[1]])
# The existing six independent rectangular solids remain exact convex colliders.
bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();remaining=set(bm.verts);islands=[]
while remaining:
    todo=[remaining.pop()];group=[]
    while todo:
        v=todo.pop();group.append(v)
        for edge in v.link_edges:
            q=edge.other_vert(v)
            if q in remaining:remaining.remove(q);todo.append(q)
    islands.append(group)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
for i,vs in enumerate(islands):
    mapping={v:j for j,v in enumerate(vs)};fs={f for v in vs for f in v.link_faces}
    mesh=bpy.data.meshes.new('UCX_'+obj.name+'_%02d'%i);mesh.from_pydata([tuple(v.co) for v in vs],[],[[mapping[v] for v in f.verts] for f in fs]);mesh.update()
    co=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(co);co.select_set(True)
bm.free()
file=OUT/(obj.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
source=json.loads((SOURCE/'geometry.json').read_text('utf8'))
mat=next(m['materials'] for m in source['meshes'] if m['kind']=='PortalFrames')
record=dict(name=obj.name,kind='PortalFrames',mesh=BASE+'/Meshes/'+obj.name,fbx=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),materials=mat,collision=True,nanite=True,cast_shadow=True)
(ROOT/'geometry.json').write_text(json.dumps(dict(meshes=[record],west_reveal_back_cm=-2479,west_reveal_front_cm=-2375.5,old_reveal_back_cm=-2424.5,grille_depth_cm=[-2453.3,-2436.6],east_frame_unchanged=True),indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'EntryFrameFit.blend'))
print('ENTRY_REVEALS_AUTHORED')
