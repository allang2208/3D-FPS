"""Save only the new near-bank revision, with existing library materials and assemblies."""
from pathlib import Path
import unreal as u,json,hashlib,collections,math,gc,sys
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R));from design import *
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
G=json.loads((R/'geometry.json').read_text());D=json.loads((R/'layout.json').read_text())
URBAN=json.loads((PROJECT/'SourceAssets/CyberpunkUrbanLandscape20261025/assets_saved.json').read_text())
report=json.loads((R/'assets_saved.json').read_text()) if (R/'assets_saved.json').exists() else dict(stage='building',materials={},meshes={},blueprints={},tests_run=False)
def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing required asset '+str(p))
    return a
def save(a):
    E.set_metadata_tag(a,'NearBank.Owner',OWNER)
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def node(m,name,**values):
    n=L.create_material_expression(m,getattr(u,'MaterialExpression'+name))
    for k,v in values.items():n.set_editor_property(k,v)
    return n
def wire(a,b,pin,out=''):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material pin '+pin)
def custom(m,code,inputs,size=3):
    n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)));ps=[]
    for k in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',k);ps.append(p)
    n.set_editor_property('inputs',ps)
    for k,v in inputs.items():wire(v,n,k)
    return n
def surfaces():
    for k in ('Paving','Metal','Rubber','Warm','Lawn'):report['materials'][k]=URBAN['materials'][k]
    report['materials']['Ground']=URBAN['materials']['Lawn']
    maps='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV18/Textures/T_AP18_Paving_'
    for key in ('Stone','Cap','Asphalt','Marking'):
        name='M_NB_'+key;path=BASE+'/Materials/'+name
        m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
        if E.get_metadata_tag(m,'NearBank.Owner')==OWNER and report['materials'].get(key)==path+'.'+name:continue
        L.delete_all_material_expressions(m);m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
        bc=node(m,'TextureSample',texture=load(maps+'BC'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        nn=node(m,'TextureSample',texture=load(maps+'N'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        orm=node(m,'TextureSample',texture=load(maps+'ORM'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        pos=node(m,'WorldPosition');wet=node(m,'CollectionParameter',collection=load('/Game/Weather/Materials/MPC_FPS_Weather'),parameter_name='WeatherWetness')
        tint={'Stone':'.76,.77,.70','Cap':'1.15,1.16,1.12','Asphalt':'.12,.14,.16','Marking':'2.4,2.35,2.15'}[key]
        base=custom(m,'float tide=1-smoothstep(-11260,-10960,P.z); float streak=.5+.5*sin(P.x*.017+sin(P.y*.011)); return C*float3('+tint+')*lerp(1,.48,tide*(.75+.25*streak));',dict(C=bc,P=pos))
        normal=custom(m,'return normalize(float3(N.xy*'+('.22' if key=='Asphalt' else '.65')+',max(.2,N.z)));',dict(N=nn))
        rough=custom(m,'float tide=1-smoothstep(-11260,-10960,P.z); return lerp(clamp(O.g,.55,.95),.35,max(saturate(Wet)*.6,tide));',dict(O=orm,Wet=wet,P=pos),1)
        zero=node(m,'Constant',r=0);slab=node(m,'SubstrateShadingModels')
        for value,pin,prop in [(base,'BaseColor','BASE_COLOR'),(normal,'Normal','NORMAL'),(rough,'Roughness','ROUGHNESS'),(zero,'Metallic','METALLIC'),(zero,'Emissive Color','EMISSIVE_COLOR')]:
            wire(value,slab,pin);L.connect_material_property(value,'',getattr(u.MaterialProperty,'MP_'+prop))
        L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        errors=L.recompile_material(m)
        if errors:raise RuntimeError(str(errors))
        save(m);report['materials'][key]=m.get_path_name();record()
    record()

def meshes(start=0,end=None):
    for row in G['meshes'][start:end]:
        digest=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest();prior=report['meshes'].get(row['key'],{})
        if prior.get('sha256')==digest and E.does_asset_exist(prior['path']):continue
        t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
        o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;o.import_mesh=True;o.import_materials=False;o.import_textures=False;o.import_animations=False
        for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False).items():o.static_mesh_import_data.set_editor_property(k,v)
        o.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=o;A.import_asset_tasks([t]);m=load(BASE+'/Meshes/'+row['name'])
        for i,s in enumerate(m.static_materials):m.set_material(i,load(report['materials'][str(s.material_slot_name)]))
        settings=SM.get_lod_build_settings(m,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;SM.set_lod_build_settings(m,0,settings)
        ns=m.get_editor_property('nanite_settings').copy();ns.enabled=True;ns.explicit_tangents=True
        if row['collision']:
            ns.generate_fallback=u.NaniteGenerateFallback.ENABLED;ns.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;ns.fallback_percent_triangles=1.0
        m.set_editor_property('nanite_settings',ns)
        body=m.get_editor_property('body_setup')
        if body and row['collision']:body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        if not u.PlazaInstanceTools.build_nanite_data(m):raise RuntimeError('Nanite build failed '+row['key'])
        save(m);report['meshes'][row['key']]=dict(path=m.get_path_name(),sha256=digest,collision=row['collision']);record()
        print('NB_MESH_SAVED',row['key'],flush=True);gc.collect();u.SystemLibrary.collect_garbage()

def blueprint(name):
    s=u.get_engine_subsystem(u.SubobjectDataSubsystem);f=u.SubobjectDataBlueprintFunctionLibrary;path=BASE+'/Blueprints/'+name
    bp=u.load_asset(path)
    if not bp:
        fac=u.BlueprintFactory();fac.set_editor_property('parent_class',u.Actor);bp=A.create_asset(name,BASE+'/Blueprints',u.Blueprint,fac)
    handles=s.k2_gather_subobject_data_for_blueprint(bp);byname={str(f.get_variable_name(f.get_data(h))):h for h in handles}
    def obj(h):return f.get_object(f.get_data(h))
    def comp(name,cls,parent):
        h=byname.get(name)
        if not h:
            h,why=s.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=cls,blueprint_context=bp))
            if not f.is_handle_valid(h):raise RuntimeError(str(why))
            s.rename_subobject(h,u.Text(name));byname[name]=h
        c=obj(h);c.modify();return h,c
    # The automatically generated DefaultSceneRoot is recreated as Movable by
    # blueprint compilation. Use an authored SCS root so static HISM children
    # remain attachable when the saved map is loaded or construction runs.
    had_authored_root='NearBankRoot' in byname
    root,c=comp('NearBankRoot',u.SceneComponent,handles[0])
    c.set_mobility(u.ComponentMobility.STATIC)
    if not had_authored_root:
        if not s.make_new_scene_root(handles[0],root,bp):raise RuntimeError('Cannot author static assembly root '+name)
    return bp,root,comp
def assemblies():
    groups=collections.defaultdict(list)
    for p in D['plants']:groups[math.floor(p['p'][0]/200)].append(('plant',p))
    for p in D['assemblies']:groups[math.floor(p['p'][0]/200)].append(('fixture',p))
    for cell,rows in sorted(groups.items()):
        name=f'BP_NB_Cell_{cell+10:02d}';bp,root,component=blueprint(name);origin=[cell*200+100,0,GROUND];types=collections.defaultdict(list)
        for kind,p in rows:types[(kind,p['mesh'] if kind=='plant' else p['kind'])].append(p)
        for (kind,key),instances in types.items():
            h,c=component(kind+'_'+key,u.HierarchicalInstancedStaticMeshComponent,root);c.set_mobility(u.ComponentMobility.STATIC)
            subsystem=u.get_engine_subsystem(u.SubobjectDataSubsystem)
            if not subsystem.attach_subobject(root,h):raise RuntimeError('Cannot attach assembly component '+key)
            if kind=='plant':
                src=URBAN['foliage'][key];mesh=src['mesh'];materials=src['materials']
            else:
                mesh=report['meshes'][key]['path'] if key in report['meshes'] else URBAN['meshes'][key]['path'];materials=None
            c.set_static_mesh(load(mesh));c.clear_instances();c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',True);c.set_editor_property('affect_distance_field_lighting',False)
            if materials:
                for i,path in enumerate(materials):c.set_material(i,load(path))
            transforms=[]
            for p in instances:
                tr=u.Transform();tr.translation=u.Vector(*[(p['p'][j]-origin[j])*100 for j in range(3)]);tr.rotation=u.Rotator(pitch=0,yaw=p['yaw'],roll=0).quaternion();tr.scale3d=u.Vector(p['scale'],p['scale'],p['scale']);transforms.append(tr)
            c.add_instances(transforms,False,False,False)
            c.set_cull_distances(0,35000 if kind=='plant' and key in ('Shrub','GroundA') else 0)
        if not u.BlueprintEditorLibrary.compile_blueprint(bp):raise RuntimeError('Blueprint compile failed '+name)
        cdo=u.get_default_object(bp.generated_class());tick=cdo.get_editor_property('primary_actor_tick');tick.set_editor_property('start_with_tick_enabled',False);cdo.set_editor_property('primary_actor_tick',tick)
        save(bp);report['blueprints'][name]=dict(path=bp.get_path_name(),origin=origin,instances=len(rows));record();print('NB_ASSEMBLY_SAVED',name,len(rows),flush=True)
def main():
    surfaces();meshes();assemblies();report.update(stage='assets_saved',counts=D['counts']);record();print('NEARBANK_ASSETS_SAVED',D['counts'],flush=True)
if __name__=='__main__':main()
