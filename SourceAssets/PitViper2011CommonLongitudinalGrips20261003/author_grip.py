"""Fit all three shared 2011 grip patterns to the accepted longitudinal domain."""
import json,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;P=O.parents[1];S=O.parent/'PitViper2011Integration20261002'
COMMON=O.parent/'PitViper2011Attachments20261002';PRIOR=O.parent/'PitViper2011GripRebuild20261003'
NAME='SM_PitViper2011_GripSurface';MESH='/Game/Weapons/PitViper2011/Attachments20261002/'+NAME
sys.path.insert(0,str(P/'Tools/Weapons'))
from pit_viper_longitudinal_grip import LongitudinalPalmPanel,palm_limits,palm_lower_boundary
(O/'Exports').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'Single/PitViper2011_single_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
root=bpy.data.objects['SK_PitViper2011_Manny'].data.bones['WPN_root'].matrix_local.copy();inv=root.inverted()
alignment=Matrix(json.loads((S/'Single/authoring.json').read_text(encoding='utf8'))['alignment'])
parts=json.loads((S/'canonical_parts.json').read_text(encoding='utf8'));vertices=[];faces=[]
for part in parts:
    if part['identity']=='2011pv frame_12' and part['material']=='polymer':
        start=len(vertices);vertices.extend(alignment@Vector(v) for v in part['verts'])
        faces.extend(tuple(start+i for i in f) for f in part['faces'])
bvh=BVHTree.FromPolygons(vertices,faces);limits=palm_limits(parts);lower_line=palm_lower_boundary(parts)
for ob in list(bpy.context.scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
V=[];F=[];UV=[];fits=[]
for side in (-1,1):
    # Same samples and outline as the VIP version, without its relief or inlay.
    panel=LongitudinalPalmPanel(bvh,alignment,root,side,limits,lower_line,nx=64,ny=160)
    vs,fs,_=panel.geometry(atlas=False);base=len(V)
    V.extend(vs);F.extend(tuple(base+i for i in f) for f in fs)
    # UV0 is derived AFTER native seam clipping. Using the old uncut row grid
    # would stretch the pattern along columns with a shorter lower boundary.
    for point in vs:
        native=inv@Vector(point);UV.append(((native.y+.30*native.z)/.1,native.z/.1))
    fits.append(panel.record())
data=bpy.data.meshes.new(NAME);data.from_pydata(V,[],F);data.update()
data.materials.append(bpy.data.materials.new('M_pistol_grip_granular'))
for face in data.polygons:face.use_smooth=True
layer=data.uv_layers.new(name='UV0')
for face in data.polygons:
    for li in face.loop_indices:layer.data[li].uv=UV[data.loops[li].vertex_index]
for channel in (1,2,3):
    layer=data.uv_layers.new(name='UV'+str(channel))
    for face in data.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(face.normal[k]))]
        for li in face.loop_indices:
            point=data.vertices[data.loops[li].vertex_index].co;layer.data[li].uv=(point[axes[0]]/.1,point[axes[1]]/.1)
ob=bpy.data.objects.new(NAME,data);bpy.context.collection.objects.link(ob)
ob['part_family']='pistol_grip_granular / pistol_grip_diamond / pistol_grip_quickdot'
ob['design']='Longitudinal lateral grip-body skins; separate from magazine and magwell'
# Native frame context is authoring-only and excluded from selected FBX export.
refs=bpy.data.collections.new('REFERENCE_NativeGrip');bpy.context.scene.collection.children.link(refs)
for part in parts:
    if part['identity']!='2011pv frame_12':continue
    reference=bpy.data.meshes.new('Reference_'+part['material'])
    reference.from_pydata([root@(alignment@Vector(v)) for v in part['verts']],[],part['faces']);reference.update()
    ref=bpy.data.objects.new(reference.name,reference);refs.objects.link(ref);ref.hide_render=True;ref.hide_set(True)
    ref['reference_only']=True
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
fbx=O/'Exports'/(NAME+'.fbx');blend=O/'Exports'/(NAME+'_Editable.blend')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
    add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
auth={'name':NAME,'fbx':str(fbx),'blend':str(blend),'mesh':MESH,'fits':fits,
    'triangles':sum(len(f.vertices)-2 for f in data.polygons),'revision':'common_longitudinal_grips_20261003',
    'frame':'native skeletal component reference; inverse WPN_root bind chain at runtime','bone':'WPN_root',
    'material_family':'PistolGripSurface20260927','texture_tile_m':.1,'sockets_blender_m':{},
    'affected_parts':['pistol_grip_granular','pistol_grip_diamond','pistol_grip_quickdot'],
    'source':str(S/'canonical_parts.json'),'uv_mapping':'UV0 physical 0.1m tile, canonical (Y+0.30Z,Z), derived from actual clipped vertices',
    'design':'Two longitudinal native grip-body skins matching the VIP outline; slanted lower seam with clearance, no magazine/baseplate/magwell coverage.',
    'provenance':'Native grip surface derived from Low Poly TTI JW4 Pit Viper 2011 by D_U; original integration records CC BY 4.0; https://sketchfab.com/3d-models/low-poly-tti-jw4-pit-viper-2011-2daaf7fe78604ee7941a4ad5fd4d0153',
    'textures_changed':False,'shared_icons_regenerated':False,'stats_changed':False,'game_tested':False,'acceptance_rendered':False}
(O/'authoring.json').write_text(json.dumps(auth,ensure_ascii=False,indent=2),encoding='utf8')
record=json.loads((COMMON/'authoring.json').read_text(encoding='utf8'));record['GripSurface']=auth
(COMMON/'authoring.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
record=json.loads((PRIOR/'authoring.json').read_text(encoding='utf8'));record['common']=auth
(PRIOR/'authoring.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print('PIT_VIPER_COMMON_LONGITUDINAL_GRIPS_AUTHORED_AND_EXPORTED',auth['triangles'],flush=True)
