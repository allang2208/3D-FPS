"""Kukri surface refinement and eight-guide hanging mesh production."""
import bpy,json,math,sys,ast,bmesh
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent
SRC=P.parent/'KukriComponentVariants20261026'
sys.path.insert(0,str(SRC))
from asset_tools import *
BASE=P.parent/'Kukri20261020/Textures'
NEW='/Game/Weapons/Kukri20261020/Refinement20261027'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except Exception:pass
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1

def append(path,name):
    with bpy.data.libraries.load(str(path),link=False) as (a,b):b.objects=[name]
    obj=b.objects[0]
    if not obj:raise RuntimeError('Missing author object '+name)
    scene.collection.objects.link(obj);obj.matrix_world=Matrix.Identity(4)
    return obj

def functions(path,names,replacements=(),extra=None):
    text=path.read_text(encoding='utf-8')
    for a,b in replacements:text=text.replace(a,b)
    module=ast.parse(text)
    defs=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in names]
    namespace=dict(globals());namespace.update(extra or {})
    exec(compile(ast.Module(body=defs,type_ignores=[]),str(path),'exec'),namespace)
    return namespace

blade=functions(P.parent/'KukriBladeSurfaceV220261026/author_surface.py',{'scaled_noise','material'},[
    ("(.30,.33),'HeavyBack':(.215,.245),'FoldedBalanced':(.255,.335)","(.265,.31),'HeavyBack':(.195,.235),'FoldedBalanced':(.235,.32)"),
    ("(3600,3000,90)","(4200,3000,110)"),
    ("grain,.000004","grain,.000007"),("forging,.000010","forging,.000014"),
    ("pattern,.000002","pattern,.000004"),
    ("default_value=.45","default_value=.70")],{'original':BASE})
grip=functions(P.parent/'KukriGripSurfaceV220261027/author_surfaces.py',{'scale_vector','noise','clamp','ramp','author_material'},[
    (".000025",".000018"),(".000035",".000025"),
    (".43, op(nt",".41, op(nt"),(".35, op(nt",".34, op(nt")])

def detail(nt,coord,scale):
    v=node(nt,'ShaderNodeVectorMath',operation='MULTIPLY');put(nt,v.inputs[0],coord);v.inputs[1].default_value=scale
    n=node(nt,'ShaderNodeTexNoise');n.inputs['Scale'].default_value=1;n.inputs['Detail'].default_value=2
    nt.links.new(v.outputs[0],n.inputs['Vector']);return n.outputs['Fac']

def refine_hanging_geometry(obj):
    # Round the original angular webbing while keeping the pierced root fixed.
    # Metal rings and the tag stay separate rigid islands with their real bevels.
    vertices=obj.data.vertices;adj=[set() for _ in vertices]
    for edge in obj.data.edges:
        a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
    seed=max(range(len(vertices)),key=lambda i:vertices[i].co.z)
    cord={seed};stack=[seed]
    while stack:
        for nxt in adj[stack.pop()]:
            if nxt not in cord:cord.add(nxt);stack.append(nxt)
    tube=obj.copy();tube.data=obj.data.copy();scene.collection.objects.link(tube)
    for target,remove_cord in [(tube,False),(obj,True)]:
        bm=bmesh.new();bm.from_mesh(target.data);bm.verts.ensure_lookup_table()
        remove=[v for v in bm.verts if (v.index in cord)==remove_cord]
        bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(target.data);bm.free()
    crease=tube.data.attributes.get('crease_edge') or tube.data.attributes.new(name='crease_edge',type='FLOAT',domain='EDGE')
    for edge in tube.data.edges:
        if all(tube.data.vertices[i].co.z>=-.018 for i in edge.vertices):crease.data[edge.index].value=1
    activate(tube)
    tube.data.normals_split_custom_set([(0,0,0)]*len(tube.data.loops))
    sub=tube.modifiers.new('SuppleWebbing','SUBSURF');sub.levels=2;sub.render_levels=2
    bpy.ops.object.modifier_apply(modifier=sub.name)
    for poly in tube.data.polygons:poly.use_smooth=True
    original_name=obj.name
    if len(obj.data.vertices):
        bpy.ops.object.select_all(action='DESELECT');tube.select_set(True);obj.hide_set(False);obj.select_set(True)
        bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
    else:
        bpy.data.objects.remove(obj,do_unlink=True);obj=tube;obj.name=original_name
    return obj

def part_material(entry):
    kind=entry['kind'];m,nt,bs,out=make_mat('Author_Refined_'+kind)
    uv='SourceUV' if kind=='LanyardFactory' else None
    oldbase=tex(nt,entry['textures']['BaseColor'],True,uv)
    oldorm=tex(nt,entry['textures']['ORM'],False,uv)
    old=node(nt,'ShaderNodeSeparateColor');nt.links.new(oldorm.outputs[0],old.inputs[0])
    tc=node(nt,'ShaderNodeTexCoord');coord=tc.outputs['Object']
    xyz=node(nt,'ShaderNodeSeparateXYZ');nt.links.new(coord,xyz.inputs[0]);x,y,z=xyz.outputs
    grain=detail(nt,coord,(5000,3500,160));micro=detail(nt,coord,(4500,4500,4500))
    if kind.startswith('Pommel'):
        basecolor={'PommelSteel':(.29,.315,.33,1),'PommelFaceted':(.36,.20,.085,1),'PommelRinged':(.12,.14,.15,1)}[kind]
        color=mix(nt,grain,basecolor,tuple(v*1.12 for v in basecolor[:3])+(1,))
        rough=op(nt,'ADD',.27 if kind!='PommelFaceted' else .32,op(nt,'MULTIPLY',grain,.075))
        metallic=.96;relief=op(nt,'MULTIPLY',grain,.000007)
        if kind=='PommelFaceted':relief=op(nt,'ADD',relief,op(nt,'MULTIPLY',micro,.000007))
        if kind=='PommelRinged':
            bands=op(nt,'POWER',op(nt,'ABSOLUTE',op(nt,'SINE',op(nt,'MULTIPLY',z,1050))),12)
            attr=node(nt,'ShaderNodeVertexColor',layer_name='SurfaceMask');sep=node(nt,'ShaderNodeSeparateColor');nt.links.new(attr.outputs[0],sep.inputs[0])
            band=op(nt,'MULTIPLY',sep.outputs[1],bands)
            color=mix(nt,band,color,(.39,.405,.42,1))
            rough=op(nt,'SUBTRACT',rough,op(nt,'MULTIPLY',band,.055))
        ao=old.outputs[0]
    else:
        metal=op(nt,'GREATER_THAN',old.outputs[2],.55)
        phase=op(nt,'ADD',op(nt,'MULTIPLY',z,8400),op(nt,'MULTIPLY',x,2800))
        a=op(nt,'ABSOLUTE',op(nt,'SINE',phase))
        b=op(nt,'ABSOLUTE',op(nt,'SINE',op(nt,'SUBTRACT',op(nt,'MULTIPLY',z,8400),op(nt,'MULTIPLY',x,2800))))
        weave=op(nt,'POWER',op(nt,'MULTIPLY',a,b),.45)
        dark=(.018,.023,.010,1) if kind=='LanyardBraid' else (.027,.012,.005,1)
        light=(.06,.075,.033,1) if kind=='LanyardBraid' else (.085,.035,.012,1)
        cord=mix(nt,op(nt,'ADD',op(nt,'MULTIPLY',weave,.55),op(nt,'MULTIPLY',micro,.45)),dark,light)
        softheight=op(nt,'ADD',op(nt,'MULTIPLY',weave,.000055),op(nt,'MULTIPLY',micro,.000014))
        soft_rough=op(nt,'ADD',.49,op(nt,'MULTIPLY',micro,.10))
        if kind=='LanyardTassel':
            leather=op(nt,'LESS_THAN',z,-.052)
            hide=detail(nt,coord,(2800,2800,2800))
            cord=mix(nt,leather,cord,mix(nt,hide,(.035,.011,.003,1),(.14,.06,.022,1)))
            softheight=op(nt,'ADD',op(nt,'MULTIPLY',softheight,op(nt,'SUBTRACT',1,leather)),op(nt,'MULTIPLY',op(nt,'MULTIPLY',hide,.00003),leather))
        color=mix(nt,metal,cord,oldbase.outputs[0])
        rough=op(nt,'ADD',op(nt,'MULTIPLY',soft_rough,op(nt,'SUBTRACT',1,metal)),op(nt,'MULTIPLY',op(nt,'ADD',.25,op(nt,'MULTIPLY',grain,.065)),metal))
        metallic=op(nt,'MULTIPLY',metal,.96)
        relief=op(nt,'ADD',op(nt,'MULTIPLY',softheight,op(nt,'SUBTRACT',1,metal)),op(nt,'MULTIPLY',op(nt,'MULTIPLY',grain,.000006),metal))
        ao=old.outputs[0]
    packed=node(nt,'ShaderNodeCombineColor')
    for socket,value in zip(packed.inputs,(ao,rough,metallic)):put(nt,socket,value)
    bump=node(nt,'ShaderNodeBump');bump.inputs['Distance'].default_value=1;bump.inputs['Strength'].default_value=.8;put(nt,bump.inputs['Height'],relief)
    for label,value in [('Base Color',color),('Metallic',metallic),('Roughness',rough),('Normal',bump.outputs[0])]:put(nt,bs.inputs[label],value)
    return m,{'BaseColor':color,'ORM':packed.outputs[0]},bs,out

def dynamics(obj,kind):
    verts=[v.co for v in obj.data.vertices];low=min(v.z for v in verts)
    if kind=='LanyardTag':zs=[-.018,-.023,-.028,-.034,-.039,-.042,-.0659,-.067]
    elif kind=='LanyardTassel':zs=[-.018,-.023,-.028,-.034,-.039,-.048,-.061,low]
    else:zs=[-.018,-.024,-.030,-.037,-.045,-.052,-.058,low]
    guides=[]
    for z in zs:
        nearest=sorted(verts,key=lambda v:abs(v.z-z))[:max(12,min(70,len(verts)//25))]
        guides.append(Vector((sum(v.x for v in nearest)/len(nearest),sum(v.y for v in nearest)/len(nearest),z)))
    # UV0 remains the PBR atlas; UV2 carries chain segment/blend just like the
    # ZhenYue guide shader (FBX flips V, restored by the material).
    while len(obj.data.uv_layers)<3:obj.data.uv_layers.new(name='SourceUV' if len(obj.data.uv_layers)==1 else 'TasselSkin')
    skin=obj.data.uv_layers[2];skin.name='TasselSkin'
    adjacency=[set() for _ in verts]
    for edge in obj.data.edges:
        a,b=edge.vertices;adjacency[a].add(b);adjacency[b].add(a)
    groups={};seen=set()
    for vi in range(len(verts)):
        if vi in seen:continue
        stack=[vi];group=[];seen.add(vi)
        while stack:
            a=stack.pop();group.append(a)
            for b in adjacency[a]:
                if b not in seen:seen.add(b);stack.append(b)
        center=sum((verts[i] for i in group),Vector())/len(group)
        rigid=None
        if kind=='LanyardTag' and center.z<-.043:rigid=5
        elif kind=='LanyardTag' and center.z<-.035:rigid=3
        elif kind=='LanyardTassel' and -.055<center.z<-.035:rigid=3 if center.z>-.043 else 4
        for i in group:groups[i]=rigid
    for loop in obj.data.loops:
        z=verts[loop.vertex_index].z;index=0
        while index<6 and z<zs[index+1]:index+=1
        blend=max(0,min(1,(zs[index]-z)/max(1e-7,zs[index]-zs[index+1]))) if index<6 else 0
        if groups[loop.vertex_index] is not None:index=groups[loop.vertex_index];blend=0
        skin.data[loop.index].uv=(index,blend)
    return {'guides_cm':[[float(v*100) for v in p] for p in guides],
        'inverse_masses':([0,1,1,.7,.45,.12,.12,.12] if kind=='LanyardTag' else [0,1,.9,.65,.45,.8,1,1]),
        'collision_capsules_cm':[[-2.4,0,-.5,2.1,0,-.5,.72],[-.3,0,2.4,-.3,0,13,1.55]],
        'damping_per_second':4.6 if kind=='LanyardTag' else 5.0,'heavy_damping_per_second':5.5,
        'particle_radius_cm':.06,'skin_uv_channel':2,'fixed_above_z_cm':-1.8}

entries=[]
for e in json.loads((P.parent/'KukriBladeSurfaceV220261026/surfaces.json').read_text(encoding='utf-8'))['variants']:
    e['slot']='blade_1'
    entries.append((e,P.parent/'KukriBladeSurfaceV220261026/Kukri_Blade_SurfaceV2_Editable.blend'))
for e in json.loads((SRC/'components.json').read_text(encoding='utf-8'))['variants']:
    source=P.parent/'KukriGripSurfaceV220261027/Kukri_Grip_SurfaceV2_Editable.blend' if e['slot']=='grip' else SRC/'Kukri_Components_Editable.blend'
    entries.append((e,source))
catalog=json.loads((P.parents[1]/'Content/ColdSteelData/kukri-modules.json').read_text(encoding='utf-8'))
factory={'id':'factory','kind':'LanyardFactory','slot':'lanyard','name':'原装挂绳','object':'SM_Kukri_Lanyard_Factory',
    'mesh':catalog['slots']['lanyard']['factory']['mesh'],'icon_key':'ue_kukri_lanyard_false',
    'textures':{s:str(BASE/('T_Kukri_'+s+'.png')) for s in ('BaseColor','ORM','Normal')}}
entries.append((factory,P.parent/'KukriModules20261026/Kukri_Modules_Editable.blend'))
manifest={'revision':'KukriRefinement20261027','numeric_changes':False,'runtime_tested':False,'variants':[]}
for original,source in entries:
    e=dict(original);kind=e['kind'];obj=append(source,e['object'])
    if e['slot']=='lanyard':obj=refine_hanging_geometry(obj)
    for other in scene.objects:other.hide_render=other!=obj;other.hide_set(other!=obj)
    if kind=='LanyardFactory':
        if len(obj.data.uv_layers)==1:
            layer=obj.data.uv_layers.new(name='SourceUV')
            for a,b in zip(layer.data,obj.data.uv_layers[0].data):a.uv=b.uv
        unwrap(obj)
    prefix='T_Kukri_'+kind
    for image in list(bpy.data.images):
        if image.name.startswith(prefix+'_'):image.name='Earlier_'+image.name
    old=bpy.data.materials.get('M_Kukri_'+kind)
    if old:old.name='Earlier_'+old.name
    material=blade['material'](kind) if e['slot']=='blade_1' else grip['author_material'](kind) if e['slot']=='grip' else part_material(e)
    obj.data.materials.clear();obj.data.materials.append(material[0])
    maps=bake(obj,[material],prefix,P/'Textures',2048)
    e['textures']=maps
    e['texture_root']=(e['material'].split('/Materials/')[0]+'/Textures') if e['slot'] not in ('lanyard',) else NEW+'/Textures'
    if e['slot']=='lanyard':
        e['dynamics']=dynamics(obj,kind)
        e['author_bounds_cm']=[[min(v.co[i] for v in obj.data.vertices)*100 for i in range(3)],[max(v.co[i] for v in obj.data.vertices)*100 for i in range(3)]]
        obj.name=obj.data.name='SM_Kukri_'+kind+'_PhysicsV1'
        obj.data.materials[0].name='M_Kukri_'+kind+'_PhysicsV1'
        e.update(object=obj.name,mesh=NEW+'/Meshes/'+obj.name+'.'+obj.name,
            material=NEW+'/Materials/'+obj.data.materials[0].name+'.'+obj.data.materials[0].name,
            fbx=str(P/'Export'/(obj.name+'.fbx')))
        activate(obj)
        bpy.ops.export_scene.fbx(filepath=e['fbx'],use_selection=True,object_types={'MESH'},
            axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',
            use_tspace=True,path_mode='STRIP',apply_unit_scale=True,add_leaf_bones=False)
    e.update(source_blend=str(P/'Kukri_Refinement_Editable.blend'),icon_input=str(P/'IconInputs'/(e['icon_key']+'.png')),
             icon=str(P/'Icons'/(e['icon_key']+'.png')))
    manifest['variants'].append(e)
    (P/'surfaces.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    obj.hide_set(True);obj.hide_render=True
    print('KUKRI_REFINEMENT_AUTHORED '+kind,flush=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Kukri_Refinement_Editable.blend'))
print('KUKRI_REFINEMENT_AUTHORING_COMPLETE',flush=True)
