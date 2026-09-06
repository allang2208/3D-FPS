"""Author a textured, skinned zombie canine from the active Quaternius wolf.
Existing skeleton and animation actions are retained. No generated motion.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.noise import noise_vector
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R/'source-wolf.blend'))
s=bpy.context.scene;s.render.fps=30
a=bpy.data.objects['AnimalArmature'];body=bpy.data.objects['Wolf']
for tr in a.animation_data.nla_tracks:tr.mute=True
a.animation_data.action=None
for pb in a.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
before={'vertices':len(body.data.vertices),'polygons':len(body.data.polygons)}
# Verify coincident hard-normal splits share their skin before welding them.
groups={};max_weight_difference=0.
for v in body.data.vertices:
    key=tuple(round(c,6) for c in v.co);w={g.group:g.weight for g in v.groups}
    if key in groups:
        old=groups[key]
        max_weight_difference=max(max_weight_difference,max(abs(w.get(i,0)-old.get(i,0)) for i in set(w)|set(old)))
    else:groups[key]=w
assert max_weight_difference<1e-4,('inconsistent split skin',max_weight_difference)
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
# Add one local interpolation level for shallow wounds without a new skeleton.
bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=True)
bm.normal_update();bm.to_mesh(body.data);bm.free();body.data.update()
for p in body.data.polygons:p.use_smooth=True
for v in body.data.vertices:
    values=sorted([(g.group,g.weight) for g in v.groups if g.weight>1e-8],key=lambda x:-x[1])[:4]
    total=sum(w for _,w in values);assert total>0
    for group in body.vertex_groups:group.remove([v.index])
    for index,w in values:body.vertex_groups[index].add([v.index],w/total,'REPLACE')

WOUNDS=[
 {'name':'left_rib_flank','center':(.43,.04,1.67),'radius':(.30,.60,.37)},
 {'name':'right_shoulder','center':(-.41,-.90,1.63),'radius':(.28,.29,.36)},
 {'name':'right_hind_thigh','center':(-.38,1.10,1.24),'radius':(.25,.33,.34)},
 {'name':'left_muzzle','center':(.19,-2.15,2.11),'radius':(.14,.24,.145)},
]
def field(co,w):return math.sqrt(sum(((co[i]-w['center'][i])/w['radius'][i])**2 for i in range(3)))
def smooth(lo,hi,x):
    u=max(0,min(1,(x-lo)/(hi-lo)));return u*u*(3-2*u)
max_sculpt=0.
for v in body.data.vertices:
    original=v.co.copy();x,y,z=v.co
    # Slightly drawn-in abdomen, keep limb pivots and the original head silhouette.
    abdomen=math.exp(-((y-.30)/.65)**2-((z-1.43)/.36)**2)
    v.co.x*=1-.11*abdomen
    depth=min(field(v.co,w) for w in WOUNDS)
    v.co-=v.normal*.035*(1-smooth(.35,1.,depth))
    max_sculpt=max(max_sculpt,(v.co-original).length)
body.data.update()

# Non-overlapping UV atlas; seam splits during export do not alter skinning.
bpy.ops.object.select_all(action='DESELECT');body.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.012,area_weight=.5,correct_aspect=True)
bpy.ops.object.mode_set(mode='OBJECT')
fur_image=bpy.data.images.load(str(R/'fur-source.png'));fur_image.pack()
wound_image=bpy.data.images.load(str(R/'wound-source.png'));wound_image.pack()

def node(nt,kind,name):
    n=nt.nodes.new(kind);n.label=name;n.name=name;return n
def mathnode(nt,op,a,b=None,name=''):
    n=node(nt,'ShaderNodeMath',name or op);n.operation=op
    for i,val in enumerate([a,b]):
        if val is None:continue
        if isinstance(val,(int,float)):n.inputs[i].default_value=val
        else:nt.links.new(val,n.inputs[i])
    return n.outputs[0]
def ramp(nt,value,stops,name):
    n=node(nt,'ShaderNodeValToRGB',name);nt.links.new(value,n.inputs['Fac'])
    cr=n.color_ramp;cr.interpolation='EASE'
    while len(cr.elements)>2:cr.elements.remove(cr.elements[-1])
    for i,(pos,color) in enumerate(stops):
        e=cr.elements[i] if i<2 else cr.elements.new(pos)
        e.position=pos;e.color=(color,color,color,1) if isinstance(color,(float,int)) else (*color,1)
    return n.outputs['Color']
def mix(nt,fac,c0,c1,name):
    n=node(nt,'ShaderNodeMixRGB',name)
    for socket,value in [(n.inputs[0],fac),(n.inputs[1],c0),(n.inputs[2],c1)]:
        if isinstance(value,(tuple,list)):socket.default_value=(*value,1)
        elif isinstance(value,(float,int)):socket.default_value=value
        else:nt.links.new(value,socket)
    return n.outputs[0]
def noise(nt,vector,scale,detail,name):
    n=node(nt,'ShaderNodeTexNoise',name);n.inputs['Scale'].default_value=scale;n.inputs['Detail'].default_value=detail
    nt.links.new(vector,n.inputs['Vector']);return n.outputs['Fac']

procedurals=[];bake_channels=[]
for material_index,oldmat in enumerate(list(body.data.materials)):
    mat=bpy.data.materials.new('ZombieDog_'+['Coat','Nose','Undercoat','Eyes'][material_index]+'_Procedural')
    mat.use_nodes=True;mat.use_fake_user=True;nt=mat.node_tree;nt.nodes.clear()
    output=node(nt,'ShaderNodeOutputMaterial','Surface')
    bs=node(nt,'ShaderNodeBsdfPrincipled','Editable PBR');nt.links.new(bs.outputs['BSDF'],output.inputs['Surface'])
    bs.inputs['Metallic'].default_value=0
    texcoord=node(nt,'ShaderNodeTexCoord','Rest-space anatomy')
    position=texcoord.outputs['Object']
    if material_index in [0,2]:
        mapping=node(nt,'ShaderNodeMapping','Fur direction and strand scale')
        mapping.inputs['Rotation'].default_value=(math.pi/2,0,0)
        mapping.inputs['Scale'].default_value=(1.15,1.15,1.15)
        nt.links.new(position,mapping.inputs['Vector'])
        fur=node(nt,'ShaderNodeTexImage','Generated matted canine fur source')
        fur.image=fur_image;fur.projection='BOX';fur.projection_blend=.25;fur.extension='REPEAT'
        nt.links.new(mapping.outputs['Vector'],fur.inputs['Vector'])
        tint=node(nt,'ShaderNodeMixRGB','Ash grey coat tint');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1
        tint.inputs[2].default_value=(1.7,1.75,1.48,1) if material_index==0 else (2.15,2.02,1.65,1)
        nt.links.new(fur.outputs['Color'],tint.inputs[1]);fur_color=tint.outputs[0]
        coarse=noise(nt,position,9,3,'Irregular necrosis borders')
        fine=noise(nt,position,95,2,'Skin pores')
        distances=[];wound_coordinates=[]
        for wound in WOUNDS:
            sub=node(nt,'ShaderNodeVectorMath',wound['name']+' position');sub.operation='SUBTRACT';sub.inputs[1].default_value=wound['center'];nt.links.new(position,sub.inputs[0])
            div=node(nt,'ShaderNodeVectorMath',wound['name']+' extent');div.operation='DIVIDE';div.inputs[1].default_value=wound['radius'];nt.links.new(sub.outputs[0],div.inputs[0])
            wound_coordinates.append(div.outputs[0])
            length=node(nt,'ShaderNodeVectorMath',wound['name']+' distance');length.operation='LENGTH';nt.links.new(div.outputs[0],length.inputs[0]);distances.append(length.outputs['Value'])
        distance=distances[0]
        for other in distances[1:]:distance=mathnode(nt,'MINIMUM',distance,other)
        edge_noise=mathnode(nt,'MULTIPLY',mathnode(nt,'SUBTRACT',coarse,.5),.60)
        distance=mathnode(nt,'ADD',distance,edge_noise)
        wide_distance=mathnode(nt,'MULTIPLY',distance,.5)
        bald=ramp(nt,wide_distance,[(.44,1),(.60,.90),(.875,0)],'Balding outside wounds')
        skin_color=ramp(nt,coarse,[(.18,(.045,.05,.040)),(.50,(.11,.12,.09)),(.80,(.19,.18,.12))],'Sallow skin mottling')
        coat_skin=mix(nt,bald,fur_color,skin_color,'Fur to bare skin')
        wound_mask=ramp(nt,distance,[(.67,1),(.88,1),(1.02,0)],'Open wound mask')
        # Striated tissue is a separate material layer, not a red recolour of fur.
        stretch=node(nt,'ShaderNodeVectorMath','Muscle fibre direction');stretch.operation='MULTIPLY';stretch.inputs[1].default_value=(40,9,65);nt.links.new(position,stretch.inputs[0])
        tissue_noise=noise(nt,stretch.outputs[0],1.0,2,'Tissue fibres')
        tissue_color=ramp(nt,tissue_noise,[(.15,(.020,.004,.007)),(.43,(.065,.009,.013)),(.65,(.15,.025,.025)),(.90,(.19,.045,.035))],'Dark red exposed tissue')
        rim_color=ramp(nt,distance,[(.30,(.075,.008,.013)),(.73,(.12,.016,.020)),(.88,(.030,.012,.010)),(1.0,(.08,.055,.035))],'Dry irregular wound rim')
        tissue=mix(nt,.55,rim_color,tissue_color,'Tissue variation')
        color=mix(nt,wound_mask,coat_skin,tissue,'Final coat skin wounds')
        rough=mix(nt,bald,(.90,.90,.90),(.72,.72,.72),'Dry skin roughness')
        rough=mix(nt,wound_mask,rough,(.57,.57,.57),'Wound roughness')
        bw=node(nt,'ShaderNodeRGBToBW','Fur strand height');nt.links.new(fur.outputs['Color'],bw.inputs[0])
        base_height=mix(nt,bald,bw.outputs[0],fine,'Fur and pores')
        pit=ramp(nt,wide_distance,[(.0,.08),(.30,.12),(.41,.66),(.495,.48),(.675,.43)],'Inset wound with raised lip')
        height=mix(nt,bald,base_height,pit,'Wound lip depth')
        detail=mix(nt,wound_mask,height,tissue_noise,'Fine fibre relief')
        # Texture-authored torn tissue replaces the regular procedural red patch.
        # Each projection is limited to its own anatomical ellipsoid.
        color=fur_color
        for wi,(coords,dist) in enumerate(zip(wound_coordinates,distances)):
            xyz=node(nt,'ShaderNodeSeparateXYZ','Wound local projection '+str(wi));nt.links.new(coords,xyz.inputs[0])
            u=mathnode(nt,'ADD',mathnode(nt,'MULTIPLY',xyz.outputs['Y'],.35 if wi%2==0 else -.35),.5)
            v=mathnode(nt,'ADD',mathnode(nt,'MULTIPLY',xyz.outputs['Z'],.35),.5)
            uv=node(nt,'ShaderNodeCombineXYZ','Wound texture UV '+str(wi));nt.links.new(u,uv.inputs['X']);nt.links.new(v,uv.inputs['Y'])
            patch=node(nt,'ShaderNodeTexImage','Torn dry tissue source '+str(wi));patch.image=wound_image;patch.extension='EXTEND'
            nt.links.new(uv.outputs[0],patch.inputs['Vector'])
            noisy=mathnode(nt,'ADD',dist,edge_noise)
            mask=ramp(nt,mathnode(nt,'MULTIPLY',noisy,.5),[(.43,1),(.62,1),(.82,0)],'Anatomical patch feather '+str(wi))
            color=mix(nt,mask,color,patch.outputs['Color'],'Projected wound '+str(wi))
            grey=node(nt,'ShaderNodeRGBToBW','Wound micro relief '+str(wi));nt.links.new(patch.outputs['Color'],grey.inputs[0])
            detail=mix(nt,mask,detail,grey.outputs[0],'Wound relief '+str(wi))
        bump=node(nt,'ShaderNodeBump','Fur pores and wound relief');bump.inputs['Strength'].default_value=.38;bump.inputs['Distance'].default_value=.024
        nt.links.new(detail,bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    elif material_index==1:
        fine=noise(nt,position,80,2,'Nose dry pores')
        color=ramp(nt,fine,[(.15,(.012,.011,.01)),(.80,(.046,.036,.027))],'Dry nose')
        rough=mix(nt,.5,(.42,.42,.42),(.58,.58,.58),'Nose roughness')
        bump=node(nt,'ShaderNodeBump','Nose micro relief');bump.inputs['Distance'].default_value=.008
        nt.links.new(fine,bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    else:
        xyz=node(nt,'ShaderNodeSeparateXYZ','Left right eye');nt.links.new(position,xyz.inputs[0])
        side=mathnode(nt,'GREATER_THAN',xyz.outputs['X'],0)
        color=mix(nt,side,(.11,.037,.017),(.48,.54,.43),'One clouded eye')
        rough=mix(nt,side,(.35,.35,.35),(.30,.30,.30),'Eye surface')
    nt.links.new(color,bs.inputs['Base Color']);nt.links.new(rough,bs.inputs['Roughness'])
    body.data.materials[material_index]=mat
    procedurals.append(mat);bake_channels.append((color,rough,bs,output))

textures=R/'textures';textures.mkdir(exist_ok=True)
s.render.engine='CYCLES';s.cycles.samples=4;s.cycles.device='CPU'
s.render.bake.use_selected_to_active=False;s.render.bake.margin=12
images={}
for channel in ['albedo','roughness','normal']:
    im=bpy.data.images.new('ZombieDog_'+channel,width=2048,height=2048,alpha=False)
    im.colorspace_settings.name='sRGB' if channel=='albedo' else 'Non-Color'
    images[channel]=im
    for mat,(color,rough,bs,out) in zip(procedurals,bake_channels):
        nt=mat.node_tree
        target=node(nt,'ShaderNodeTexImage','Bake '+channel);target.image=im
        for n in nt.nodes:n.select=False
        target.select=True;nt.nodes.active=target
        if channel!='normal':
            emission=node(nt,'ShaderNodeEmission','Bake channel '+channel)
            nt.links.new(color if channel=='albedo' else rough,emission.inputs['Color'])
            nt.links.new(emission.outputs[0],out.inputs['Surface'])
        else:nt.links.new(bs.outputs[0],out.inputs['Surface'])
    bpy.ops.object.bake(type='NORMAL' if channel=='normal' else 'EMIT',normal_space='TANGENT')
    im.filepath_raw=str(textures/(channel+'.png'));im.file_format='PNG';im.save();im.pack()
    print('ZOMBIE_DOG_BAKED',channel,flush=True)

# Game material uses the baked atlas; editable procedural originals remain in the blend.
game=bpy.data.materials.new('ZombieDog_PBR');game.use_nodes=True
nt=game.node_tree;bs=nt.nodes.get('Principled BSDF');bs.inputs['Metallic'].default_value=0
for channel in ['albedo','roughness','normal']:
    tex=node(nt,'ShaderNodeTexImage',channel);tex.image=images[channel]
    if channel=='normal':
        normal=node(nt,'ShaderNodeNormalMap','Baked fur and wound normals')
        nt.links.new(tex.outputs['Color'],normal.inputs['Color']);nt.links.new(normal.outputs[0],bs.inputs['Normal'])
    else:nt.links.new(tex.outputs['Color'],bs.inputs['Base Color' if channel=='albedo' else 'Roughness'])
for mat,(color,rough,bs0,out) in zip(procedurals,bake_channels):mat.node_tree.links.new(bs0.outputs[0],out.inputs['Surface'])
body.data.materials.clear();body.data.materials.append(game)
for poly in body.data.polygons:poly.material_index=0
body.name='ZombieDog'
a.animation_data.action=bpy.data.actions['Idle']
if a.animation_data.action.slots:a.animation_data.action_slot=a.animation_data.action.slots[0]
s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'zombie-dog-v01.blend'))
bpy.ops.object.select_all(action='DESELECT');a.select_set(True);body.select_set(True)
bpy.context.view_layer.objects.active=a
bpy.ops.export_scene.gltf(filepath=str(R/'zombie-dog-v01.glb'),export_format='GLB',use_selection=True,
 export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,
 export_frame_step=1,export_def_bones=False)
report={'source':'assets/models/wolf_quaternius.gltf','before':before,'after':{'vertices':len(body.data.vertices),'polygons':len(body.data.polygons)},
 'bone_count':len(a.data.bones),'clips':{x.name:(x.frame_range[1]-x.frame_range[0])/30 for x in bpy.data.actions},
 'split_vertex_skin_difference':max_weight_difference,'max_sculpt_source_units':max_sculpt,'runtime_scale':.3,
 'max_skin_weight_error':max(abs(sum(g.weight for g in v.groups)-1) for v in body.data.vertices),
 'max_influences':max(len(v.groups) for v in body.data.vertices),'wounds':WOUNDS,'texture_size':[2048,2048],
 'wound_method':'localized texture projection and shallow mesh recess on original interpolated skin'}
(R/'build-report.json').write_text(json.dumps(report,indent=2));print('ZOMBIE_DOG_BUILD_COMPLETE',json.dumps(report))
