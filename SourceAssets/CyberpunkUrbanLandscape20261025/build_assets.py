"""Scoped production imports and static spatial instance assemblies; no map changes."""
from pathlib import Path
import unreal as u,json,runpy,hashlib,collections,math
R=Path(__file__).resolve().parent;P=R.parents[1];BASE='/Game/Props/CyberpunkUrbanLandscape20261025'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
H=runpy.run_path(str(P/'SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV10/build_assets.py'));node=H['node'];wire=H['wire'];custom=H['custom']
D=json.loads((R/'layout.json').read_text(encoding='utf8'));G=json.loads((R/'geometry.json').read_text(encoding='utf8'));I=json.loads((R/'inputs.json').read_text(encoding='utf8'))
report=json.loads((R/'assets_saved.json').read_text(encoding='utf8')) if (R/'assets_saved.json').exists() else dict(stage='authoring',materials={},textures={},meshes={},foliage={},blueprints={},derived_materials={},tests_run=False)

def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing production asset '+str(path))
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def compile_save(m):
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Production shader compilation '+str(errors))
    save(m)
def newmaterial(key):
    name='M_UL_'+key;path=BASE+'/Materials/'+name;m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m)
    m.set_editor_property('used_with_instanced_static_meshes',True);m.set_editor_property('used_with_nanite',True);return m
def duplicate(src,prefix):
    name=prefix+'_'+src.get_name()+'_'+hashlib.sha1(src.get_path_name().encode()).hexdigest()[:8];path=BASE+'/Materials/'+name
    return load(path) if E.does_asset_exist(path) else A.duplicate_asset(name,BASE+'/Materials',src)
def texture(name):
    kind='normal' if name.endswith('_N') else ('mask' if name.endswith('_ORM') else 'color')
    t=u.AssetImportTask();t.filename=str(R/'Textures'/(name+'.png'));t.destination_path=BASE+'/Textures';t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.TextureFactory();A.import_asset_tasks([t]);a=load(BASE+'/Textures/'+name)
    for k,v in dict(srgb=kind=='color',compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if kind=='normal' else (u.TextureCompressionSettings.TC_MASKS if kind=='mask' else u.TextureCompressionSettings.TC_BC7),max_texture_size=1024,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE).items():a.set_editor_property(k,v)
    save(a);report['textures'][name]=a.get_path_name();return a
def sample(m,t,kind):return node(m,'TextureSample',texture=t,sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind))
def connect_surface(m,bc,normal,rough,metal=None,emission=None):
    slab=node(m,'SubstrateShadingModels');zero=node(m,'Constant',r=0)
    for v,pin,prop in [(bc,'BaseColor','BASE_COLOR'),(normal,'Normal','NORMAL'),(rough,'Roughness','ROUGHNESS'),(metal or zero,'Metallic','METALLIC'),(emission or zero,'EmissiveColor','EMISSIVE_COLOR')]:
        wire(v,slab,pin);L.connect_material_property(v,'',getattr(u.MaterialProperty,'MP_'+prop))
    L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)

def surfaces():
    v18=json.loads((P/'SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV18/assets_saved.json').read_text(encoding='utf8'))['materials']
    for role in ('Paving','Metal','Copper','Rubber','Warm','Teal'):
        report['materials'][role]=v18[role]
    report['materials']['Stone']=v18['Paving']
    for role in ('Lawn','Soil'):
        maps={k:texture('T_UL_'+role+'_'+k) for k in ('BC','N','ORM')};m=newmaterial(role)
        bc=sample(m,maps['BC'],'COLOR');normal=sample(m,maps['N'],'NORMAL');orm=sample(m,maps['ORM'],'MASKS')
        wet=node(m,'CollectionParameter',collection=load('/Game/Weather/Materials/MPC_FPS_Weather'),parameter_name='WeatherWetness')
        rough=custom(m,'return lerp(ORM.g,max(.32,ORM.g*.6),saturate(Wet));',dict(ORM=orm,Wet=wet),1,description='Planting surface weather response')
        connect_surface(m,bc,normal,rough);ao=custom(m,'return ORM.r;',dict(ORM=orm),1);L.connect_material_property(ao,'',u.MaterialProperty.MP_AMBIENT_OCCLUSION);compile_save(m);report['materials'][role]=m.get_path_name();record()
    texture('T_UL_AspenBark_N');record()

def foliage_material(src):
    key=src.get_path_name()
    if key in report['derived_materials']:return load(report['derived_materials'][key])
    dst=duplicate(src,'MI_UL_Static' if isinstance(src,u.MaterialInstanceConstant) else 'M_UL_Static')
    if isinstance(src,u.MaterialInstanceConstant):
        L.set_material_instance_parent(dst,foliage_material(src.get_editor_property('parent')));L.update_material_instance(dst);save(dst)
    else:
        # Static clusters retain original diffuse / normal / opacity and discard wind WPO.
        zero=node(dst,'Constant3Vector',constant=u.LinearColor(0,0,0,1));L.connect_material_property(zero,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        dst.set_editor_property('used_with_instanced_static_meshes',True)
        compile_save(dst)
    report['derived_materials'][key]=dst.get_path_name();record();return dst

def foliage(key):
    row=D['source_meshes'][key]
    if key=='TreeA':
        bark=newmaterial('AspenBark');fol='/Game/SoulCity/Environment/Textures/Foliage/'
        connect_surface(bark,sample(bark,load(fol+'T_Tree_Aspen_Bark_D'),'COLOR'),sample(bark,load(report['textures']['T_UL_AspenBark_N']),'NORMAL'),node(bark,'Constant',r=.85));compile_save(bark)
        leaf=newmaterial('AspenLeaves');leaf.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED);leaf.set_editor_property('two_sided',True);leaf.set_editor_property('opacity_mask_clip_value',.33)
        bc=sample(leaf,load(fol+'T_Foliage_Leaves_D'),'COLOR');normal=sample(leaf,load(fol+'T_Foliage_Leaves_N'),'NORMAL')
        connect_surface(leaf,bc,normal,node(leaf,'Constant',r=.73));L.connect_material_property(bc,'A',u.MaterialProperty.MP_OPACITY_MASK);compile_save(leaf)
        mats=[bark.get_path_name(),leaf.get_path_name()]
    else:mats=[foliage_material(load(p)).get_path_name() for p in row['materials']]
    report['foliage'][key]=dict(mesh=row['path'],materials=mats,source_normal_maps_retained=True,wind=False);record();print('URBAN_FOLIAGE_SAVED',key,flush=True)

def water():
    src=load('/Game/Props/RomanFountain20260917/Materials/M_FountainWaveWaterV3');m=duplicate(src,'M_UL_Pool')
    m.set_editor_property('used_with_instanced_static_meshes',True);m.set_editor_property('used_with_nanite',True);compile_save(m);report['materials']['Water']=m.get_path_name()
    flow=newmaterial('FountainStream');flow.set_editor_property('two_sided',True)
    uv=node(flow,'TextureCoordinate');clock=node(flow,'Time')
    normal=custom(flow,'float p=UV.y*65-T*4; return normalize(float3(.12*sin(p),.09*cos(p*1.7),1));',dict(UV=uv,T=clock),3,description='Continuous fine stream ripples')
    bc=node(flow,'Constant3Vector',constant=u.LinearColor(.18,.30,.32,1));connect_surface(flow,bc,normal,node(flow,'Constant',r=.15));compile_save(flow);report['materials']['Flow']=flow.get_path_name();record()

def meshes(start,end):
    for row in G['meshes'][start:end]:
        t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
        o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;o.import_mesh=True;o.import_materials=False;o.import_textures=False;o.import_animations=False;d=o.static_mesh_import_data
        for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False).items():d.set_editor_property(k,v)
        d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=o;A.import_asset_tasks([t])
        if not t.imported_object_paths:raise RuntimeError('Mesh import did not produce an asset: '+row['fbx'])
        mesh=load(BASE+'/Meshes/'+row['name'])
        roles=report['materials']
        if row['kind']=='trim':
            old=I['actors'][row['actor']]['components'][0];roles={str(k).removeprefix('AP16_').removeprefix('AP18_'):v for k,v in zip(old['slots'],old['materials'])}
        for i,s in enumerate(mesh.static_materials):
            role=str(s.material_slot_name).removeprefix('AP16_').removeprefix('AP18_');mesh.set_material(i,load(roles[role]))
        settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;SM.set_lod_build_settings(mesh,0,settings)
        ns=mesh.get_editor_property('nanite_settings').copy();ns.enabled=not row.get('water',False);ns.explicit_tangents=True;mesh.set_editor_property('nanite_settings',ns)
        save(mesh);report['meshes'][row['key']]=dict(path=mesh.get_path_name(),triangles=row['triangles'],kind=row['kind']);record();print('URBAN_MESH_SAVED',row['key'],flush=True)

def blueprint(name):
    s=u.get_engine_subsystem(u.SubobjectDataSubsystem);f=u.SubobjectDataBlueprintFunctionLibrary;path=BASE+'/Blueprints/'+name;bp=u.load_asset(path)
    if not bp:
        factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.Actor);bp=A.create_asset(name,BASE+'/Blueprints',u.Blueprint,factory)
    handles=s.k2_gather_subobject_data_for_blueprint(bp);byname={str(f.get_variable_name(f.get_data(h))):h for h in handles}
    def obj(h):return f.get_object(f.get_data(h))
    def component(name,cls,parent):
        h=byname.get(name)
        if not h:
            h,reason=s.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=cls,blueprint_context=bp))
            if not f.is_handle_valid(h):raise RuntimeError(str(reason))
            s.rename_subobject(h,u.Text(name));byname[name]=h
        c=obj(h);c.modify();return h,c
    roots=[h for h in handles if f.is_root_component(f.get_data(h))]
    if roots:root=roots[0]
    else:root,c=component('LandscapeRoot',u.SceneComponent,handles[0]);s.make_new_scene_root(handles[0],root,bp)
    obj(root).set_mobility(u.ComponentMobility.STATIC);return bp,root,component

def assembly(zone):
    plants=[p for p in D['plants'] if p['zone']==zone];groups=collections.defaultdict(list)
    for p in plants:groups[(math.floor(p['p'][0]/200),math.floor(p['p'][1]/200),p['mesh'])].append(p)
    origins={z['id']:z['origin'] for z in D['zones']};origin=origins.get(zone,[0,0,-106.25])
    bp,root,component=blueprint('BP_UL_'+zone+'_Plants')
    s=u.get_engine_subsystem(u.SubobjectDataSubsystem);f=u.SubobjectDataBlueprintFunctionLibrary
    for handle in s.k2_gather_subobject_data_for_blueprint(bp):
        old=f.get_object(f.get_data(handle))
        if isinstance(old,u.InstancedStaticMeshComponent):old.modify();old.clear_instances()
    for (cx,cy,key),rows in groups.items():
        h,c=component('F_'+str(cx).replace('-','N')+'_'+str(cy).replace('-','N')+'_'+key,u.HierarchicalInstancedStaticMeshComponent,root);c.set_mobility(u.ComponentMobility.STATIC);src=report['foliage'][key];c.set_static_mesh(load(src['mesh']));c.clear_instances();trs=[]
        for row in rows:
            t=u.Transform();t.translation=u.Vector(*[(row['p'][i]-origin[i])*100 for i in range(3)]);t.rotation=u.Rotator(pitch=0,yaw=row['yaw'],roll=0).quaternion();t.scale3d=u.Vector(row['scale'],row['scale'],row['scale']);trs.append(t)
        c.add_instances(trs,False,False,False)
        for i,path in enumerate(src['materials']):c.set_material(i,load(path))
        c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',key.startswith('Tree'));c.set_editor_property('visible_in_ray_tracing',False);c.set_editor_property('affect_distance_field_lighting',False)
        c.set_editor_property('instancing_random_seed',int(hashlib.sha1((zone+str(cx)+str(cy)+key).encode()).hexdigest()[:7],16)+1)
        # Trees remain in the skyline; low understorey fades beyond its useful range.
        if key.startswith('Tree'):c.set_cull_distances(0,0)
        elif key=='Shrub':c.set_cull_distances(400000,650000)
        else:c.set_cull_distances(180000,260000)
    if not u.BlueprintEditorLibrary.compile_blueprint(bp):raise RuntimeError('Cannot compile planted assembly '+zone)
    cdo=u.get_default_object(bp.generated_class());tick=cdo.get_editor_property('primary_actor_tick');tick.set_editor_property('start_with_tick_enabled',False);cdo.set_editor_property('primary_actor_tick',tick);save(bp)
    report['blueprints'][zone]=dict(path=bp.get_path_name(),origin=origin,plants=len(plants),components=len(groups));record();print('URBAN_ASSEMBLY_SAVED',zone,len(plants),len(groups),flush=True)

def finish():
    if len(report['meshes'])!=len(G['meshes']) or len(report['blueprints'])!=6:raise RuntimeError('Production batches incomplete')
    for p in set(report['derived_materials'].values())|{p for p in report['materials'].values() if p.startswith(BASE)}:save(load(p))
    report.update(stage='assets_saved',counts=D['counts'],new_runtime_lights=0,new_runtime_captures=0,new_tick_actors=0);record();print('URBAN_ALL_ASSETS_SAVED',flush=True)
