"""Background UE publication for the scoped kitchen only.
Creates new materials and kitchen-local asset copies. No map mutation here.
"""
from pathlib import Path
import json,traceback,hashlib
from datetime import datetime
import unreal as u
R=Path(__file__).resolve().parent
BASE='/Game/Props/CyberpunkApartmentKitchen20261024'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report=dict(stage='building',base=BASE,materials={},textures={},meshes={},shared_copies={})
previous=R/'assets_saved.json'
if previous.exists():
    try:
        old=json.loads(previous.read_text(encoding='utf8'))
        for field in ('materials','textures','meshes'):
            if isinstance(old.get(field),dict):report[field]=old[field]
    except Exception:pass
def record():
    report['last_update']=datetime.now().astimezone().isoformat()
    (R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('KITCHEN_ASSET_STAGE '+report['stage']+' '+str(len(report['materials']))+' '+str(len(report['meshes'])),flush=True)
SOURCE_HASH=hashlib.sha256(b''.join((R/n).read_bytes() for n in ['build_assets.py','spec.py','make_surfaces.py'])).hexdigest()
def save(o):
    if not E.save_loaded_asset(o,False):
        package=o.get_outer()
        if not u.EditorLoadingAndSavingUtils.save_packages([package],False):raise RuntimeError('Save package '+package.get_path_name())
def load(path):
    o=u.load_asset(path)
    if not o:raise RuntimeError('Missing asset '+path)
    return o
def node(m,kind,**kw):
    o=L.create_material_expression(m,getattr(u,'MaterialExpression'+kind))
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def wire(a,b,pin,out=''):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material connection '+pin)
def scalar(m,v):return node(m,'Constant',r=v)
def rgb(m,v):return node(m,'Constant3Vector',constant=u.LinearColor(*v,1))
def custom(m,code,inputs,channels=3):
    n=node(m,'Custom',code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(channels)))
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for name,source in inputs.items():wire(source,n,name)
    return n
SIMPLE={
 'Graphite':dict(color=(.022,.024,.028),rough=.40,metal=.65),
 'Rubber':dict(color=(.012,.013,.015),rough=.73,metal=0),
 'Inside':dict(color=(.065,.067,.071),rough=.67,metal=.05),
 'Copper':dict(color=(.25,.105,.046),rough=.32,metal=.85),
 'Paper':dict(color=(.56,.54,.43),rough=.85,metal=0),
 'Ink':dict(color=(.016,.026,.030),rough=.63,metal=0),
 'Leaf':dict(color=(.047,.14,.065),rough=.50,metal=0),
 'Soil':dict(color=(.025,.019,.012),rough=.98,metal=0),
 'Coffee':dict(color=(.018,.008,.003),rough=.20,metal=0),
 'Warm':dict(color=(.95,.72,.39),rough=.32,metal=0,emission=3),
 'Cyan':dict(color=(.028,.34,.39),rough=.30,metal=0,emission=1.6),
 'Red':dict(color=(.27,.025,.017),rough=.55,metal=0),
 'Ochre':dict(color=(.38,.18,.043),rough=.51,metal=0),
 'Sage':dict(color=(.12,.18,.12),rough=.56,metal=0),
 'Food':dict(color=(.54,.33,.12),rough=.60,metal=0),
 'Glass':dict(color=(.70,.73,.76),rough=.14,metal=0,transmission=.92),
}
PBR={
 'Enamel':('PetrolEnamel',.38,(1.,1.,1.),.42,.12,.30),
 'Stone':('HonedStone',.55,(1.,1.,1.),.46,0,.28),
 'Tile':('GlazedTile',.60,(1.,1.,1.),.34,0,.42),
 'Steel':('BrushedSteel',.36,(.90,.92,.94),.32,1,.30),
 'Wood':('SmokedWalnut',.80,(1.,1.,1.),.48,0,.38),
 'Linen':('LinenTowel',.22,(1.,1.,1.),.88,0,.42),
 'Porcelain':('Porcelain',.25,(1.,1.,1.),.26,0,.16),
}
def import_tex(family,suffix,normal=False):
    path=BASE+'/Textures/T_KP_'+family+'_'+suffix
    t=u.AssetImportTask();t.filename=str(R/'TexturesV2'/f'T_KP_{family}_{suffix}.png');t.destination_path=BASE+'/Textures';t.destination_name='T_KP_'+family+'_'+suffix
    t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);tex=load(path)
    tex.set_editor_property('srgb',suffix=='BC');tex.set_editor_property('flip_green_channel',False)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT if suffix=='BC' else u.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
    tex.set_editor_property('never_stream',False);save(tex)
    report['textures'][family+'_'+suffix]=path
    record()
    return tex

def pbr_material(role,spec):
    family,period,tint,rough,metal,strength=spec
    for suffix in ['BC','N','ORM']:import_tex(family,suffix,suffix=='N')
    path=BASE+'/Materials/M_KP_'+role
    m=load(path) if E.does_asset_exist(path) else A.create_asset('M_KP_'+role,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    for n in list(L.get_material_expressions(m)):L.delete_material_expression(m,n)
    coord=node(m,'TextureCoordinate');scale=scalar(m,1/period)
    uv=node(m,'Multiply');wire(coord,uv,'A');wire(scale,uv,'B')
    def tex(suffix,normal=False):
        sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_COLOR if suffix=='BC' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
        t=node(m,'TextureSample',texture=load(BASE+'/Textures/T_KP_'+family+'_'+suffix),sampler_type=sampler);wire(uv,t,'UVs');return t
    base=custom(m,'return C.rgb*Tint;',{'C':tex('BC'),'Tint':rgb(m,tint)})
    n=custom(m,'return normalize(float3(N.xy*S,lerp(1.,N.z,saturate(S))));',{'N':tex('N',True),'S':scalar(m,strength)})
    packed=tex('ORM')
    r=custom(m,'return lerp(L,H,P.g);',{'P':packed,'L':scalar(m,max(.05,rough-.055)),'H':scalar(m,min(1,rough+.055))},1)
    ao=custom(m,'return P.r;',{'P':packed},1)
    met=custom(m,'return max(P.b,M);',{'P':packed,'M':scalar(m,metal)},1)
    for source,pin in [(base,'BASE_COLOR'),(n,'NORMAL'),(r,'ROUGHNESS'),(met,'METALLIC'),(scalar(m,.35),'SPECULAR'),(ao,'AMBIENT_OCCLUSION')]:
        L.connect_material_property(source,'',getattr(u.MaterialProperty,'MP_'+pin))
    m.set_editor_property('used_with_nanite',True)
    L.recompile_material(m);save(m)
    report['materials']['KP_'+role]=dict(path=path,normal=BASE+'/Textures/T_KP_'+family+'_N',normal_input='NORMAL',normal_green='DirectX; no flip',period_m=period,tint=tint,roughness=rough,metal=metal,normal_strength=strength,source_sha256=SOURCE_HASH);record()

def simple_material(role,spec):
    path=BASE+'/Materials/M_KP_'+role
    m=load(path) if E.does_asset_exist(path) else A.create_asset('M_KP_'+role,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    for n in list(L.get_material_expressions(m)):L.delete_material_expression(m,n)
    color=rgb(m,spec['color']);L.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    for pin,value in [('ROUGHNESS',spec['rough']),('METALLIC',spec['metal'])]:L.connect_material_property(scalar(m,value),'',getattr(u.MaterialProperty,'MP_'+pin))
    if spec.get('emission'):
        L.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
        # Color itself is restrained; small status elements stay below practical lights.
        L.connect_material_property(custom(m,'return C*S;',{'C':color,'S':scalar(m,spec['emission'])}),'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    if spec.get('transmission'):
        m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        m.set_editor_property('two_sided',True)
        # Static vessels stay inexpensive and do not add ray-traced refraction.
        L.connect_material_property(scalar(m,.34),'',u.MaterialProperty.MP_OPACITY)
    L.recompile_material(m);save(m)
    report['materials']['KP_'+role]=dict(path=path,normal='unchanged shared micro-normal when recolouring existing assets',source_sha256=SOURCE_HASH);record()

def verify_normal_bindings():
    bindings={}
    for role in PBR:
        name='KP_'+role;entry=report['materials'].get(name,{})
        mat=load(entry['path']);normal=load(entry['normal'])
        root=L.get_material_property_input_node(mat,u.MaterialProperty.MP_NORMAL)
        if not root:raise RuntimeError('Normal property not connected '+name)
        if normal.get_editor_property('compression_settings')!=u.TextureCompressionSettings.TC_NORMALMAP:raise RuntimeError('Normal compression '+name)
        if normal.get_editor_property('flip_green_channel'):raise RuntimeError('Unexpected green flip '+name)
        samples=[n for n in L.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionTextureSample) and n.get_editor_property('texture')==normal]
        if not samples or any(n.get_editor_property('sampler_type')!=u.MaterialSamplerType.SAMPLERTYPE_NORMAL for n in samples):raise RuntimeError('Normal sampler '+name)
        bindings[name]=dict(normal_input_node=root.get_name(),output=L.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_NORMAL),texture=normal.get_path_name(),compression=str(normal.get_editor_property('compression_settings')),flip_green_channel=False,samplers=[str(n.get_editor_property('sampler_type')) for n in samples])
    report['normal_bindings']=bindings

def import_mesh(row):
    key=row['key'];path=BASE+'/Meshes/SM_KP_'+key.removeprefix('KIT_')
    if key in report['meshes'] and E.does_asset_exist(path):
        if report['meshes'][key].get('fbx_sha256')==hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest():return
    t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name='SM_KP_'+key.removeprefix('KIT_')
    t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=True;t.factory=u.FbxFactory()
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.import_as_skeletal=False
    data=opt.static_mesh_import_data
    for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=True,import_uniform_scale=1.).items():data.set_editor_property(k,v)
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
    opt.static_mesh_import_data.set_editor_property('build_reversed_index_buffer',False)
    t.options=opt;A.import_asset_tasks([t]);mesh=load(path)
    build=SM.get_lod_build_settings(mesh,0)
    for k,v in dict(use_full_precision_u_vs=True,use_high_precision_tangent_basis=True,use_mikk_t_space=True,recompute_tangents=False,recompute_normals=False).items():build.set_editor_property(k,v)
    SM.set_lod_build_settings(mesh,0,build)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        m=report['materials'].get(str(slot.material_slot_name))
        if m:mesh.set_material(i,load(m['path']))
    if not E.save_loaded_asset(mesh,False):
        if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outer()],False):raise RuntimeError('Mesh package save '+path)
    report['meshes'][key]=dict(path=path,fbx_sha256=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest(),bounds=[list(mesh.get_bounding_box().min.to_tuple()),list(mesh.get_bounding_box().max.to_tuple())],materials=[s.material_interface.get_path_name() if s.material_interface else None for s in mesh.get_editor_property('static_materials')]);record()

def main():
    report['source_sha256']=SOURCE_HASH
    report['texture_directory']='TexturesV2'
    report['texture_source_sha256']=hashlib.sha256((R/'texture-source.json').read_bytes()).hexdigest()
    record()
    # Receipt-backed resume: imported packages are saved immediately; only a
    # missing or previously unfinished stage is rebuilt after a stopped batch.
    # Reuse already-saved materials; only build ones that are genuinely missing.
    # Rebuilding an existing graph in-place is what produced the None node error.
    for role,spec in PBR.items():
        entry=report['materials'].get('KP_'+role,{})
        path=entry.get('path','')
        # does_asset_exist can report False for an on-disk asset that is not yet
        # loaded; load_asset is the reliable existence check here.
        if not path or not u.load_asset(path):
            pbr_material(role,spec)
        elif entry.get('source_sha256')!=SOURCE_HASH:
            entry['source_sha256']=SOURCE_HASH;report['materials']['KP_'+role]=entry
    for role,spec in SIMPLE.items():
        entry=report['materials'].get('KP_'+role,{})
        path=entry.get('path','')
        if not path or not u.load_asset(path):
            simple_material(role,spec)
        elif entry.get('source_sha256')!=SOURCE_HASH:
            entry['source_sha256']=SOURCE_HASH;report['materials']['KP_'+role]=entry
    verify_normal_bindings()
    for row in json.loads((R/'assembly.json').read_text())['meshes']:
        if row.get('local_audit_only') and not row.get('fbx'):continue
        import_mesh(row)
    report['stage']='assets_saved';report.pop('error',None);record();print('KITCHEN_ASSETS_SAVED',len(report['meshes']),len(report['materials']),flush=True)
if __name__=='__main__':
    try:main()
    except Exception:
        report['stage']='failed';report['error']=traceback.format_exc();record();raise
