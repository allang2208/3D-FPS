"""Local wolf variant: closed torn ear, lean flank, rest-space skin/wound bake.

Preserves the exported wolf armature, bind transforms and existing skin weights.
The Cycles jobs below make game textures; no scene preview or game test is run.
"""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector

R = Path('D:/FPS3D/FPSGAME/SourceAssets/ZombieDogV1')
SKIN = Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/material_v04/fab_source')
(R/'Textures').mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'Source/Wolf_Source.blend'))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
obj.name = 'SK_ZombieDog'
rig.data.pose_position = 'REST'
mesh = obj.data
source_uv = mesh.uv_layers.active
source_uv.name = 'SourceUV'
world = obj.matrix_world.copy()
inverse_world = world.inverted()

# Cut just the upper left ear and close its actual cut boundary on the same mesh.
bm = bmesh.new(); bm.from_mesh(mesh)
ear_faces = [f for f in bm.faces if all(
    (world@v.co).x > .025 and -.74 < (world@v.co).y < -.47 for v in f.verts)
    and any((world@v.co).z > .919 for v in f.verts)]
ear_geom = set(ear_faces)
for f in ear_faces:
    ear_geom.update(f.edges); ear_geom.update(f.verts)
cut = bmesh.ops.bisect_plane(bm, geom=list(ear_geom), dist=.0001,
    plane_co=inverse_world@Vector((0,0,.919)),
    plane_no=(world.to_3x3().transposed()@Vector((0,0,1))).normalized(),
    clear_outer=True, clear_inner=False)
cut_edges = [e for e in cut['geom_cut'] if isinstance(e, bmesh.types.BMEdge) and e.is_boundary]
cut_verts = {v for e in cut_edges for v in e.verts}
# FBX splits coincident vertices at UV/normal seams. Join only the new cut rim.
bmesh.ops.remove_doubles(bm, verts=list(cut_verts), dist=.001)
cut_edges = [e for e in bm.edges if e.is_boundary and
    all(abs((world@v.co).z-.919)<.00002 and (world@v.co).x>.025 for v in e.verts)]
body_rim = [e for e in cut_edges if any(f.material_index == 0 for f in e.link_faces)]
cap_faces = bmesh.ops.holes_fill(bm, edges=body_rim, sides=0)['faces'] if body_rim else []
if not cap_faces:
    raise RuntimeError('The cut body rim could not be capped; leave source wolf untouched')
print('EAR_AUTHORING',len(cap_faces),'closed wound cap faces',flush=True)
for f in cap_faces: f.material_index = 2
for v in {v for e in cut_edges for v in e.verts}:
    p = world@v.co
    p.z += .0018*math.sin(p.x*410 + p.y*180)
    v.co = inverse_world@p
bm.to_mesh(mesh); bm.free()

# Mild emaciation within the existing silhouette; feet and attack organs stay put.
sculpted = 0
for v in mesh.vertices:
    p = world@v.co
    abdomen = math.exp(-((p.y-.12)/.21)**2-((p.z-.52)/.14)**2)
    if abs(p.x)>.065 and -.1<p.y<.4 and p.z>.31:
        p.x *= 1-.12*abdomen
        sculpted += 1
    shoulder = math.exp(-((p.y+.29)/.09)**2-((p.z-.66)/.07)**2)
    p.x *= 1+.028*shoulder
    v.co = inverse_world@p
mesh.update()
rest = mesh.attributes.get('ZombieRestPosition') or mesh.attributes.new('ZombieRestPosition','FLOAT_VECTOR','POINT')
for v,d in zip(mesh.vertices,rest.data): d.vector=world@v.co

# Independent UV atlas prevents wounds appearing on the mirrored opposite side.
mesh.uv_layers.new(name='ZombieUV')
mesh.uv_layers.active = mesh.uv_layers['ZombieUV']
bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
bpy.context.view_layer.objects.active=obj
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(70), island_margin=.012, area_weight=.4)
bpy.ops.object.mode_set(mode='OBJECT')
mesh.uv_layers['ZombieUV'].active_render=True

WOUNDS = [
    {'name':'left_shoulder','center':[.135,-.30,.61],'radii':[.085,.14,.11]},
    {'name':'right_flank','center':[-.125,.08,.55],'radii':[.06,.17,.105]},
    {'name':'left_cheek','center':[.068,-.716,.824],'radii':[.045,.075,.058]},
    {'name':'left_neck','center':[.10,-.47,.71],'radii':[.055,.07,.06]},
]
def material(name, fur=False, cap=False):
    m=bpy.data.materials.new(name);m.use_nodes=True
    ns=m.node_tree.nodes;ns.clear();lk=m.node_tree.links
    def n(kind,label=''):
        x=ns.new(kind);x.label=label;return x
    def put(value,socket):
        if isinstance(value,bpy.types.NodeSocket): lk.new(value,socket)
        else: socket.default_value=value
    def mathn(op,a,b=None):
        x=n('ShaderNodeMath');x.operation=op;put(a,x.inputs[0])
        if b is not None:put(b,x.inputs[1])
        return x.outputs[0]
    def vec(op,a,b=None):
        x=n('ShaderNodeVectorMath');x.operation=op;put(a,x.inputs[0])
        if b is not None:put(b,x.inputs[1])
        return x.outputs['Value'] if op=='LENGTH' else x.outputs['Vector']
    def mix(a,b,t):
        x=n('ShaderNodeMixRGB');put(t,x.inputs[0]);put(a,x.inputs[1]);put(b,x.inputs[2]);return x.outputs[0]
    def smooth(v,lo,hi):
        x=n('ShaderNodeMapRange');x.interpolation_type='SMOOTHSTEP';x.clamp=True
        put(v,x.inputs['Value']);x.inputs['From Min'].default_value=lo;x.inputs['From Max'].default_value=hi
        return x.outputs[0]
    attr=n('ShaderNodeAttribute','Rest-space metres');attr.attribute_name='ZombieRestPosition';pos=attr.outputs['Vector']
    uv=n('ShaderNodeUVMap');uv.uv_map='SourceUV'
    noise=n('ShaderNodeTexNoise');lk.new(pos,noise.inputs['Vector']);noise.inputs['Scale'].default_value=41
    noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.7
    jitter=mathn('MULTIPLY',mathn('SUBTRACT',noise.outputs['Fac'],.5),.24)
    def ellipse(center,radii,factor=1.):
        d=vec('LENGTH',vec('DIVIDE',vec('SUBTRACT',pos,center),tuple(v*factor for v in radii)))
        return mathn('ADD',mathn('SUBTRACT',1,d),jitter)
    wound=0.; exposed=0.
    for w in WOUNDS:
        wound=mathn('MAXIMUM',wound,smooth(ellipse(w['center'],w['radii']),-.03,.25))
        exposed=mathn('MAXIMUM',exposed,smooth(ellipse(w['center'],w['radii'],1.7),-.12,.20))
    # Three narrow irregular claw tears on the left rib wall.
    for y in [-.06,-.015,.031]:
        slash=smooth(ellipse((.135,y,.60),(.040,.011,.076)),-.02,.32)
        wound=mathn('MAXIMUM',wound,mathn('MULTIPLY',slash,.86))
    if cap: wound=1.;exposed=1.
    def tex(path, color=True, box=False):
        x=n('ShaderNodeTexImage');x.image=bpy.data.images.load(str(path),check_existing=True)
        x.image.colorspace_settings.name='sRGB' if color else 'Non-Color'
        if box:
            x.projection='BOX';x.projection_blend=.25
            lk.new(vec('MULTIPLY',pos,(3.4,3.4,3.4)),x.inputs['Vector'])
        else:lk.new(uv.outputs['UV'],x.inputs['Vector'])
        return x
    original=tex(R/'Source/T_WolfDark_BaseColorAlpha.png')
    orm=tex(R/'Source/T_Wolf_OcclusionRoughnessMetallic.png',False)
    original_n=tex(R/'Source/T_Wolf_Nml.png',False)
    skin_col=tex(SKIN/'T_ZombieSkinMaterial1_basecolor.png',True,True)
    skin_h=tex(SKIN/'T_ZombieSkinMaterial1_height.png',False,True)
    skin_r=tex(SKIN/'T_ZombieSkinMaterial1_roughness.png',False,True)
    skin_ao=tex(SKIN/'T_ZombieSkinMaterial1_ambientocclusion.png',False,True)
    gray=n('ShaderNodeRGBToBW');lk.new(original.outputs['Color'],gray.inputs[0])
    fur_color=mix(original.outputs['Color'],gray.outputs[0],.58)
    skin_gray=n('ShaderNodeRGBToBW');lk.new(skin_col.outputs[0],skin_gray.inputs[0])
    skin_variation=mathn('MULTIPLY_ADD',skin_gray.outputs[0],1.45)
    # Map authored organic tissue detail into muted necrotic skin, without uniform red fur.
    skin_color=mix((.032,.041,.029,1),(.19,.21,.155,1),mathn('ADD',skin_variation,.12))
    scar_color=mix((.038,.0035,.003,1),(.20,.035,.020,1),noise.outputs['Fac'])
    skin_color=mix(skin_color,scar_color,wound)
    base=mix(fur_color,skin_color,exposed)
    rough=mix((.84,.84,.84,1),skin_r.outputs[0],exposed)
    rough=mix(rough,(.32,.32,.32,1),wound)
    sep=n('ShaderNodeSeparateColor');lk.new(orm.outputs['Color'],sep.inputs[0])
    ao=mix(sep.outputs['Red'],skin_ao.outputs[0],exposed)
    packed=n('ShaderNodeCombineColor');put(ao,packed.inputs['Red']);put(rough,packed.inputs['Green']);packed.inputs['Blue'].default_value=0
    # DirectX source normal -> Blender tangent normal before the new UV tangent bake.
    nspl=n('ShaderNodeSeparateColor');lk.new(original_n.outputs[0],nspl.inputs[0])
    nc=n('ShaderNodeCombineColor');lk.new(nspl.outputs['Red'],nc.inputs['Red'])
    lk.new(mathn('SUBTRACT',1,nspl.outputs['Green']),nc.inputs['Green']);lk.new(nspl.outputs['Blue'],nc.inputs['Blue'])
    normal=n('ShaderNodeNormalMap');normal.uv_map='SourceUV';lk.new(nc.outputs[0],normal.inputs['Color'])
    put(mathn('SUBTRACT',.68,mathn('MULTIPLY',exposed,.53)),normal.inputs['Strength'])
    bump=n('ShaderNodeBump');bump.inputs['Distance'].default_value=.0025
    put(mathn('MULTIPLY',exposed,.62),bump.inputs['Strength']);lk.new(skin_h.outputs[0],bump.inputs['Height'])
    lk.new(normal.outputs[0],bump.inputs['Normal'])
    torn=n('ShaderNodeBump');torn.inputs['Distance'].default_value=.004;torn.inputs['Strength'].default_value=.5
    lk.new(mathn('SUBTRACT',1,wound),torn.inputs['Height']);lk.new(bump.outputs[0],torn.inputs['Normal'])
    alpha=mathn('MULTIPLY',original.outputs['Alpha'],mathn('SUBTRACT',1,smooth(exposed,.18,.58))) if fur else 1.
    bs=n('ShaderNodeBsdfPrincipled');put(base,bs.inputs['Base Color']);put(rough,bs.inputs['Roughness'])
    lk.new(torn.outputs[0],bs.inputs['Normal']);put(alpha,bs.inputs['Alpha'])
    bs.inputs['Specular IOR Level'].default_value=.32
    out=n('ShaderNodeOutputMaterial');lk.new(bs.outputs[0],out.inputs['Surface'])
    return m,{'BaseColor':base,'ORM':packed.outputs[0],'Opacity':alpha},out,bs

material_defs=[material('M_ZombieDog_Skin_Source'),material('M_ZombieDog_Fur_Source',fur=True),material('M_ZombieDog_EarScar_Source',cap=True)]
face_materials=[p.material_index for p in mesh.polygons]
mesh.materials.clear()
for m,*_ in material_defs:mesh.materials.append(m)
for polygon,index in zip(mesh.polygons,face_materials):polygon.material_index=index
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=4
scene.render.bake.margin=12;scene.render.bake.use_selected_to_active=False
scene.render.bake.use_clear=True
bpy.ops.wm.save_as_mainfile(filepath=str(R/'ZombieDog_Authoring.blend'))

files={}
for semantic in ['BaseColor','ORM','Opacity','Normal']:
    img=bpy.data.images.new('T_ZombieDog_'+semantic,2048,2048,alpha=False)
    img.colorspace_settings.name='sRGB' if semantic=='BaseColor' else 'Non-Color'
    temporary=[]
    for m,outputs,out,bs in material_defs:
        nodes=m.node_tree.nodes;links=m.node_tree.links
        target=nodes.new('ShaderNodeTexImage');target.image=img;nodes.active=target
        if semantic!='Normal':
            emission=nodes.new('ShaderNodeEmission');s=outputs[semantic]
            if isinstance(s,bpy.types.NodeSocket):links.new(s,emission.inputs['Color'])
            else:emission.inputs['Color'].default_value=(s,s,s,1)
            links.new(emission.outputs[0],out.inputs['Surface']);temporary.append((m,emission))
    if semantic=='Normal':
        bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',normal_r='POS_X',normal_g='NEG_Y',normal_b='POS_Z')
    else:bpy.ops.object.bake(type='EMIT')
    for m,em in temporary:m.node_tree.nodes.remove(em)
    for m,_,out,bs in material_defs:m.node_tree.links.new(bs.outputs[0],out.inputs['Surface'])
    img.filepath_raw=str(R/'Textures'/(img.name+'.png'));img.file_format='PNG';img.save()
    files[semantic]=img.filepath_raw
    print('ZOMBIE_DOG_TEXTURE_BAKED',semantic,flush=True)

# Keep editable source UVs in .blend; exported runtime UV0 is the dedicated atlas.
bpy.ops.wm.save_as_mainfile(filepath=str(R/'ZombieDog_Authoring.blend'))
mesh.uv_layers.remove(mesh.uv_layers['SourceUV'])
mesh.uv_layers.active=mesh.uv_layers['ZombieUV'];mesh.uv_layers['ZombieUV'].active_render=True
rig.data.pose_position='POSE'
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(R/'SK_ZombieDog.fbx'),use_selection=True,
    object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,
    use_armature_deform_only=False,axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',use_mesh_modifiers=False,
    mesh_smooth_type='FACE',path_mode='STRIP')
(R/'authoring_manifest.json').write_text(json.dumps({
    'source_mesh':'/Game/Monsters/Wolf/SK_Wolf_Gameplay','source_blend':'Source/Wolf_Source.blend',
    'authoring_blend':'ZombieDog_Authoring.blend','fbx':'SK_ZombieDog.fbx','textures':files,
    'wounds_metres_in_blender_rest_space':WOUNDS,'ear_cut_height_m':.919,
    'ear_cap_faces_created':len(cap_faces),'abdomen_vertices_sculpted':sculpted,
    'bone_transforms_modified':False,'animations_modified':False,
    'skin_source':str(SKIN),'new_uv_atlas':'ZombieUV 2048; original UV retained in authoring blend',
    'runtime_tested':False,'preview_rendered':False,
},indent=2),encoding='utf-8')
print('ZOMBIE_DOG_MODEL_AND_TEXTURES_AUTHORED',flush=True)
