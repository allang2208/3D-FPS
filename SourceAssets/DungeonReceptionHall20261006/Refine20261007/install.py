"""Save reception-scoped material/mesh variants and patch the existing subject. No tests."""
import unreal as u
from pathlib import Path
import json,hashlib,shutil,re,traceback
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent;PROJECT=PARENT.parents[1]
BASE='/Game/Dungeons/ReceptionHall20261006/Refine20261007';MAP='/Game/GameMaps/Design/L_ReceptionHall_Subject';OWNER='Reception.Refine20261007'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
geometry=json.loads((ROOT/'geometry.json').read_text('utf8'));electronics=json.loads((ROOT/'electronics.json').read_text('utf8'))
report=dict(stage='preparing',saved_assets=[],map=MAP,replacements={},source_material_usage=[],tests_run=False,rendered=False,game_run=False)
def record(): (ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def asset(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing required asset '+p)
    return a
def save(a):
    E.set_metadata_tag(a,'Reception.Owner',OWNER)
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    report['saved_assets'].append(a.get_path_name());record();return a
def owned(p):
    if not E.does_asset_exist(p):return None
    a=asset(p)
    if E.get_metadata_tag(a,'Reception.Owner')!=OWNER:raise RuntimeError('Preserve unowned target '+p)
    return a
def guard():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE: preserve running editor')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('DIRTY_MAP: preserve unsaved map')
def imported(path,source,options=None):
    a=owned(path)
    if a:return a
    t=u.AssetImportTask();t.filename=str(source);t.destination_path,t.destination_name=path.rsplit('/',1);t.automated=True;t.save=False;t.replace_existing=False
    if options:t.options=options;t.factory=u.FbxFactory()
    A.import_asset_tasks([t]);a=asset(path);E.set_metadata_tag(a,'Reception.Owner',OWNER);return a
def material(key,col=(.05,.06,.06),rough=.6,metal=0,texture=None,normal=None,roughtex=None,emission=0):
    path=BASE+'/Materials/M_RH2_'+key;m=owned(path)
    if m:return m
    m=A.create_asset(path.rsplit('/',1)[1],BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
    slab=L.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels);slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    def scalar(v):
        n=L.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',v);return n
    def rgb(v):
        n=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*v,1));return n
    def sample(tex,kind):
        n=L.create_material_expression(m,u.MaterialExpressionTextureSample);n.set_editor_property('texture',asset(tex));n.set_editor_property('sampler_type',kind);return n
    def connect(n,out,prop,pin):L.connect_material_property(n,out,prop);L.connect_material_expressions(n,out,slab,pin)
    b=sample(texture,u.MaterialSamplerType.SAMPLERTYPE_COLOR) if texture else rgb(col);out='RGB' if texture else ''
    connect(b,out,u.MaterialProperty.MP_BASE_COLOR,'BaseColor')
    if roughtex:connect(sample(roughtex,u.MaterialSamplerType.SAMPLERTYPE_MASKS),'R',u.MaterialProperty.MP_ROUGHNESS,'Roughness')
    else:connect(scalar(rough),'',u.MaterialProperty.MP_ROUGHNESS,'Roughness')
    connect(scalar(metal),'',u.MaterialProperty.MP_METALLIC,'Metallic');connect(scalar(.28),'',u.MaterialProperty.MP_SPECULAR,'Specular')
    if normal:connect(sample(normal,u.MaterialSamplerType.SAMPLERTYPE_NORMAL),'RGB',u.MaterialProperty.MP_NORMAL,'Normal')
    elif key in ('ABS','Office_Plastic','Office_Rubber','Office_Keycaps'):
        uv=L.create_material_expression(m,u.MaterialExpressionTextureCoordinate);grain=L.create_material_expression(m,u.MaterialExpressionCustom)
        inp=u.CustomInput();inp.set_editor_property('input_name','UV');grain.set_editor_property('inputs',[inp]);grain.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
        grain.set_editor_property('code','float f=1-saturate(length(fwidth(UV))*900);float2 g=sin(UV*1900+sin(UV.yx*270));return normalize(float3(g*.024*f,1));')
        L.connect_material_expressions(uv,'',grain,'UV');connect(grain,'',u.MaterialProperty.MP_NORMAL,'Normal')
    if emission:
        mul=L.create_material_expression(m,u.MaterialExpressionMultiply);mul.set_editor_property('const_b',emission);L.connect_material_expressions(b,out,mul,'A');connect(mul,'',u.MaterialProperty.MP_EMISSIVE_COLOR,'EmissiveColor')
    L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material build failed '+key+' '+str(errors))
    L.layout_material_expressions(m);return save(m)
def materials():
    for source in (ROOT/'Authored/Textures').glob('*.png'):
        path=BASE+'/Textures/'+source.stem;t=owned(path)
        if t:continue
        t=imported(path,source);normal='Normal' in source.stem;mask='Roughness' in source.stem
        t.set_editor_property('srgb',not(normal or mask));t.set_editor_property('never_stream',False)
        t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS if mask else u.TextureCompressionSettings.TC_BC7)
        t.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD)
        if normal:t.set_editor_property('flip_green_channel',False)
        save(t)
    tex=lambda s:BASE+'/Textures/T_RH2_'+s
    for key in ('Fabric','Wood'):
        material(key,texture=tex(key+'_BaseColor'),normal=tex(key+'_NormalDX'),roughtex=tex(key+'_Roughness'))
    for key in ('Seam','Paper','ABS','Blue','Leather'):
        r=geometry['roles'][key];material(key,r['basecolor_linear'],r['roughness'],r['metallic'])
    material('Boards',texture=tex('Boards'),rough=.86)
    for key,col,rough,metal in [('Plastic',(.038,.050,.052),.48,0),('Rubber',(.011,.015,.015),.85,0),('Steel',(.28,.31,.32),.38,.86),('Paint',(.044,.078,.066),.57,.15),('Keycaps',(.018,.024,.025),.6,0),('Display',(.024,.09,.07),.30,0),('Lamp',(.15,.40,.26),.4,0),('Copper',(.48,.19,.065),.36,.85)]:
        material('Office_'+key,col,rough,metal,emission=.3 if key in ('Display','Lamp') else 0)
    for key in ('Labels','Screen'):material('Office_'+key,texture=tex('OfficePrint'),rough=.31 if key=='Screen' else .86,emission=.28 if key=='Screen' else 0)
    material('Office_Legends',texture='/Game/Dungeons/StationWorkshop20261003/RefineV2/Textures/T_Office_KeyLegends',rough=.6)
def import_mesh(item):
    m=owned(item['mesh'])
    if m:return m
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.one_convex_hull_per_ucx=True
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    m=imported(item['mesh'],item['fbx'],opt)
    for i,s in enumerate(m.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(s.material_slot_name));m.set_material(i,asset(item['materials'][key]))
    build=SM.get_lod_build_settings(m,0);build.set_editor_property('use_full_precision_u_vs',True);build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True);SM.set_lod_build_settings(m,0,build)
    m.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_DEFAULT)
    ns=m.get_editor_property('nanite_settings').copy();ns.enabled=item['nanite'];ns.explicit_tangents=True;m.set_editor_property('nanite_settings',ns)
    if ns.enabled and not u.PlazaInstanceTools.build_nanite_data(m):raise RuntimeError('Nanite build failed '+item['mesh'])
    E.set_metadata_tag(m,'Reception.SourceSHA256',item['sha256']);return save(m)
def clone_furniture(old):
    target=BASE+'/Meshes/'+old.rsplit('/',1)[1];m=owned(target)
    if m:return target
    original=asset(old);m=E.duplicate_asset(old,target)
    if not m:raise RuntimeError('Unable to create scoped mesh '+old)
    for i,s in enumerate(original.get_editor_property('static_materials')):
        name=re.sub(r'[._][0-9]{3}$','',str(s.material_slot_name));key=name.removeprefix('RS_')
        mapping={'Wood':'Wood','PaintedSteel':'Office_Paint','Paint':'Office_Paint','BareSteel':'Office_Steel','Steel':'Office_Steel','Rubber':'Office_Rubber','Plastic':'Office_Plastic','Labels':'Office_Labels','Fabric':'Blue','SofaFabric':'Fabric'}
        if key in mapping:m.set_material(i,asset(BASE+'/Materials/M_RH2_'+mapping[key]))
        else:raise RuntimeError('Unmapped reused furniture slot '+old+' '+name)
        mat=s.material_interface;row=dict(mesh=old,slot=name,material=mat.get_path_name() if mat else None)
        if isinstance(mat,u.Material):row.update(nanite=mat.get_editor_property('used_with_nanite'),instanced=mat.get_editor_property('used_with_instanced_static_meshes'))
        report['source_material_usage'].append(row)
    save(m);return target
def vec(p):return u.Vector(p[0]*100,-p[1]*100,p[2]*100)
def patch_map(items,replacements):
    guard();disk=PROJECT/'Content/GameMaps/Design/L_ReceptionHall_Subject.umap';snap=ROOT/'Snapshots/L_ReceptionHall_Subject.before-refine.umap'
    if not snap.exists():shutil.copy2(disk,snap)
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    if not world:raise RuntimeError('Unable to load subject')
    actors=AA.get_all_level_actors();labels={a.get_actor_label():a for a in actors};changed=[]
    for a in actors:
        if not a.get_actor_label().startswith('Reception_'):continue
        for c in a.get_components_by_class(u.StaticMeshComponent):
            old=c.static_mesh
            if not old:continue
            oldpath=old.get_path_name().split('.')[0]
            if oldpath not in replacements:continue
            a.modify();c.modify();c.set_static_mesh(asset(replacements[oldpath]));c.set_editor_property('override_materials',[]);changed.append(a.get_actor_label())
    for item in items:
        if item['kind'] in ('Signs','Hardware','ReceptionCounter','Sofa','DispatchElectronics'):continue
        label='Reception_Refine_'+item['kind']
        if label in labels:continue
        a=AA.spawn_actor_from_class(u.StaticMeshActor,vec([0,0,0]),u.Rotator());a.set_actor_label(label);a.set_folder_path('Reception/Refine20261007');a.set_editor_property('tags',[u.Name('Reception.Subject')])
        c=a.static_mesh_component;c.set_mobility(u.ComponentMobility.STATIC);c.set_static_mesh(asset(item['mesh']));c.set_collision_profile_name('BlockAll' if item['collision'] else 'NoCollision');c.set_editor_property('generate_overlap_events',False);c.set_cast_shadow(item['cast_shadow']);changed.append(label)
    E.set_metadata_tag(world,OWNER,'saved')
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Map save failed')
    report.update(stage='map_saved',changed_actors=changed,replacements=replacements);record()
def source_sync(items,replacements):
    cfg=json.loads((PARENT/'Config/layout.json').read_text('utf8'));man=json.loads((PARENT/'manifest.json').read_text('utf8'))
    for p in cfg['parts']:p['mesh']=replacements.get(p['mesh'],p['mesh'])
    by_old={old:new for old,new in replacements.items()};by_new={m['mesh']:m for m in items}
    for i,m in enumerate(man['meshes']):
        if m['mesh'] in by_old:man['meshes'][i]=by_new[by_old[m['mesh']]]
    present={m['mesh'] for m in man['meshes']}
    for m in items:
        if m['kind'] in ('Sofa','DispatchElectronics'):continue
        if m['mesh'] not in present:man['meshes'].append(m)
    cfg['revision']='20261007-refine2';cfg['active_refinement']=str(ROOT);man['active_refinement']=str(ROOT)
    (PARENT/'Config/layout.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8');(PARENT/'manifest.json').write_text(json.dumps(man,ensure_ascii=False,indent=2),encoding='utf8')
    report['source_references_saved']=True;record()
try:
    guard();materials()
    items=geometry['meshes']+[m for m in electronics['meshes'] if m['kind']=='DispatchElectronics']
    for item in items:import_mesh(item)
    oldbase='/Game/Dungeons/ReceptionHall20261006/Meshes/SM_Reception_'
    replacements={oldbase+k:BASE+'/Meshes/SM_RH2_'+k for k in ('Signs','Hardware','ReceptionCounter')}
    replacements['/Game/Dungeons/StaffLiving20261002/Meshes/SM_Staff_Sofa']=BASE+'/Meshes/SM_RH2_Sofa'
    replacements['/Game/Dungeons/StationWorkshop20261003/RefineV2/Meshes/SM_SW_DispatchElectronics']=BASE+'/Meshes/SM_SW_DispatchElectronics'
    cfg=json.loads((ROOT/'Snapshots/layout.json').read_text('utf8'))
    for p in cfg['parts']:
        old=p['mesh'];name=old.rsplit('/',1)[-1]
        if name in ('SM_Staff_Chair','SM_Staff_CoffeeTable','SM_Staff_ChangingBench','SM_SW_DispatchDesk','SM_SW_DispatchPaper') and old not in replacements:replacements[old]=clone_furniture(old)
    patch_map(items,replacements);source_sync(items,replacements)
    print('RECEPTION_REFINEMENT_MAP_SAVED',len(report['changed_actors']),flush=True)
except Exception:
    report['error']=traceback.format_exc();record();raise
