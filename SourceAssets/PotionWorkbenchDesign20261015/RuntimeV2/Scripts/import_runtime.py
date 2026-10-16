from pathlib import Path
import unreal as u,json,re
ROOT=Path(__file__).resolve().parents[1]
HOST=ROOT.parent/'IntegrationV1/UEImportHost'
if Path(u.Paths.project_dir()).resolve()!=HOST.resolve():raise RuntimeError('Use the isolated potion import host')
DEST='/Game/Building/PotionWorkbench20261015/RuntimeV2'
BASE='/Game/Building/PotionWorkbench20261015/V1/Materials/'
OWNER='PotionWorkbench20261015_RuntimeV2'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
spec=json.loads((ROOT/'runtime_manifest.json').read_text('utf8'));report={'stage':'importing','meshes':[],'materials':[],'runtime_tested':False}
def save(obj):
    E.set_metadata_tag(obj,'PotionWorkbench.Owner',OWNER)
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Could not save '+obj.get_path_name())
def mat(name):
    path=DEST+'/Materials/'+name
    if E.does_asset_exist(path):
        ob=u.load_asset(path)
        if E.get_metadata_tag(ob,'PotionWorkbench.Owner')!=OWNER:raise RuntimeError('Unowned '+path)
        for n in list(L.get_material_expressions(ob)):L.delete_material_expression(ob,n)
    else:ob=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    return ob
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,b,input='',out=''):
    names=[str(n) for n in L.get_material_expression_input_names(b)]
    if input not in names and len(names)==1:input=names[0]
    if not L.connect_material_expressions(a,out,b,input):raise RuntimeError('Material connection failed '+input+' '+str(names))
def prop(m,n,p):
    if not L.connect_material_property(n,'',p):raise RuntimeError('Material property failed')
liquid=mat('M_AlchemyLiquid')
color=node(liquid,u.MaterialExpressionVectorParameter,parameter_name='PotionColor',default_value=u.LinearColor(.015,.3,.21,1))
prop(liquid,color,u.MaterialProperty.MP_BASE_COLOR)
rough=node(liquid,u.MaterialExpressionConstant,r=.16);prop(liquid,rough,u.MaterialProperty.MP_ROUGHNESS)
glow=node(liquid,u.MaterialExpressionMultiply,const_b=.12);wire(color,glow,'A');prop(liquid,glow,u.MaterialProperty.MP_EMISSIVE_COLOR)
agitation=node(liquid,u.MaterialExpressionScalarParameter,parameter_name='Agitation',default_value=.05)
time=node(liquid,u.MaterialExpressionTime);freq=node(liquid,u.MaterialExpressionMultiply,const_b=.7);wire(time,freq,'A')
uv=node(liquid,u.MaterialExpressionTextureCoordinate);mask=node(liquid,u.MaterialExpressionComponentMask,r=True,g=False,b=False,a=False);wire(uv,mask,'Input')
spatial=node(liquid,u.MaterialExpressionMultiply,const_b=6);wire(mask,spatial,'A')
phase=node(liquid,u.MaterialExpressionAdd);wire(freq,phase,'A');wire(spatial,phase,'B')
sine=node(liquid,u.MaterialExpressionSine);wire(phase,sine,'Input')
amp=node(liquid,u.MaterialExpressionMultiply);wire(sine,amp,'A');wire(agitation,amp,'B')
up=node(liquid,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,.18,1))
offset=node(liquid,u.MaterialExpressionMultiply);wire(amp,offset,'A');wire(up,offset,'B');prop(liquid,offset,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
L.recompile_material(liquid);save(liquid);report['materials'].append(liquid.get_path_name())
rune=mat('M_AlchemyRune');c=node(rune,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.8,.36,.055,1));prop(rune,c,u.MaterialProperty.MP_BASE_COLOR)
g=node(rune,u.MaterialExpressionScalarParameter,parameter_name='Glow',default_value=.08)
em=node(rune,u.MaterialExpressionMultiply);wire(c,em,'A');wire(g,em,'B');prop(rune,em,u.MaterialProperty.MP_EMISSIVE_COLOR)
L.recompile_material(rune);save(rune);report['materials'].append(rune.get_path_name())
u.load_module('StaticMeshEditor');SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
opt=u.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False
opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
d.convert_scene=True;d.convert_scene_unit=True;d.force_front_x_axis=False;d.transform_vertex_to_absolute=True
d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.remove_degenerates=False
canon=lambda s:re.sub('[^a-z0-9]','',str(s).lower())
for p in spec['parts']:
    task=u.AssetImportTask();task.filename=p['lods'][0]['source'];task.destination_path=DEST+'/Meshes';task.destination_name=p['name']
    task.automated=True;task.replace_existing=True;task.save=False;task.options=opt
    A.import_asset_tasks([task]);objects=task.get_objects()
    mesh=next((o for o in objects if isinstance(o,u.StaticMesh)),None)
    if not mesh:raise RuntimeError('Import failed '+p['name'])
    mats={canon(n):u.load_asset(BASE+'M_'+n) for n in p['materials']}
    for i,s in enumerate(mesh.static_materials):
        material=mats.get(canon(s.material_slot_name))
        if not material:raise RuntimeError('Missing source material '+str(s.material_slot_name))
        mesh.set_material(i,material)
    for i,lod in enumerate(p['lods'][1:],1):
        if SM.get_lod_count(mesh)<=i:SM.import_lod(mesh,i,lod['source'])
    for i in range(SM.get_lod_count(mesh)):
        settings=SM.get_lod_build_settings(mesh,i);settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
        settings.generate_lightmap_u_vs=False;settings.recompute_normals=False;settings.recompute_tangents=True;settings.remove_degenerates=False
        SM.set_lod_build_settings(mesh,i,settings)
    if len(p['lods'])>1:SM.set_lod_screen_sizes(mesh,[1,.45,.18])
    nan=mesh.get_editor_property('nanite_settings');nan.enabled=False;SM.set_nanite_settings(mesh,nan,True)
    save(mesh);report['meshes'].append(mesh.get_path_name())
    (ROOT/'Receipts/import-runtime.json').write_text(json.dumps(report,indent=2),'utf8')
report['stage']='assets_saved';(ROOT/'Receipts/import-runtime.json').write_text(json.dumps(report,indent=2),'utf8')
u.log('ALCHEMY_RUNTIME_ASSETS_SAVED')
