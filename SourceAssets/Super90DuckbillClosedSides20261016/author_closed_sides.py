"""Close the two cosmetic side openings of the accepted V2 game mesh.

Keep existing lip/shoulder geometry, UVs, normals and seating frame. New solid
side panels follow the lip outline; the front horizontal opening stays open.
"""
import bpy,bmesh,math,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];SOURCE=P/'SourceAssets/Super90DuckbillV2_20261016'
X=O/'Exports';X.mkdir(parents=True,exist_ok=True)
ROWS=[(.036,.0200,.0022,.0090),(.046,.0240,.0021,.0092),(.060,.0300,.0020,.0095),
      (.079,.0340,.0019,.0100),(.096,.0350,.0018,.0105),(.1045,.0346,.0018,.0106),
      (.1064,.0344,.0018,.0106),(.107,.0338,.00125,.0106)]
def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
def material(key):
    return next(m for m in bpy.data.materials if m.name.split('.')[0]==key)
def wall(side,segments):
    verts=[];faces=[];ids=[]
    for x,width,thickness,center in ROWS:
        # Bury the panel's upper/lower joins slightly inside the existing lips.
        # The lip edge remains proud of the side wall as a continuous narrow rim.
        outside=side*(width-.0008);inside=side*(width-.0026)
        height=center-thickness+.0004
        verts.extend([(x,outside,-height),(x,outside,height),(x,inside,height),(x,inside,-height)])
    faces.append((3,2,1,0));ids.append(0)
    for k in range(len(ROWS)-1):
        for j in range(4):
            q=(j+1)%4;faces.append((4*k+j,4*k+q,4*(k+1)+q,4*(k+1)+j))
            ids.append(1 if j==2 else 0)
    faces.append(tuple(4*(len(ROWS)-1)+j for j in range(4)));ids.append(2)
    mesh=bpy.data.meshes.new('ClosedSidePanelMesh');mesh.from_pydata(verts,[],faces)
    for name in ('DuckbillV2_Graphite','DuckbillV2_Recess','DuckbillV2_Edge'):mesh.materials.append(material(name))
    for face,index in zip(mesh.polygons,ids):face.material_index=index
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
    obj=bpy.data.objects.new('ClosedSidePanel_Left' if side>0 else 'ClosedSidePanel_Right',mesh);bpy.context.collection.objects.link(obj)
    select([obj]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
    mesh.uv_layers.active.name='UV0'
    for face in mesh.polygons:face.use_smooth=True
    mesh.set_sharp_from_angle(angle=math.radians(45))
    bevel=obj.modifiers.new('Side panel edge highlights','BEVEL');bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(40)
    bevel.width=.00016;bevel.segments=segments;bevel.use_clamp_overlap=True
    normals=obj.modifiers.new('Side panel surface normals','WEIGHTED_NORMAL');normals.keep_sharp=True;normals.weight=40
    obj['revision']='ClosedSides20261016';return obj
def export(parts,level):
    select(parts);bpy.ops.object.duplicate();copies=list(bpy.context.selected_objects)
    for obj in copies:select([obj]);bpy.ops.object.convert(target='MESH')
    select(copies);bpy.ops.object.join();obj=bpy.context.object;obj.name='SM_ShotgunDuckbillV2_'+level
    mod=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.data.calc_loop_triangles();row={'triangles':len(obj.data.loop_triangles),'vertices':len(obj.data.vertices)}
    filename='SM_ShotgunDuckbillV2_'+level
    fbx=X/(filename+'.fbx');glb=X/(filename+'.glb')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=False,export_tangents=True)
    row.update({'fbx':str(fbx),'glb':str(glb)});bpy.data.objects.remove(obj,do_unlink=True);return row
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'ShotgunDuckbillV2_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
parts=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']+[wall(1,3),wall(-1,3)]
select(parts);editable=O/'ShotgunDuckbill_ClosedSides_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(editable))
lods={'LOD0':export(parts,'LOD0')}
for level,segments in [('LOD1',2),('LOD2',1)]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    bpy.ops.import_scene.fbx(filepath=str(SOURCE/'Exports'/('SM_ShotgunDuckbillV2_'+level+'.fbx')),use_anim=False)
    parts=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']+[wall(1,segments),wall(-1,segments)]
    lods[level]=export(parts,level)
report={'editable_source':str(editable),'source':str(SOURCE/'ShotgunDuckbillV2_Editable.blend'),
    'revision':'ClosedSides20261016','lods':lods,'changed_geometry':'two solid side panels only',
    'front_opening_preserved':True,'existing_geometry_uv_normals_preserved':True,
    'runtime_asset':'/Game/Weapons/CommonShotgun/DuckbillV2_20261016/Meshes/SM_ShotgunDuckbillV2',
    'tip_cm':10.7,'runtime_tested':False}
(O/'authoring_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DUCKBILL_CLOSED_SIDES_EXPORTED',json.dumps(lods),flush=True)
