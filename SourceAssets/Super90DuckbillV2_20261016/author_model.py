"""Original V2 cosmetic game mesh, authored from scratch.

Two sculpted exterior lips, a short shoulder, relief grooves and decorative
fasteners. No imported donor mesh or functional internal mechanism.
Blender metres; +X forward, +Z up; existing game attachment seat at the origin.
"""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;X=O/'Exports';X.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
RECIPES=[('DuckbillV2_Graphite',(.026,.028,.032,1),.39,1),
         ('DuckbillV2_Seat',(.034,.035,.037,1),.42,1),
         ('DuckbillV2_Recess',(.005,.006,.007,1),.61,.2),
         ('DuckbillV2_Edge',(.080,.085,.094,1),.29,1),
         ('DuckbillV2_Fastener',(.044,.047,.052,1),.34,1)]
MATS=[]
for name,color,roughness,metallic in RECIPES:
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear();bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(bs.outputs[0],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=color;bs.inputs['Roughness'].default_value=roughness;bs.inputs['Metallic'].default_value=metallic
    mat.diffuse_color=color;mat.roughness=roughness;mat.metallic=metallic;MATS.append(mat)
def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
def mesh_object(name,vertices,faces,materials):
    mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(vertices,[],faces)
    for mat in MATS:mesh.materials.append(mat)
    for face,index in zip(mesh.polygons,materials):face.material_index=index
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    mesh.update();obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
    return obj
def rounded(n,w,h,r):
    result=[];steps=n//4
    for corner,(sy,sz) in enumerate(((1,1),(-1,1),(-1,-1),(1,-1))):
        for j in range(steps):
            angle=(corner+j/(steps-1))*math.pi*.5
            result.append((sy*(w-r)+r*math.cos(angle),sz*(h-r)+r*math.sin(angle)))
    return result
def loft(name,rows,n):
    vertices=[];faces=[];ids=[]
    for x,w,h,r,cz,index in rows:
        vertices.extend((x,y,z+cz) for y,z in rounded(n,w,h,r))
    faces.append(tuple(reversed(range(n))));ids.append(rows[0][-1])
    for k in range(len(rows)-1):
        for j in range(n):
            q=(j+1)%n;faces.append((k*n+j,k*n+q,(k+1)*n+q,(k+1)*n+j));ids.append(rows[k+1][-1])
    faces.append(tuple((len(rows)-1)*n+j for j in range(n)));ids.append(rows[-1][-1])
    return mesh_object(name,vertices,faces,ids)
def lathe(name,profile,n,mat=1):
    vs=[(x,r*math.cos(j*math.tau/n),r*math.sin(j*math.tau/n)) for x,r in profile for j in range(n)]
    fs=[tuple(reversed(range(n)))];ms=[mat]
    for k in range(len(profile)-1):
        for j in range(n):
            q=(j+1)%n;fs.append((k*n+j,k*n+q,(k+1)*n+q,(k+1)*n+j));ms.append(mat)
    fs.append(tuple((len(profile)-1)*n+j for j in range(n)));ms.append(mat)
    return mesh_object(name,vs,fs,ms)
def prism(name,outline,bottom,top,mat):
    n=len(outline);vs=[(x,y,z) for z in (bottom,top) for x,y in outline]
    fs=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]
    for i in range(n):q=(i+1)%n;fs.append((i,q,n+q,n+i))
    return mesh_object(name,vs,fs,[mat]*len(fs))
def cut(target,cutter):
    select([target]);mod=target.modifiers.new('Authored relief','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
def bevel(obj,width,segments):
    select([obj]);mod=obj.modifiers.new('Detail edge chamfer','BEVEL');mod.width=width;mod.segments=segments
    mod.limit_method='ANGLE';mod.angle_limit=math.radians(40);mod.use_clamp_overlap=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
def finish(obj):
    select([obj]);mesh=obj.data
    for face in mesh.polygons:face.use_smooth=True
    mesh.set_sharp_from_angle(angle=math.radians(48))
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.012)
    bpy.ops.object.mode_set(mode='OBJECT');mesh.uv_layers.active.name='UV0'
    # Weighted normals are reserved for small planar mechanical details.
    # Sculpted lips use their continuous surface normals and authored edge rings.
    if not obj.name.startswith(('UpperLip','LowerLip','Shoulder')):
        mod=obj.modifiers.new('Planar detail normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=40
    return obj
LIP_ROWS=[(.030,.0175,.0022,.0013,.0090,0),(.036,.0200,.0022,.0013,.0090,0),
          (.046,.0240,.0021,.0013,.0092,0),(.060,.0300,.0020,.0013,.0095,0),
          (.079,.0340,.0019,.00125,.0100,0),(.096,.0350,.0018,.0012,.0105,0),
          (.1045,.0346,.0018,.0012,.0106,0),(.1064,.0344,.0018,.0012,.0106,3),
          (.107,.0338,.00125,.0008,.0106,3)]
def create(level,n,segments):
    parts=[]
    seat=lathe('NativeSeatTransition',[( -.002,.0113),(-.0012,.012),(.003,.012),(.0037,.0131),(.007,.0131),
        (.0073,.0127),(.0081,.0127),(.0084,.0131),(.012,.0131),(.0128,.0140),(.0175,.0140),(.018,.0137)],n)
    parts.append(seat)
    # Six planar facets distinguish the wrench-like exterior shoulder from the
    # smooth round mounting band. This is a visible game prop detail only.
    collar=lathe('FacetedShoulderBand',[(.0128,.0145),(.0140,.0153),(.019,.0153),(.0202,.0145)],12,1)
    bevel(collar,.0003,segments);parts.append(collar)
    shoulder=loft('Shoulder_ContinuousTransition',[
        (.017,.0137,.0122,.009,0,0),(.023,.0160,.0122,.007,0,0),(.032,.0192,.0115,.0055,0,0),
        (.043,.0230,.0112,.004,0,0),(.047,.0242,.0110,.0038,0,0),(.0475,.0237,.0105,.0034,0,3),
        (.0475,.0195,.0062,.0027,0,2),(.041,.0170,.0056,.0025,0,2)],n)
    parts.append(shoulder)
    for sign,name in [(1,'UpperLip'),(-1,'LowerLip')]:
        rows=[(x,w,h,r,z*sign,m) for x,w,h,r,z,m in LIP_ROWS]
        lip=loft(name+'_SculptedTongue',rows,n)
        # Actual shallow exterior grooves, not black lines painted on a flat box.
        if level<2:
            for side in (-1,1):
                outline=[(.052,side*.009),(.055,side*.011),(.091,side*.021),(.095,side*.020),
                         (.092,side*.0184),(.056,side*.0080)]
                if side<0:outline.reverse()
                low,high=(.01105,.016) if sign>0 else(-.016,-.01105)
                cutter=prism('ReliefCutter',outline,low,high,2);bevel(cutter,.00025,segments);cut(lip,cutter)
        parts.append(lip)
    # Small recessed drive fasteners sit on the rear upper/lower surface, away
    # from the native seating boundary. Their slot remains geometry at LOD0/1.
    if level<2:
        for sign in (-1,1):
            bpy.ops.mesh.primitive_cylinder_add(vertices=32 if level==0 else 16,radius=.00225,depth=.0008,location=(.025,0,sign*.0122))
            screw=bpy.context.object;screw.name='RecessedFastener_'+str(sign)
            for mat in MATS:screw.data.materials.append(mat)
            for p in screw.data.polygons:p.material_index=4
            # Apply transform before Boolean/UV so the drive recess is local.
            select([screw]);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
            cutter=prism('DriveRecess',[(.0233,-.00035),(.0267,-.00035),(.0267,.00035),(.0233,.00035)],
                .01225 if sign>0 else -.014,.014 if sign>0 else -.01225,2)
            cut(screw,cutter);bevel(screw,.00012,segments);parts.append(screw)
    return [finish(obj) for obj in parts]
def export(parts,level):
    select(parts);bpy.ops.object.duplicate();copies=list(bpy.context.selected_objects)
    for obj in copies:select([obj]);bpy.ops.object.convert(target='MESH')
    select(copies);bpy.ops.object.join();obj=bpy.context.object;obj.name='SM_ShotgunDuckbillV2_'+level
    mod=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.data.calc_loop_triangles();row={'triangles':len(obj.data.loop_triangles),'vertices':len(obj.data.vertices)}
    fbx=X/(obj.name+'.fbx');glb=X/(obj.name+'.glb')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=False,export_tangents=True)
    row.update({'fbx':str(fbx),'glb':str(glb)});bpy.data.objects.remove(obj,do_unlink=True);return row
parts=create(0,96,3);lods={'LOD0':export(parts,'LOD0')}
for index,n,segments in [(1,48,2),(2,24,1)]:
    simple=create(index,n,segments);lods['LOD'+str(index)]=export(simple,'LOD'+str(index))
    for obj in simple:bpy.data.objects.remove(obj,do_unlink=True)
select(parts);source=O/'ShotgunDuckbillV2_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(source))
report={'editable_source':str(source),'lods':lods,'parts':[p.name for p in parts],
    'materials':[{'name':n,'base_color_linear':c,'roughness':r,'metallic':m} for n,c,r,m in RECIPES],
    'tip_cm':10.7,'donor_meshes':[],'source_reference':'Original split-lip duckbill exterior; authored from scratch',
    'extended_tube_compatible':True,'engine_imported':False,'runtime_tested':False}
(O/'authoring_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DUCKBILL_V2_ORIGINAL_MODEL_SAVED',json.dumps(lods),flush=True)
