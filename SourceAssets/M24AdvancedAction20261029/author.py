"""Receiver and handguard kit only; the native host retains its original stock and grips."""
import bpy,bmesh,json,math,shutil
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parent
for name in ('Exports','Icons','Reference'): (O/name).mkdir(exist_ok=True)
ref=Path('C:/Users/allan/AppData/Local/Temp/codex-clipboard-7c60dfc7-acde-49b7-9b65-225a990ef4ce.png')
if ref.exists():shutil.copy2(ref,O/'Reference/user-side-reference.png')
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'),use_scripts=False)
native=bpy.data.objects['M24_base'];src=native.data
parent=list(range(len(src.vertices)));seen={}
def root(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
def unite(a,b):parent[root(a)]=root(b)
for v in src.vertices:
    key=tuple(round(x,6) for x in v.co)
    if key in seen:unite(v.index,seen[key])
    else:seen[key]=v.index
for e in src.edges:unite(*e.vertices)
islands={}
for v in src.vertices:islands.setdefault(root(v.index),[]).append(v.index)
chosen={root(0)}|{k for k,vs in islands.items() if max(src.vertices[i].co.y for i in vs)<.041}
ids=sorted({i for k in chosen for i in islands[k]})
(O/'factory_vertices.json').write_text(json.dumps([[src.vertices[i].co.x*100,-src.vertices[i].co.y*100,src.vertices[i].co.z*100] for i in ids]))
existing=list(bpy.data.objects)
for ob in existing:ob.hide_render=True;ob.hide_set(True)
parts=[]
def material(name,color,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    return m
coat=material('M24_AAS_CoatedMetal',(.035,.039,.041),.85,.31)
steel=material('M24_AAS_SatinSteel',(.16,.17,.18),.92,.27)
polymer=material('M24_AAS_ContactPolymer',(.018,.019,.019),0,.48)
rubber=material('M24_AAS_Rubber',(.009,.010,.010),0,.7)
def finish(ob,name,mat,bevel=.0006,group=parts):
    ob.name=name;ob.data.materials.clear();ob.data.materials.append(mat)
    if bevel:
        mod=ob.modifiers.new('Manufactured edge radius','BEVEL');mod.width=bevel;mod.segments=3
        mod=ob.modifiers.new('Area weighted corner normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    for p in ob.data.polygons:p.use_smooth=True
    group.append(ob);return ob
def cube(name,pos,size,mat=coat,bevel=.0006,group=parts):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pos);ob=bpy.context.object;ob.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(ob,name,mat,bevel,group)
def cylinder(name,pos,radius,depth,axis='X',mat=steel,vertices=32,group=parts):
    rot={'X':(0,math.pi/2,0),'Y':(math.pi/2,0,0),'Z':(0,0,0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=pos,rotation=rot)
    ob=bpy.context.object;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    return finish(ob,name,mat,.00025,group)
def profile(name,yz,width,mat=coat,group=parts):
    n=len(yz);v=[(s*width/2,y,z) for s in (-1,1) for y,z in yz]
    f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(v,[],f);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);return finish(ob,name,mat,.0007,group)
def apply_modifiers(ob):
    bpy.context.view_layer.objects.active=ob
    for mod in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
def cut(ob,cutter):
    # All holes have real wall depth. Apply cuts before the final bevel pass.
    mod=ob.modifiers.new('Open machined aperture','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.context.view_layer.objects.active=ob
    bpy.ops.object.modifier_move_up(modifier=mod.name)
    bpy.ops.object.modifier_move_up(modifier=mod.name)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    if cutter in parts:parts.remove(cutter)
    bpy.data.objects.remove(cutter,do_unlink=True)
def slot(ob,pos,size,radius=.002):
    cutter=cube('temporary rounded aperture',pos,size,coat,radius)
    apply_modifiers(cutter);cut(ob,cutter)
def bolt(pos,axis='X',radius=.0025,group=parts):
    shell=cylinder('Recessed captive fastener',pos,radius,.0013,axis,steel,32,group)
    q=Vector(pos);idx={'X':0,'Y':1,'Z':2}[axis];q[idx]+=.0007 if q[idx]>=0 else -.0007
    cylinder('Dark hex drive',q,radius*.51,.00015,axis,rubber,6,group)
# Receiver lower side walls stay below the native bolt/ejection corridor.
for sign in (-1,1):
    p=profile('Faceted receiver side',[(-.065,.068),(.041,.054),(.091,.059),(.120,.080),(.265,.083),(.282,.097),(.280,.106),(.093,.106),(.030,.086),(-.065,.087)],.0035)
    p.location.x=sign*.024
    for y,z in ((-.047,.079),(.070,.078),(.132,.094),(.249,.094)):bolt((sign*.027,y,z))
    # Grasp and magazine lips are kept clear; the lower wall stops above them.
    cube('Receiver seam accent',(sign*.0264,.190,.095),(.0006,.099,.0014),steel,.0002)
# Ventilated upper forend. Existing lower contact surface and barrel remain.
for sign in (-1,1):
    side=cube('Handguard side shell',(sign*.0255,.445,.126),(.005,.318,.037),coat,.001)
    for y in (.318,.369,.420,.471,.522,.573):
        slot(side,(sign*.0255,y,.126),(.012,.037,.013),.004)
    for y in (.296,.394,.496,.595):bolt((sign*.0286,y,.111),radius=.002)
    # Front side accessory rail with individual transverse ridges.
    cube('Accessory rail base',(sign*.0305,.528,.126),(.006,.096,.013),coat,.0006)
    for j in range(10):cube('Side rail rib',(sign*.034,.487+j*.009,.126),(.006,.005,.019),coat,.0004)
    for y in (.489,.568):bolt((sign*.038,y,.126),radius=.0027)
for y in (.288,.605):
    bridge=cube('Handguard end bulkhead',(0,y,.126),(.055,.006,.037),coat,.0008)
    hole=cylinder('barrel clearance',(0,y,.115),.020,.018,'Y',coat,64)
    apply_modifiers(hole);cut(bridge,hole)
cube('Rail continuous spine',(0,.447,.144),(.020,.333,.004),coat,.0004)
for j in range(33):
    y=.286+j*.010
    # Dovetail profile gives visible undercut shoulders and rounded corners.
    cube('Top rail shoulder',(0,y,.146),(.026,.0062,.004),coat,.00045)
    cube('Top rail crown',(0,y,.149),(.022,.0062,.003),coat,.00035)
# Apply the final game bevels, author UVs for newly created geometry, export in
# the same cm/-Y-forward convention as the existing M24 native attachments.
def prepare(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    apply_modifiers(ob)
    tri=ob.modifiers.new('Export triangles with tangent basis','TRIANGULATE')
    if hasattr(tri,'keep_custom_normals'):tri.keep_custom_normals=True
    apply_modifiers(ob)
    if not ob.data.uv_layers:
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(68),island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
    # UVs cover physical repeated surface detail; no post-import recompute.
    ob.data.calc_loop_triangles()
for ob in parts:prepare(ob)
def export(key,objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    file=O/'Exports'/('SM_M24_'+key+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',global_scale=1,bake_anim=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    return {'file':str(file),'objects':[o.name for o in objects],'triangles':sum(len(o.data.loop_triangles) for o in objects)}
models={'m24_advanced_action':export('m24_advanced_action',parts)}
for ob in existing:ob.hide_render=True;ob.hide_set(True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_AdvancedAction_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'models':models,'materials':[m.name for m in (coat,steel,polymer,rubber)],'source':str(O.parent/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'),'factory_vertex_count':len(ids),'hand_interfaces':'Native host stock and grip remain visible; no duplicate hand-contact liner','reference':'user side image; hidden-side design inferred','runtime_tested':False},indent=2))
print('M24_ADVANCED_ACTION_AUTHORED',json.dumps({k:v['triangles'] for k,v in models.items()}),flush=True)
