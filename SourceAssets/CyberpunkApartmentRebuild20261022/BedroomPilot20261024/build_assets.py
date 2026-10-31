"""Create only pilot-owned materials and meshes. Existing sources stay read-only."""
from pathlib import Path
import sys,json,hashlib,gc,traceback
import unreal as u
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import *
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report=dict(stage='building',materials={},meshes={},reused_textures=[],game_run=False,rendered=False)
previous=json.loads((R/'assets_saved.json').read_text('utf8')) if (R/'assets_saved.json').exists() else {}

def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing bedroom dependency '+path)
    return a
def save(a):
    if not a.get_path_name().startswith(BASE+'/'):raise RuntimeError('Outside pilot write boundary '+a.get_path_name())
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def node(m,kind,**props):
    n=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,b,pin):
    normal=lambda s:str(s).replace(' ','').replace('_','').lower()
    pin=next((str(n) for n in L.get_material_expression_input_names(b) if normal(n)==normal(pin)),pin)
    if not L.connect_material_expressions(a,'',b,pin):raise RuntimeError('Material pin '+pin)
def scalar(m,v):return node(m,'Constant',r=v)
def rgb(m,v):return node(m,'Constant3Vector',constant=u.LinearColor(*v,1))
def custom(m,code,inputs,width=3):
    n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for key in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',key);pins.append(p)
    n.set_editor_property('inputs',pins)
    for key,value in inputs.items():wire(value,n,key)
    return n
def texture(m,path,uv,normal=False):
    t=load(path);sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR if t.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_MASKS if 'MASKS' in str(t.compression_settings) else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
    n=node(m,'TextureSample',texture=t,sampler_type=sampler);wire(uv,n,'UVs')
    if path not in report['reused_textures']:report['reused_textures'].append(path)
    return n

def materials():
    for key,spec in SURFACES.items():
        name='M_BP_'+key;path=BASE+'/Materials/'+name
        m=load(path) if E.does_asset_exist(path) else A.create_asset(name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
        L.delete_all_material_expressions(m)
        m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
        uv=node(m,'Multiply');wire(node(m,'TextureCoordinate'),uv,'A')
        wire(node(m,'ScalarParameter',parameter_name='UVScale',default_value=1/spec['period']),uv,'B')
        n=texture(m,SUB+spec['normal'],uv,True)
        n=custom(m,'return normalize(float3(N.xy*S,lerp(1.0,N.z,saturate(S))));',{'N':n,'S':scalar(m,spec['strength'])})
        color=node(m,'VectorParameter',parameter_name='Tint',default_value=u.LinearColor(*spec['color'],1))
        if spec.get('base'):
            color=custom(m,'return Tint*lerp(.70,1.20,saturate(dot(C,float3(.2126,.7152,.0722))*2.2));',{'Tint':color,'C':texture(m,SUB+spec['base'],uv)})
        rough=scalar(m,sum(spec['limits'])/2)
        if spec.get('rough'):
            rough=custom(m,'return lerp(Lo,Hi,saturate(R.r));',{'R':texture(m,SUB+spec['rough'],uv),'Lo':scalar(m,spec['limits'][0]),'Hi':scalar(m,spec['limits'][1])},1)
        slab=node(m,'SubstrateShadingModels',shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
        for val,pin,prop in [(color,'BaseColor','BASE_COLOR'),(n,'Normal','NORMAL'),(rough,'Roughness','ROUGHNESS'),(scalar(m,spec['metal']),'Metallic','METALLIC')]:
            wire(val,slab,pin);L.connect_material_property(val,'',getattr(u.MaterialProperty,'MP_'+prop))
        if 'emission' in spec:
            emission=node(m,'Multiply');wire(rgb(m,spec['emission']),emission,'A')
            wire(node(m,'ScalarParameter',parameter_name='FixtureLevel',default_value=1.),emission,'B')
            wire(emission,slab,'Emissive Color');L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
        L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        result=L.recompile_material(m)
        if result:raise RuntimeError(str(result))
        # Complete pending shader work before saving the material production result.
        shader=L.get_statistics(m)
        if shader.get_editor_property('num_pixel_shader_instructions')<=0:
            raise RuntimeError('No compiled pixel program for '+key)
        save(m);report['materials'][key]=m.get_path_name();record();print('BP_MATERIAL_SAVED',key)

def meshes():
    for row in json.loads((R/'assembly.json').read_text('utf8'))['meshes']:
        digest=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest()
        old=previous.get('meshes',{}).get(row['key'],{})
        if old.get('sha256')==digest and E.does_asset_exist(row['asset']):
            report['meshes'][row['key']]=old;record();continue
        task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=row['name'];task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.FbxFactory()
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        d=opt.static_mesh_import_data
        for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False,one_convex_hull_per_ucx=True).items():d.set_editor_property(k,v)
        d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;task.options=opt;A.import_asset_tasks([task]);mesh=load(row['asset'])
        for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,load(report['materials'][str(slot.material_slot_name)]))
        settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True;SM.set_lod_build_settings(mesh,0,settings)
        body=mesh.get_editor_property('body_setup')
        if body:body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
        ns=mesh.get_editor_property('nanite_settings').copy();ns.enabled=row['nanite'];ns.explicit_tangents=True;ns.generate_fallback=u.NaniteGenerateFallback.ENABLED;ns.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;ns.fallback_percent_triangles=1.;mesh.set_editor_property('nanite_settings',ns)
        if row['nanite']:
            if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite production failed '+row['key'])
        save(mesh)
        report['meshes'][row['key']]=dict(path=mesh.get_path_name(),source_triangles=row['triangles'],simple_hulls=row['simple_hulls'],nanite=row['nanite'],sha256=digest)
        record();print('BP_MESH_SAVED',row['key'])
        mesh=None;task=None;opt=None;d=None;body=None;gc.collect();u.SystemLibrary.collect_garbage()

def main():
    try:
        materials();meshes();report['stage']='assets_saved';report['shaders_compiled']=True;record()
    except Exception:
        report['stage']='failed';report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
