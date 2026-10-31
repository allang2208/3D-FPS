"""V3 independent PBR assets and source-hash mesh imports; no shared asset edits."""
import sys,json,hashlib,gc,runpy
from pathlib import Path
import unreal as u
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R))
from design import *
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
helper=runpy.run_path(str(R.parent/'build_assets.py'))
node=helper['node'];wire=helper['wire'];scalar=helper['scalar'];rgb=helper['rgb'];custom=helper['custom']
report=dict(stage='building',revision='V3',materials={},meshes={},textures={},material_details={})
def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing production source '+path)
    return asset
def save(a):
    if not a.get_path_name().startswith(BASE+'/'):raise RuntimeError('Outside V3 boundary')
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def texture(m,path,uv,normal=False):
    t=load(path)
    sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR if t.srgb else u.MaterialSamplerType.SAMPLERTYPE_MASKS if 'MASKS' in str(t.compression_settings) else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
    n=node(m,'TextureSample',texture=t,sampler_type=sampler);wire(uv,n,'UVs');return n
def import_textures():
    for f in sorted((R/'Textures').glob('*.png')):
        sha=hashlib.sha256(f.read_bytes()).hexdigest();folder=BASE+'/Textures/'+sha[:10];path=folder+'/'+f.stem
        t=u.load_asset(path) if E.does_asset_exist(path) else None
        if not t:
            task=u.AssetImportTask();task.filename=str(f);task.destination_path=folder;task.destination_name=f.stem;task.automated=True;task.replace_existing=False;task.save=False
            A.import_asset_tasks([task]);t=load(path);suffix=f.stem.rsplit('_',1)[-1]
            for k,v in dict(srgb=suffix=='BC',compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if suffix=='N' else u.TextureCompressionSettings.TC_MASKS if suffix=='ORM' else u.TextureCompressionSettings.TC_BC7,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,never_stream=False).items():t.set_editor_property(k,v)
            if suffix=='N':t.set_editor_property('flip_green_channel',False)
            save(t)
        report['textures'][f.stem]=dict(path=t.get_path_name(),sha256=sha,size=[t.blueprint_get_size_x(),t.blueprint_get_size_y()]);record()
def materials():
    for role,spec in SURFACES.items():
        name='M_BP3_'+role;path=BASE+'/Materials/'+name
        m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
        L.delete_all_material_expressions(m)
        for key,val in dict(two_sided=False,blend_mode=u.BlendMode.BLEND_OPAQUE,used_with_nanite=True,used_with_instanced_static_meshes=True).items():m.set_editor_property(key,val)
        uv=node(m,'Multiply');wire(node(m,'TextureCoordinate'),uv,'A');wire(node(m,'ScalarParameter',parameter_name='UVScale',default_value=1/spec['period']),uv,'B')
        tint=node(m,'VectorParameter',parameter_name='Tint',default_value=u.LinearColor(*spec['color'],1))
        sources={}
        if 'generated' in spec:
            root='T_BP3_'+spec['generated']+'_'
            for suffix in ('BC','N','ORM'):sources[suffix]=report['textures'][root+suffix]['path']
            color=texture(m,sources['BC'],uv);n=texture(m,sources['N'],uv,True);packed=texture(m,sources['ORM'],uv)
            rough=custom(m,'return P.g;',{'P':packed},1);ao=custom(m,'return P.r;',{'P':packed},1)
        else:
            sources['N']=SUB+spec['normal'];n=texture(m,sources['N'],uv,True)
            rough=scalar(m,sum(spec['limits'])/2);color=tint;ao=scalar(m,1.)
            if spec.get('rough'):
                sources['R']=SUB+spec['rough'];rr=texture(m,sources['R'],uv)
                rough=custom(m,'return lerp(Lo,Hi,saturate(R.r));',{'R':rr,'Lo':scalar(m,spec['limits'][0]),'Hi':scalar(m,spec['limits'][1])},1)
                color=custom(m,'return Tint*lerp(.88,1.10,saturate(R.r));',{'Tint':tint,'R':rr})
            if spec.get('base'):
                sources['BC']=SUB+spec['base'];bc=texture(m,sources['BC'],uv)
                color=custom(m,'return Tint*lerp(.55,1.45,saturate(dot(C,float3(.2126,.7152,.0722))*2.0));',{'Tint':tint,'C':bc})
        n=custom(m,'return normalize(float3(N.xy*S,max(N.z,.12)));',{'N':n,'S':node(m,'ScalarParameter',parameter_name='NormalStrength',default_value=spec['strength'])})
        slab=node(m,'SubstrateShadingModels',shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
        for val,pin,prop in [(color,'BaseColor','BASE_COLOR'),(n,'Normal','NORMAL'),(rough,'Roughness','ROUGHNESS'),(scalar(m,spec['metal']),'Metallic','METALLIC')]:
            wire(val,slab,pin);L.connect_material_property(val,'',getattr(u.MaterialProperty,'MP_'+prop))
        L.connect_material_property(ao,'',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
        if 'emission' in spec:
            e=node(m,'Multiply');wire(rgb(m,spec['emission']),e,'A');wire(node(m,'ScalarParameter',parameter_name='FixtureLevel',default_value=1.),e,'B')
            wire(e,slab,'Emissive Color');L.connect_material_property(e,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
        L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        errors=L.recompile_material(m)
        if errors:raise RuntimeError(str(errors))
        stats=L.get_statistics(m);instructions=stats.get_editor_property('num_pixel_shader_instructions')
        if instructions<=0:raise RuntimeError('Uncompiled material '+role)
        save(m);report['materials'][role]=m.get_path_name();report['material_details'][role]=dict(sources=sources,period_m=spec['period'],normal_strength=spec['strength'],opaque=True,two_sided=False,pixel_instructions=instructions)
        record();print('BP3_MATERIAL_SAVED',role,flush=True)
def meshes():
    for row in json.loads((R/'assembly.json').read_text('utf8'))['meshes']:
        sha=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest();folder=BASE+'/Meshes/'+sha[:10];path=folder+'/'+row['name']
        mesh=u.load_asset(path) if E.does_asset_exist(path) else None
        if not mesh:
            task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=folder;task.destination_name=row['name'];task.automated=True;task.replace_existing=False;task.save=False;task.factory=u.FbxFactory()
            opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
            d=opt.static_mesh_import_data
            for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False,one_convex_hull_per_ucx=True).items():d.set_editor_property(k,v)
            d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;task.options=opt;A.import_asset_tasks([task]);mesh=load(path)
            for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,load(report['materials'][str(slot.material_slot_name)]))
            bs=SM.get_lod_build_settings(mesh,0);bs.use_full_precision_u_vs=True;bs.recompute_normals=False;bs.recompute_tangents=True;bs.use_mikk_t_space=True;SM.set_lod_build_settings(mesh,0,bs)
            body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
            ns=mesh.get_editor_property('nanite_settings').copy();ns.enabled=row['nanite'];ns.explicit_tangents=True;ns.generate_fallback=u.NaniteGenerateFallback.ENABLED;ns.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;ns.fallback_percent_triangles=1.;mesh.set_editor_property('nanite_settings',ns)
            if row['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build '+row['key'])
            save(mesh)
        report['meshes'][row['key']]=dict(path=mesh.get_path_name(),sha256=sha,triangles=row['triangles'],simple_hulls=row['simple_hulls'],nanite=row['nanite']);record()
        print('BP3_MESH_SAVED',row['key'],flush=True);mesh=None;gc.collect();u.SystemLibrary.collect_garbage()
def export_material_sources():
    folder=R/'Review/LibraryTextures';folder.mkdir(parents=True,exist_ok=True);exports={}
    for spec in report['material_details'].values():
        for path in spec['sources'].values():
            if path in exports or path.startswith(BASE+'/'):continue
            t=load(path);file=folder/(t.get_name()+'.png')
            # Let the registry call SupportsObject. Some library normals retain
            # HDR source pixels: forcing PNG asserts inside UE, whereas EXR is valid.
            task=u.AssetExportTask();task.object=t;task.filename=str(file);task.automated=True;task.replace_identical=True;task.prompt=False
            if not u.Exporter.run_asset_export_task(task):
                file=folder/(t.get_name()+'.exr');task.filename=str(file)
                if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Texture source export failed '+path)
            exports[path]=str(file)
    (R/'Review/texture-exports.json').write_text(json.dumps(exports,indent=2),encoding='utf8')
def calibrated_instances():
    # Authoring owns material changes; the production installer only binds saved art.
    for key in ('BedRefined','FootThrow'):
        mesh=load(report['meshes'][key]['path'])
        for slot in mesh.static_materials:
            role=str(slot.material_slot_name);name='MI_BP3_'+key+'_'+role;path=BASE+'/Materials/'+name
            mat=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
            parent=load(report['materials'][role]);scale=1.4/SURFACES[role]['period']
            if mat.get_editor_property('parent')!=parent or abs(L.get_material_instance_scalar_parameter_value(mat,'UVScale')-scale)>1e-6:
                mat.modify();L.set_material_instance_parent(mat,parent);L.set_material_instance_scalar_parameter_value(mat,'UVScale',scale);L.update_material_instance(mat);save(mat)
def main():
    import_textures();materials();meshes();calibrated_instances();report['stage']='assets_saved';report['shaders_compiled']=True;record();export_material_sources()
if __name__=='__main__':main()
