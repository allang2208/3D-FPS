"""Split the existing accepted surfaces into reusable modules. No renders/tests."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
SOURCE=P.parent/'MeshyMelee20260915/FrostCrystalSword_Manny_Editable.blend'
FIX=P.parent/'FrostSwordSurfaceFix20260915'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=bpy.data.objects['SK_RuneSword_Rig'];arms=bpy.data.objects['SK_Manny_Arms_Export']
rest=rig.data.bones['WPN_root'].matrix_local.copy();rig.animation_data_clear();rig.data.pose_position='REST'
def export(name,objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[-1]
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
export('SK_FrostSword_Arms',[arms,rig])
source=bpy.data.objects['FrostCrystalSword_Blade'].data.copy();source.transform(rest.inverted());source.update()
modules=[];interfaces={};rows=[]
PIVOTS={'blade_1':Vector((0,0,0)),'guard':Vector((0,0,0)),'grip':Vector((0,0,-.050)),'pommel':Vector((0,0,-.227))}
# V seat lies inside the original crystal/bronze surround. It is unchanged in
# all three repaired guards. Horizontal cuts follow the two grip-end collars.
PLANE_A=lambda p:p.z+.008-1.1*p.x
PLANE_B=lambda p:p.z+.008+1.1*p.x
TOP=lambda p:p.z+.050
BOTTOM=lambda p:p.z+.227
def clip(poly,fn,inside=True):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=fn(a[0])*(1 if inside else -1);db=fn(b[0])*(1 if inside else -1)
        if da>=0:result.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);result.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return result
def part_polygons(mesh,part):
    mesh.calc_loop_triangles();uv0=mesh.uv_layers[0].data
    uv1=mesh.uv_layers.get('StockBronzeUV');color=mesh.color_attributes.get('GuardFinish')
    normals=[n.vector.copy() for n in mesh.corner_normals]
    for tri in mesh.loop_triangles:
        poly=[]
        for i in tri.loops:
            co=mesh.vertices[mesh.loops[i].vertex_index].co.copy()
            poly.append((co,uv0[i].uv.copy(),uv1.data[i].uv.copy() if uv1 else uv0[i].uv.copy(),Vector(color.data[i].color if color else (0,0,0,1)),normals[i]))
        if part=='blade_1':groups=[clip(clip(poly,PLANE_A),PLANE_B)]
        elif part=='guard':
            poly=clip(poly,TOP);groups=[clip(poly,PLANE_A,False),clip(clip(poly,PLANE_A),PLANE_B,False)] if poly else []
        elif part=='grip':groups=[clip(clip(poly,TOP,False),BOTTOM)]
        else:groups=[clip(poly,BOTTOM,False)]
        for polygon in groups:
            if len(polygon)>=3:yield polygon
def build(mesh,part,option):
    pivot=PIVOTS[part];name='SM_FrostSword_'+('Blade' if part=='blade_1' else part.title())+'_'+option
    vertices=[];faces=[];corners=[]
    for polygon in part_polygons(mesh,part):
        for i in range(1,len(polygon)-1):
            tri=[polygon[0],polygon[i],polygon[i+1]]
            if (tri[1][0]-tri[0][0]).cross(tri[2][0]-tri[0][0]).length<1e-12:continue
            face=[]
            for item in tri:face.append(len(vertices));vertices.append(item[0]-pivot);corners.append(item)
            faces.append(face)
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    data.materials.append(mesh.materials[0])
    uv0=data.uv_layers.new(name='UVMap');uv1=data.uv_layers.new(name='StockBronzeUV');col=data.color_attributes.new(name='GuardFinish',type='FLOAT_COLOR',domain='CORNER')
    stored=data.attributes.new('SurfaceNormal',type='FLOAT_VECTOR',domain='CORNER')
    for f in data.polygons:
        f.use_smooth=True
        for i in f.loop_indices:
            item=corners[data.loops[i].vertex_index];uv0.data[i].uv=item[1];uv1.data[i].uv=item[2];col.data[i].color=item[3];stored.data[i].vector=item[4].normalized()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000005)
    # Close only newly introduced mounting boundaries, preserving source seams.
    cuts={'blade_1':[PLANE_A,PLANE_B],'guard':[PLANE_A,PLANE_B,TOP],'grip':[TOP,BOTTOM],'pommel':[BOTTOM]}[part]
    edges=[e for e in bm.edges if e.is_boundary and any(all(abs(fn(v.co+pivot))<.000003 for v in e.verts) for fn in cuts)]
    graph={}
    for e in edges:
        for v in e.verts:graph.setdefault(v,[]).append(e.other_vert(v))
    unused=set(graph);loops=[]
    while unused:
        start=min(unused,key=lambda v:tuple(v.co));current=start;previous=None;loop=[]
        for _ in range(len(graph)+1):
            loop.append(current);unused.discard(current)
            candidates=[v for v in graph[current] if v!=previous]
            if not candidates:break
            nxt=candidates[0]
            if nxt==start:break
            if nxt in loop:break
            previous,current=current,nxt
        if len(loop)>=3:loops.append(loop)
    exported=[]
    norm_layer=bm.loops.layers.float_vector.get('SurfaceNormal');color_layer=bm.loops.layers.float_color.get('GuardFinish')
    for loop in loops:
        exported.append([list(v.co+pivot) for v in loop])
        center=sum((v.co for v in loop),Vector())/len(loop)
        cap=bm.verts.new(center)
        for a,b in zip(loop,loop[1:]+loop[:1]):
            face=bm.faces.new((b,a,cap));face.smooth=False;face.normal_update()
            for l in face.loops:
                l[norm_layer]=face.normal
                l[bm.loops.layers.uv[0]].uv=(.97,.905);l[bm.loops.layers.uv[1]].uv=(.97,.905)
                l[color_layer]=(0,0,0,1)
    bm.to_mesh(data);bm.free();data.update()
    data.normals_split_custom_set([tuple(v.vector) for v in data.attributes['SurfaceNormal'].data])
    obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj)
    export(name,[obj]);obj.location=pivot;modules.append(obj)
    interfaces[part+'_'+option]={'pivot_m':list(pivot),'boundary_loops_m':exported}
    rows.append({'slot':part,'id':option,'mesh':name,'location_cm':[pivot.x*100,-pivot.y*100,pivot.z*100]})
    return obj
for part in ['blade_1','guard','grip','pommel']:build(source,part,'factory')
for option in ['bastion_guard','riposte_guard','light_guard']:
    file=FIX/option/('FrostCrystalSword_'+option+'_Editable.blend')
    with bpy.data.libraries.load(str(file),link=False) as (src,dst):dst.objects=['FrostCrystalSword_Seamless']
    full=dst.objects[0];mesh=full.data.copy();mesh.transform(rest.inverted());mesh.update()
    obj=build(mesh,'guard',option);obj.hide_set(True);obj.hide_render=True
    bpy.data.objects.remove(full,do_unlink=True)
for obj in list(bpy.context.scene.objects):
    if obj not in modules:
        if obj.name in bpy.context.view_layer.objects:obj.hide_set(True)
        obj.hide_render=True
# Named mounting datums and frozen grip envelope, retained in the editable file.
for part,pivot in PIVOTS.items():
    o=bpy.data.objects.new('Mount_'+part,None);bpy.context.scene.collection.objects.link(o);o.location=pivot;o.empty_display_type='ARROWS';o.empty_display_size=.03
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'FrostSword_Modular_Editable.blend'))
(P/'interfaces.json').write_text(json.dumps({'units':'meters; canonical blade +Z, width X, thickness Y','interface_version':'frost_hilt_v1','seat':{'blade_V':'z=-0.008+1.1*abs(x)','guard_grip_z':-.050,'grip_pommel_z':-.227},'parts':interfaces},indent=2))
(P/'exports.json').write_text(json.dumps({'parts':rows,'arms':'SK_FrostSword_Arms','source':str(SOURCE),'blade_visual_tip_cm':81.1727345,'scope':'Module authoring/export only. No rendering or tests.'},indent=2))
print('FROST_SWORD_MODULES_EXPORTED',flush=True)
