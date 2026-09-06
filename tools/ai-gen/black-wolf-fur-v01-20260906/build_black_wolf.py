"""Author a black fur wolf from the active Quaternius wolf.
Existing skeleton and animation actions are retained. No generated motion.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.noise import noise_vector
R=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(R.parents[2]/'assets/models/wolf_quaternius.gltf'))
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
bm.normal_update();bm.to_mesh(body.data);bm.free();body.data.update()
for p in body.data.polygons:p.use_smooth=True
for v in body.data.vertices:
    values=sorted([(g.group,g.weight) for g in v.groups if g.weight>1e-8],key=lambda x:-x[1])[:4]
    total=sum(w for _,w in values);assert total>0
    for group in body.vertex_groups:group.remove([v.index])
    for index,w in values:body.vertex_groups[index].add([v.index],w/total,'REPLACE')

# Non-overlapping UV atlas; seam splits during export do not alter skinning.
bpy.ops.object.select_all(action='DESELECT');body.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.012,area_weight=.5,correct_aspect=True)
bpy.ops.object.mode_set(mode='OBJECT')
fur_image=bpy.data.images.load(str(R/'fur-source.png'));fur_image.pack()

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
    mat=bpy.data.materials.new('BlackWolf_'+['Coat','Nose','Undercoat','Eyes'][material_index]+'_Editable')
    mat.use_nodes=True;mat.use_fake_user=True;nt=mat.node_tree;nt.nodes.clear()
    output=node(nt,'ShaderNodeOutputMaterial','Surface')
    bs=node(nt,'ShaderNodeBsdfPrincipled','Editable PBR');nt.links.new(bs.outputs['BSDF'],output.inputs['Surface'])
    bs.inputs['Metallic'].default_value=0
    coord=node(nt,'ShaderNodeTexCoord','Rest-space anatomy');position=coord.outputs['Object']
    if material_index in [0,2]:
        mapping=node(nt,'ShaderNodeMapping','Fur direction and strand scale')
        mapping.inputs['Rotation'].default_value=(math.pi/2,0,0)
        mapping.inputs['Scale'].default_value=(1.15,1.15,1.15)
        nt.links.new(position,mapping.inputs['Vector'])
        fur=node(nt,'ShaderNodeTexImage','Existing generated canine fur source')
        fur.image=fur_image;fur.projection='BOX';fur.projection_blend=.25;fur.extension='REPEAT'
        nt.links.new(mapping.outputs['Vector'],fur.inputs['Vector'])
        bw=node(nt,'ShaderNodeRGBToBW','Fur strand height');nt.links.new(fur.outputs['Color'],bw.inputs[0])
        color=ramp(nt,bw.outputs[0],[(.0,(.004,.005,.006)),(.14,(.028,.030,.034)),(.50,(.09,.093,.10)),(1.,(.14,.15,.16))],'Black coat with charcoal highlights')
        if material_index==2:
            color=mix(nt,.12,color,(.09,.09,.085),'Subtle charcoal undercoat')
        rough=ramp(nt,bw.outputs[0],[(0.,.86),(.6,.69)],'Natural dry fur roughness')
        bump=node(nt,'ShaderNodeBump','Short fur micro relief')
        bump.inputs['Strength'].default_value=.55;bump.inputs['Distance'].default_value=.030
        nt.links.new(bw.outputs[0],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    elif material_index==1:
        fine=noise(nt,position,90,2,'Nose pores')
        color=ramp(nt,fine,[(.0,(.004,.004,.004)),(1.,(.016,.017,.018))],'Black nose')
        rough=ramp(nt,fine,[(0.,.26),(1.,.38)],'Nose moisture')
        bump=node(nt,'ShaderNodeBump','Nose micro relief');bump.inputs['Distance'].default_value=.004
        nt.links.new(fine,bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    else:
        eye=node(nt,'ShaderNodeRGB','Healthy amber eyes');eye.outputs[0].default_value=(.30,.115,.015,1)
        color=eye.outputs[0]
        rough=mathnode(nt,'ADD',.22,0)
    nt.links.new(color,bs.inputs['Base Color']);nt.links.new(rough,bs.inputs['Roughness'])
    body.data.materials[material_index]=mat
    procedurals.append(mat);bake_channels.append((color,rough,bs,output))

textures=R/'textures';textures.mkdir(exist_ok=True)
s.render.engine='CYCLES';s.cycles.samples=4;s.cycles.device='CPU'
s.render.bake.use_selected_to_active=False;s.render.bake.margin=12
images={}
for channel in ['albedo','roughness','normal']:
    im=bpy.data.images.new('BlackWolf_'+channel,width=2048,height=2048,alpha=False)
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
    print('BLACK_WOLF_BAKED',channel,flush=True)

# Game material uses the baked atlas; editable procedural originals remain in the blend.
game=bpy.data.materials.new('BlackWolf_PBR');game.use_nodes=True
nt=game.node_tree;bs=nt.nodes.get('Principled BSDF');bs.inputs['Metallic'].default_value=0
for channel in ['albedo','roughness','normal']:
    tex=node(nt,'ShaderNodeTexImage',channel);tex.image=images[channel]
    if channel=='normal':
        normal=node(nt,'ShaderNodeNormalMap','Baked short fur normals')
        nt.links.new(tex.outputs['Color'],normal.inputs['Color']);nt.links.new(normal.outputs[0],bs.inputs['Normal'])
    else:nt.links.new(tex.outputs['Color'],bs.inputs['Base Color' if channel=='albedo' else 'Roughness'])
for mat,(color,rough,bs0,out) in zip(procedurals,bake_channels):mat.node_tree.links.new(bs0.outputs[0],out.inputs['Surface'])
body.data.materials.clear();body.data.materials.append(game)
for poly in body.data.polygons:poly.material_index=0
body.name='BlackWolf'
a.animation_data.action=bpy.data.actions['Idle']
if a.animation_data.action.slots:a.animation_data.action_slot=a.animation_data.action.slots[0]
s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'black-wolf-fur-v01.blend'))
bpy.ops.object.select_all(action='DESELECT');a.select_set(True);body.select_set(True)
bpy.context.view_layer.objects.active=a
bpy.ops.export_scene.gltf(filepath=str(R/'black-wolf-fur-v01.glb'),export_format='GLB',use_selection=True,
 export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,
 export_frame_step=1,export_def_bones=False)
report={'source':'assets/models/wolf_quaternius.gltf','before':before,'after':{'vertices':len(body.data.vertices),'polygons':len(body.data.polygons)},
 'bone_count':len(a.data.bones),'clips':{x.name:(x.frame_range[1]-x.frame_range[0])/30 for x in bpy.data.actions},
 'split_vertex_skin_difference':max_weight_difference,'max_sculpt_source_units':0,'runtime_scale':.3,
 'max_skin_weight_error':max(abs(sum(g.weight for g in v.groups)-1) for v in body.data.vertices),
 'max_influences':max(len(v.groups) for v in body.data.vertices),'wounds':[],'texture_size':[2048,2048],
 'geometry_method':'weld matching split vertices, preserve source triangles and positions, smooth normals; no sculpt or subdivision'}
(R/'build-report.json').write_text(json.dumps(report,indent=2));print('BLACK_WOLF_BUILD_COMPLETE',json.dumps(report))
