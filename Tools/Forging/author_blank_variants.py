"""Author Tang Dao and compact warhammer blanks in the accepted station frame.

The exported profile is also the runtime source for contact heights, strike regions,
tong contact and quenching. No renders, animation rebakes or gameplay tests.
For a hammer-only update use --warhammer-only, then import_hammer_refinement.py.
"""
import bpy
import bmesh
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HAMMER_ONLY = '--warhammer-only' in sys.argv
OUT = ROOT / 'SourceAssets/ForgeHammerRefine20261024'
EXPORT = OUT / 'Export'
EXPORT.mkdir(parents=True, exist_ok=True)
DEST = '/Game/Props/ForgeInteraction20260927/BlankVariants20261015'
HAMMER_DEST = '/Game/Props/ForgeInteraction20260927/HammerRefine20261024'


def point(x, y):
    # WorkYaw=180: author +X is opposite station +X; UV retains the existing scoring metric.
    return [round(.5-y/24, 6), round(.375-x/60, 6)]


common = {
    'grip_cm': [-24, 0, .475],
    'quench_tip_cm': [30, 0, .475], 'quench_heel_cm': [-21, 0, .475],
    'quench_drop_cm': 30, 'aim_min': [.37, .1], 'aim_max': [.63, .65],
    'heat_span_cm': [-19, 25], 'heat_center_cm': [0, 0, 8], 'veil_scale': [.65, .22, 1],
}
sword = dict(common, label='剑胚', crown=[.5, .5], stages=[],
             points=[[.496,.13],[.499,.20],[.496,.27],[.500,.34],
                     [.497,.41],[.501,.48],[.496,.55],[.500,.62]])
dao = dict(common, label='唐刀刀胚', crown=[.46, 1], stages=[],
           quench_tip_cm=[29,1.8,.375],
           points=[point(x,.2) for x in (-14,-10,-6,-2,2,6,10,14)])
hammer = dict(common, label='双手锤锤胚', crown=[.075, .925], stages=[],
              eye_center_cm=[1,0], eye_radius_cm=[1.8,1.5],
              aim_min=[.26,.12], aim_max=[.74,.59], quench_drop_cm=36,
              quench_tip_cm=[14,0,2.2], quench_heel_cm=[-12,0,2.35],
              heat_span_cm=[-9,10], heat_center_cm=[1,0,10], veil_scale=[.28,.22,1],
              # Full 1.85 cm target discs fit the cheeks and avoid the open eye.
              points=[point(x,y) for x in (-7,-4,6,10) for y in (-1.8,1.8)])
for stage in range(3):
    width_scale = 1+.12*(2-stage)
    sword['stages'].append({
        'mesh': f'/Game/Props/ForgeInteraction20260927/SM_ForgeBlank{stage}',
        'sections': [[x,-w*width_scale,w*width_scale,.95,.38]
                     for x,w in [(-31,1.2),(-22,1.2),(-21,2.6),(-8,2.55),(16,2.35),(25,1.65),(30,.08)]],
    })
    swell = 1+.09*(2-stage)
    # Straight spine and an oblique single-edge point, with an unsharpened forging edge.
    dao_sections = [
        [-31,-1.2,1.2,.95,.38],[-22,-1.2,1.2,.95,.38],
        [-20.5,-2.1*swell,2.1*swell,.95,.24+.06*(2-stage)],
        [-8,-2.05*swell,2.1*swell,.95,.24+.06*(2-stage)],
        [16,-1.95*swell,2.1*swell,.95,.24+.06*(2-stage)],
        [24,-1.85*swell,2.1*swell,.95,.24+.06*(2-stage)],
        [30,1.92*swell,2.1*swell,.75,.24+.06*(2-stage)],
    ]
    dao['stages'].append({'mesh': f'{DEST}/SM_ForgeDaoBlank{stage}', 'sections': dao_sections})
    width = 4.2+.3*(2-stage)
    height = 5.4+.25*(2-stage)
    hammer_sections = [
        [-31,-1.2,1.2,.95,.38],[-23,-1.2,1.2,.95,.38],[-21,-1.35,1.35,1.25,.75],
        [-16,-2,2,2.4,1.9],[-12,-width+.3,width-.3,height-.7,height-1.3],
        [-9,-width,width,height,height-.6],
        [10,-width,width,height,height-.6],
        [13,-width+.4,width-.4,height-.5,height-1.1],
        [14,-width+1,width-1,height-1,height-1.6],
    ]
    hammer['stages'].append({'mesh': f'{HAMMER_DEST}/SM_ForgeHammerBlank{stage}', 'sections': hammer_sections})

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
material = bpy.data.materials.new('HotBlank')
material.diffuse_color = (.16,.05,.014,1)
material.use_nodes = True
bsdf = material.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (.16,.05,.014,1)
bsdf.inputs['Metallic'].default_value = .7
bsdf.inputs['Roughness'].default_value = .8


def author(profile, stage):
    name = stage['mesh'].rsplit('/',1)[-1]
    vertices, faces = [], []
    low, high = profile['crown']
    # Perimeter ordered from bottom edge through spine and back over the working face.
    # high=1 for the Dao gives a thick vertical spine without a second cutting bevel.
    ring_size = 6 if high<1 else 5
    for x, ymin, ymax, top, edge in stage['sections']:
        yl, yh = ymin+(ymax-ymin)*low, ymin+(ymax-ymin)*high
        cross = [(ymin,0),(ymax,0)]
        if high<1: cross += [(ymax,edge),(yh,top)]
        else: cross += [(ymax,top)]
        cross += [(yl,top),(ymin,edge)]
        vertices += [(x*.01,-y*.01,z*.01) for y,z in cross]
    faces.append(tuple(reversed(range(ring_size))))
    last = (len(stage['sections'])-1)*ring_size
    faces.append(tuple(last+i for i in range(ring_size)))
    for row in range(len(stage['sections'])-1):
        for col in range(ring_size):
            a=row*ring_size+col
            b=row*ring_size+(col+1)%ring_size
            faces.append((a,b,b+ring_size,a+ring_size))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    if 'eye_radius_cm' in profile:
        # Real open eye through the metal head; no handle, leather or finished ornament in the hot blank.
        rx,ry=profile['eye_radius_cm'];cx,cy=profile['eye_center_cm']
        bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=1,depth=.25,location=(cx*.01,-cy*.01,.04))
        cutter=bpy.context.object;cutter.scale=(rx*.01,ry*.01,1)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        bpy.context.view_layer.objects.active=obj
        cut=obj.modifiers.new('Open handle eye','BOOLEAN');cut.operation='DIFFERENCE';cut.solver='EXACT';cut.object=cutter
        bpy.ops.object.modifier_apply(modifier=cut.name)
        bpy.data.objects.remove(cutter,do_unlink=True)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bevel=obj.modifiers.new('Forged edge rounding','BEVEL');bevel.width=.0007;bevel.segments=3
    bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(35);bevel.use_clamp_overlap=True
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.dissolve_degenerate(bm,dist=.000001,edges=list(bm.edges))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    for polygon in obj.data.polygons: polygon.use_smooth=True
    normal=obj.modifiers.new('Weighted working normals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=50
    bpy.ops.object.modifier_apply(modifier=normal.name)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.025)
    bpy.ops.object.mode_set(mode='OBJECT')
    color=obj.data.color_attributes.new(name='Wear',type='FLOAT_COLOR',domain='CORNER')
    for value in color.data: value.color=(.08,0,0,1)
    tri=obj.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    bpy.ops.export_scene.fbx(filepath=str(EXPORT/(name+'.fbx')),use_selection=True,object_types={'MESH'},
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',axis_forward='-Y',axis_up='Z',
        use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,bake_anim=False)
    obj.hide_set(True)
    return {'mesh':stage['mesh'],'file':str(EXPORT/(name+'.fbx')),
            'vertices':len(obj.data.vertices),'triangles':len(obj.data.polygons)}


outputs=[]
for profile in ((hammer,) if HAMMER_ONLY else (dao,hammer)):
    for stage in profile['stages']:outputs.append(author(profile,stage))
# A precisely mapped carrier for an antialiased ring material. The shader's
# outer radius is 1.85 cm, identical to the authoritative strike radius.
name='SM_ForgeHammerGuide'
mesh=bpy.data.meshes.new(name)
mesh.from_pydata([(-.0185,-.0185,0),(.0185,-.0185,0),(.0185,.0185,0),(-.0185,.0185,0)],[],[(0,1,2,3)])
mesh.update()
uv=mesh.uv_layers.new(name='UVMap')
for loop,coord in zip(uv.data,[(0,0),(1,0),(1,1),(0,1)]):loop.uv=coord
obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
obj.data.materials.append(material)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(EXPORT/(name+'.fbx')),use_selection=True,object_types={'MESH'},
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',axis_forward='-Y',axis_up='Z',
    use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,bake_anim=False)
obj.hide_set(True)
outputs.append({'mesh':HAMMER_DEST+'/'+name,'file':str(EXPORT/(name+'.fbx')),'vertices':4,'triangles':2})
# The editable source opens with the two final stages separated; FBXs retain the station origin.
for name, offset in [('SM_ForgeDaoBlank2',-.22),('SM_ForgeHammerBlank2',.22)]:
    if name not in bpy.data.objects:continue
    obj=bpy.data.objects[name];obj.hide_set(False);obj.location.y=0 if HAMMER_ONLY else offset
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Forge_Blank_Variants_Editable.blend'))
profile_path=ROOT/'Content/ColdSteelData/forge-blanks.json'
profiles=json.loads(profile_path.read_text(encoding='utf-8-sig'))
profiles['profiles'].update({'warhammer':hammer} if HAMMER_ONLY else {'sword':sword,'tang_dao':dao,'warhammer':hammer})
payload=json.dumps(profiles,ensure_ascii=False,indent=2)+'\n'
(OUT/'profiles.json').write_text(payload,encoding='utf-8')
# Runtime reference is installed only after the UE assets have been saved.
receipt={'source':'Original parametric derivatives of the accepted ForgeInteraction20260927 sword blank',
         'material':'/Game/Props/ForgeInteraction20260927/M_ForgeHotSteel',
         'frame':'UE cm; support plane Z=0; sacrificial tong shank on -X; clamp (-24,0,.475)',
         'hammer':'Compact forged head with open eye; accepted tong shank and grip retained unchanged',
         'assets':outputs,'rendered':False,'runtime_tested':False}
(OUT/'authored.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('FORGE_BLANKS_AUTHORED '+str(OUT),flush=True)
