"""Refine three blade finishes on the existing geometry/UV0; no gameplay changes."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
OLD=P.parent/'KukriBladeVariants20261026'
sys.path.insert(0,str(P.parent/'KukriComponentVariants20261026'))
from asset_tools import node,put,op,mix,tex,make_mat,bake,smooth,export

for folder in ('Export','Textures','IconInputs','Icons','Before','Receipts'):(P/folder).mkdir(exist_ok=True)
data=json.loads((OLD/'variants.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(OLD/'Kukri_Blade_Variants_Editable.blend'))
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=32
scene.render.bake.use_selected_to_active=False
names={v['object'] for v in data['variants']}
for obj in list(scene.objects):
    if obj.name not in names:bpy.data.objects.remove(obj,do_unlink=True)
original=P.parent/'Kukri20261020/Textures'
# Reusing the source master must not give new bake images a .001 datablock suffix.
for image in bpy.data.images:
    if any(image.name.startswith('T_Kukri_'+e['kind']+'_') for e in data['variants']):
        image.name='SurfaceV1_Source_'+image.name

def refine_normals(obj):
    mesh=obj.data
    old=[Vector(n.vector) for n in mesh.corner_normals]
    adjacency=[[] for v in mesh.vertices]
    for poly in mesh.polygons:
        for vi in poly.vertices:adjacency[vi].append(poly)
    normals=[]
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            vertex=mesh.vertices[mesh.loops[li].vertex_index]
            weight=smooth(.066,.092,vertex.co.z)
            nearby=[p for p in adjacency[vertex.index] if p.normal.dot(poly.normal)>.819152]
            weighted=sum((p.normal*p.area for p in nearby),Vector())
            target=weighted.normalized() if weighted.length_squared>1e-16 else poly.normal
            normals.append(old[li].lerp(target,weight).normalized())
    mesh.normals_split_custom_set(normals)

def scaled_noise(nt,coord,scale,detail=2,roughness=.5):
    vector=node(nt,'ShaderNodeVectorMath',operation='MULTIPLY')
    put(nt,vector.inputs[0],coord);vector.inputs[1].default_value=scale
    noise=node(nt,'ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1
    noise.inputs['Detail'].default_value=detail;noise.inputs['Roughness'].default_value=roughness
    nt.links.new(vector.outputs[0],noise.inputs['Vector'])
    return noise.outputs['Fac']

def fields(obj,kind):
    mesh=obj.data;old=mesh.color_attributes['BladeData']
    # Existing per-corner q identifies the original edge/spine, independent of UV seams.
    zmin=.044;zmax=max(v.co.z for v in mesh.vertices)
    sections=[]
    for index in range(257):
        z=zmin+(zmax-zmin)*index/256;xs=[]
        for edge in mesh.edges:
            a,b=[mesh.vertices[j].co for j in edge.vertices]
            if min(a.z,b.z)<=z<=max(a.z,b.z) and abs(b.z-a.z)>1e-9:
                xs.append(a.x+(b.x-a.x)*(z-a.z)/(b.z-a.z))
        sections.append(max(xs)-min(xs) if xs else 0)
    def width(z):
        t=max(0,min(256,(z-zmin)/(zmax-zmin)*256));i=min(int(t),255)
        return sections[i]*(1-(t-i))+sections[i+1]*(t-i)
    field=mesh.color_attributes.get('SurfaceField') or mesh.color_attributes.new(name='SurfaceField',type='FLOAT_COLOR',domain='CORNER')
    edge_width={'Swift':.0042,'HeavyBack':.0064,'FoldedBalanced':.0050}[kind]
    for i,loop in enumerate(mesh.loops):
        co=mesh.vertices[loop.vertex_index].co;q=old.data[i].color[2];w=width(co.z)
        root=smooth(.044,.064,co.z)
        edge=1-smooth(.0008,edge_width,(1-q)*w)
        field.data[i].color=(root,edge,q*w,q)
    return edge_width

def material(kind):
    mat,nt,bs,out=make_mat('M_Kukri_'+kind+'_SurfaceV2_Author')
    attr=node(nt,'ShaderNodeVertexColor',layer_name='SurfaceField')
    split=node(nt,'ShaderNodeSeparateColor');nt.links.new(attr.outputs['Color'],split.inputs['Color'])
    root,edge,across=split.outputs[0],split.outputs[1],split.outputs[2]
    tc=node(nt,'ShaderNodeTexCoord');coord=tc.outputs['Object']
    xyz=node(nt,'ShaderNodeSeparateXYZ');nt.links.new(coord,xyz.inputs[0]);z=xyz.outputs['Z']
    grain=scaled_noise(nt,coord,(3600,3000,90),1,.4)
    broad=scaled_noise(nt,coord,(60,60,60),2,.45)
    forging=scaled_noise(nt,coord,(850,850,850),2,.42)
    # The fine directional grain affects roughness much more than the base color.
    colors={'Swift':(.30,.33),'HeavyBack':(.215,.245),'FoldedBalanced':(.255,.335)}
    a,b=colors[kind];pattern=grain
    if kind=='FoldedBalanced':
        bend=op(nt,'ADD',op(nt,'MULTIPLY',z,52),op(nt,'MULTIPLY',op(nt,'SINE',op(nt,'MULTIPLY',z,137)),.7))
        bend=op(nt,'MULTIPLY',op(nt,'SINE',bend),18)
        frequency=op(nt,'ADD',1,op(nt,'MULTIPLY',op(nt,'SINE',op(nt,'MULTIPLY',z,81)),.19))
        phase=op(nt,'ADD',op(nt,'MULTIPLY',op(nt,'MULTIPLY',across,2*math.pi/.0019),frequency),bend)
        flowing=scaled_noise(nt,coord,(190,50,90),2,.55)
        phase=op(nt,'ADD',phase,op(nt,'MULTIPLY',flowing,32))
        pattern=op(nt,'MULTIPLY',op(nt,'ADD',op(nt,'SINE',phase),1),.5)
    elif kind=='HeavyBack':pattern=forging
    body=mix(nt,pattern,(a,a*1.025,a*1.045,1),(b,b*1.025,b*1.045,1))
    if kind=='Swift':
        # Gentle tone transition follows the already modeled fuller; no painted black groove.
        q=attr.outputs['Alpha']
        channel=op(nt,'POWER',op(nt,'DIVIDE',op(nt,'SUBTRACT',q,.24),.095),2)
        channel=op(nt,'EXPONENT',op(nt,'MULTIPLY',channel,-1))
        channel=op(nt,'MULTIPLY',channel,.12)
        body=mix(nt,channel,body,(.26,.268,.276,1))
    steel=mix(nt,edge,body,(.47,.48,.49,1))
    old_base=tex(nt,original/'T_Kukri_BaseColor.png',True)
    base=mix(nt,root,old_base.outputs['Color'],steel)
    old_orm=tex(nt,original/'T_Kukri_ORM.png')
    old_split=node(nt,'ShaderNodeSeparateColor');nt.links.new(old_orm.outputs[0],old_split.inputs[0])
    rough_base={'Swift':.255,'HeavyBack':.335,'FoldedBalanced':.265}[kind]
    rough_face=op(nt,'ADD',rough_base,op(nt,'MULTIPLY',grain,.045))
    if kind=='FoldedBalanced':rough_face=op(nt,'ADD',rough_face,op(nt,'MULTIPLY',pattern,.025))
    elif kind=='HeavyBack':rough_face=op(nt,'ADD',rough_face,op(nt,'MULTIPLY',forging,.035))
    rough_edge=op(nt,'ADD',.185,op(nt,'MULTIPLY',grain,.025))
    rough=mix(nt,root,old_split.outputs[1],mix(nt,edge,rough_face,rough_edge))
    metal=mix(nt,root,old_split.outputs[2],(1,1,1,1))
    ao=mix(nt,root,old_split.outputs[0],(1,1,1,1))
    packed=node(nt,'ShaderNodeCombineColor')
    for socket,value in zip(packed.inputs,(ao,rough,metal)):put(nt,socket,value)
    # Micron-scale surface relief; avoid the broad noisy height that looked like damage.
    height=op(nt,'MULTIPLY',grain,.000004)
    if kind=='HeavyBack':height=op(nt,'ADD',height,op(nt,'MULTIPLY',forging,.000010))
    if kind=='FoldedBalanced':height=op(nt,'ADD',height,op(nt,'MULTIPLY',pattern,.000002))
    height=op(nt,'MULTIPLY',height,root)
    height=op(nt,'MULTIPLY',height,op(nt,'SUBTRACT',1,op(nt,'MULTIPLY',edge,.65)))
    bump=node(nt,'ShaderNodeBump');bump.inputs['Distance'].default_value=1;bump.inputs['Strength'].default_value=.45
    nt.links.new(height,bump.inputs['Height'])
    for socket,value in [('Base Color',base),('Roughness',rough),('Metallic',metal),('Normal',bump.outputs[0])]:put(nt,bs.inputs[socket],value)
    return mat,{'BaseColor':base,'ORM':packed.outputs[0]},bs,out

receipt={'source':str(OLD/'Kukri_Blade_Variants_Editable.blend'),'vertex_positions_changed':False,'corner_normals_refined':True,
         'uv0_changed':False,'stats_authored':False,'runtime_tested':False,'variants':[]}
for entry in data['variants']:
    obj=bpy.data.objects[entry['object']]
    for other in scene.objects:other.hide_render=other!=obj;other.hide_set(other!=obj)
    refine_normals(obj)
    width=fields(obj,entry['kind']);m=material(entry['kind'])
    obj.data.materials.clear();obj.data.materials.append(m[0])
    for poly in obj.data.polygons:poly.material_index=0
    maps=bake(obj,[m],'T_Kukri_'+entry['kind'],P/'Textures',2048)
    # Use the established slot identity in FBX, including existing rune overrides.
    runtime_name='M_Kukri_'+entry['kind']
    existing=bpy.data.materials.get(runtime_name)
    if existing and existing!=obj.data.materials[0]:existing.name=runtime_name+'_LegacySource'
    obj.data.materials[0].name=runtime_name
    fbx=P/'Export'/(entry['object']+'.fbx');export(obj,fbx)
    receipt['variants'].append({**entry,'textures':maps,'fbx':str(fbx),'edge_finish_width_m':width,
        'icon_input':str(P/'IconInputs'/(entry['icon_key']+'.png')),
        'icon':str(P/'Icons'/(entry['icon_key']+'.png'))})
    print('KUKRI_SURFACE_V2_BAKED '+entry['id'],flush=True)
    (P/'surfaces.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Kukri_Blade_SurfaceV2_Editable.blend'))
print('KUKRI_SURFACE_V2_AUTHOR_COMPLETE',flush=True)
