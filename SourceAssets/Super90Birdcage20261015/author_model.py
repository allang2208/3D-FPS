"""Author a cosmetic birdcage muzzle attachment for the game's shotgun family.

Exterior mesh only: no threads, bore engineering or internal mechanism.
Blender metres, +X forward, +Z up, rear seating plane at the origin.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
X=O/'Exports';X.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=1
RECIPES=[('Birdcage_Shell',(.034,.037,.043,1),.35,1),
         ('Birdcage_RearSeat',(.034,.035,.037,1),.42,1),
         ('Birdcage_Recess',(.006,.007,.009,1),.64,.15),
         ('Birdcage_Edge',(.065,.071,.080,1),.31,1)]
MATS=[]
for name,color,rough,metal in RECIPES:
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear()
    bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=color
    bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    mat.diffuse_color=color;mat.roughness=rough;mat.metallic=metal
    MATS.append(mat)

def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]

def finish(name,vertices,faces,indices,bevel_segments):
    mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(vertices,[],faces)
    for mat in MATS:mesh.materials.append(mat)
    for face,index in zip(mesh.polygons,indices):face.material_index=index
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(mesh);bm.free();mesh.update()
    for face in mesh.polygons:face.use_smooth=True
    mesh.set_sharp_from_angle(angle=math.radians(40))
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    select([obj]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.018)
    bpy.ops.object.mode_set(mode='OBJECT');mesh.uv_layers.active.name='UV0'
    bevel=obj.modifiers.new('Small edge highlights','BEVEL')
    bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(38)
    bevel.width=.00023;bevel.segments=bevel_segments;bevel.use_clamp_overlap=True
    normal=obj.modifiers.new('Weighted surface normals','WEIGHTED_NORMAL')
    normal.keep_sharp=True;normal.weight=50
    return obj

def sleeve(n,bevel_segments):
    vertices=[];faces=[];materials=[]
    radius=.017
    half_angle=math.pi/12
    period=math.tau/6
    outer=[];inner=[]
    for inside in (False,True):
        rows=[[] for _ in range(8)]
        for j in range(n):
            angle=math.tau*j/n
            phase=(angle+period/2)%period-period/2
            t=min(1,abs(phase)/half_angle)
            cap=radius*half_angle*math.sqrt(max(0,1-t*t))
            sections=[(.014,.0146),(.018,.0168),(.022,.017),
                      (.030-cap,.017),(.052+cap,.017),
                      (.064,.017),(.071,.0175),(.074,.0175)]
            for k,(x,r) in enumerate(sections):
                r-=.0022 if inside else 0
                rows[k].append(len(vertices))
                vertices.append((x,r*math.cos(angle),r*math.sin(angle)))
        if inside:inner=rows
        else:outer=rows
    def add(face,material=0):faces.append(face);materials.append(material)
    opening=[]
    for j in range(n):
        middle=math.tau*(j+.5)/n
        phase=(middle+period/2)%period-period/2
        opening.append(abs(phase)<half_angle-1e-8)
    for j in range(n):
        q=(j+1)%n
        for k in range(7):
            if k==3 and opening[j]:continue
            add((outer[k][j],outer[k][q],outer[k+1][q],outer[k+1][j]),0)
            add((inner[k+1][j],inner[k+1][q],inner[k][q],inner[k][j]),2)
        add((outer[0][q],outer[0][j],inner[0][j],inner[0][q]),1)
        add((outer[-1][j],outer[-1][q],inner[-1][q],inner[-1][j]),3)
        if opening[j]:
            add((outer[3][j],outer[3][q],inner[3][q],inner[3][j]),0)
            add((outer[4][q],outer[4][j],inner[4][j],inner[4][q]),0)
        if opening[j]!=opening[(j-1)%n]:
            add((outer[3][j],outer[4][j],inner[4][j],inner[3][j]),0)
    return finish('Birdcage_SlottedShell',vertices,faces,materials,bevel_segments)

def rear_seat(n,bevel_segments):
    # Shared visual shoulder size follows the already installed SUPER90 seat.
    profile=[(-.002,.0113),(-.0012,.012),(.003,.012),(.0037,.0131),
             (.008,.0131),(.0083,.0129),(.0088,.0129),(.0091,.0131),
             (.0145,.0131),(.017,.0146),(.019,.0146)]
    vertices=[(x,r*math.cos(j*math.tau/n),r*math.sin(j*math.tau/n))
              for x,r in profile for j in range(n)]
    faces=[tuple(reversed(range(n)))];materials=[1]
    for k in range(len(profile)-1):
        for j in range(n):
            q=(j+1)%n
            faces.append((k*n+j,k*n+q,(k+1)*n+q,(k+1)*n+j))
            materials.append(2 if k==5 else 1)
    # Dark rear cap closes the cosmetic recess; no internal mechanical detail.
    faces.append(tuple((len(profile)-1)*n+j for j in range(n)));materials.append(2)
    return finish('Birdcage_RearVisualSeat',vertices,faces,materials,bevel_segments)

def export(parts,level):
    select(parts);bpy.ops.object.duplicate();copies=list(bpy.context.selected_objects)
    for obj in copies:
        select([obj]);bpy.ops.object.convert(target='MESH')
    select(copies);bpy.ops.object.join();obj=bpy.context.object
    obj.name='SM_ShotgunBirdcage01_'+level
    triangulate=obj.modifiers.new('Export triangles','TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    obj.data.calc_loop_triangles()
    row={'triangles':len(obj.data.loop_triangles),'vertices':len(obj.data.vertices)}
    fbx=X/(obj.name+'.fbx');glb=X/(obj.name+'.glb')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,
        mesh_smooth_type='FACE',use_tspace=True)
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
        export_animations=False,export_tangents=True,export_materials='EXPORT')
    row.update({'fbx':str(fbx),'glb':str(glb)})
    bpy.data.objects.remove(obj,do_unlink=True)
    return row

parts=[sleeve(96,3),rear_seat(96,3)]
lods={'LOD0':export(parts,'LOD0')}
for level,n,segments in [('LOD1',48,2),('LOD2',24,1)]:
    simple=[sleeve(n,segments),rear_seat(n,segments)]
    lods[level]=export(simple,level)
    for obj in simple:bpy.data.objects.remove(obj,do_unlink=True)
for name,x in [('Mount_Origin',0),('Visual_Front',.074)]:
    marker=bpy.data.objects.new(name,None);marker.location=(x,0,0)
    marker.empty_display_type='ARROWS';marker.empty_display_size=.012
    marker.hide_render=True;bpy.context.collection.objects.link(marker)
    marker.hide_set(True)
for obj in parts:
    obj['asset_family']='Shared_Shotgun_Muzzle'
    obj['variant']='shotgun_birdcage_flash_hider'
select(parts)
source=O/'ShotgunBirdcage01_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(source))
report={'status':'model_and_exports_saved','editable_source':str(source),'lods':lods,
    'materials':[{'name':name,'base_color_linear':color,'roughness':rough,'metallic':metal}
                 for name,color,rough,metal in RECIPES],
    'tip_cm':7.4,'source_reference':'Original game exterior, birdcage visual language',
    'normal_texture':None,'engine_imported':False,'runtime_tested':False}
(O/'authoring_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BIRDCAGE_MODEL_SAVED',json.dumps(lods),flush=True)
