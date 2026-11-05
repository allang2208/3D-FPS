"""Save the three M24 fitted tactical meshes and their private surface variants."""
import unreal as u,json,re
from pathlib import Path
O=Path(__file__).resolve().parent;ROOT='/Game/Weapons/M24/Tactical20261104'
D=json.loads((O/'current_sources.json').read_text());AUTH=json.loads((O/'authoring.json').read_text())
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
R={'complete':False,'materials':{},'meshes':{},'runtime_tested':False}

def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing asset '+p)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Asset save failed '+a.get_path_name())
def clone(src,dst):
    if E.does_asset_exist(dst):raise RuntimeError('Existing destination retained '+dst)
    a=E.duplicate_asset(src,dst)
    if not a:raise RuntimeError('Asset duplication failed '+src)
    return a
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for key,value in props.items():n.set_editor_property(key,value)
    return n
def wire(src,dst,pin):
    a,ch=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_expressions(a,ch,dst,pin):raise RuntimeError('Material connection failed '+pin)
def inputs(n,pins):
    old=list(n.get_editor_property('inputs'))
    for key in pins:
        v=u.CustomInput();v.set_editor_property('input_name',key);old.append(v)
    n.set_editor_property('inputs',old)
    for key,src in pins.items():wire(src,n,key)
def grain(m):
    p=node(m,u.MaterialExpressionVertexInterpolator);n=node(m,u.MaterialExpressionVertexInterpolator)
    wire(node(m,u.MaterialExpressionPreSkinnedPosition),p,'VS');wire(node(m,u.MaterialExpressionPreSkinnedNormal),n,'VS')
    tex=node(m,u.MaterialExpressionTextureObjectParameter,parameter_name='M24FineGrain',texture=load('/Game/Weapons/WeaponSurface/Textures/T_WS_Grain'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    c=node(m,u.MaterialExpressionCustom,description='M24 tactical local fine grain',output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,
        code='float3 w=pow(abs(normalize(N)),4);w/=max(dot(w,float3(1,1,1)),.0001);float3 q=P/2.;return Texture2DSample(T,TSampler,q.yz)*w.x+Texture2DSample(T,TSampler,q.xz+float2(.37,.61))*w.y+Texture2DSample(T,TSampler,q.xy+float2(.71,.13))*w.z;')
    inputs(c,{'P':p,'N':n,'T':tex});return c

dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(ROOT) for p in dirty):raise RuntimeError('Unsaved destination retained')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; retain live state')
for kind in AUTH['devices']:
    if E.does_asset_exist(ROOT+'/SM_'+kind):raise RuntimeError('Existing fitted mesh retained '+kind)

reference=D['meshes']['chassis']['slots'][0]['material']
bearing=clone(reference,ROOT+'/Materials/MI_M24_Tactical_Bearing')
for key,value in {'MaskUVChannel':0.,'SourceRoughnessWeight':0.,'AOStrength':0.,'CavityDarken':0.,'CavityRoughness':0.}.items():
    L.set_material_instance_scalar_parameter_value(bearing,key,value)
for key,path in {'SurfaceNormal':'/Engine/EngineMaterials/DefaultNormal','SourceRoughness':'/Game/Weapons/WeaponSurface/Textures/T_WS_GreyLinear','SurfaceMask':'/Game/Weapons/WeaponSurface/Textures/T_WS_MaskNeutral'}.items():
    L.set_material_instance_texture_parameter_value(bearing,key,load(path))
L.update_material_instance(bearing);save(bearing)
R['materials']['bearing']={'path':bearing.get_path_name(),'reference':reference};record()
materials={}
for kind in ('laser','flashlight'):
    src=D['meshes'][kind]['slots'][0]['material']
    m=clone(src,ROOT+'/Materials/M_M24_'+kind+'_Body')
    for name in ('automatically_set_usage_in_editor','used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):m.set_editor_property(name,False)
    existing=list(L.get_material_expressions(m))
    wet=node(m,u.MaterialExpressionScalarParameter,parameter_name='WeaponWetness',default_value=0.)
    g=grain(m)
    for n in existing:
        if not isinstance(n,u.MaterialExpressionCustom):continue
        description=str(n.get_editor_property('description'));code=n.get_editor_property('code')
        # Donor coating/aperture masks are spatial. Convert the fitted native
        # position back to the donor frame before evaluating those masks.
        if re.search(r'\bP\b',code):
            code='float3 CanonicalP=float3(-P.y-53.2,P.x-4.5,P.z-12.);\n'+re.sub(r'\bP\b','CanonicalP',code)
        if description=='ASH receiver black metal':
            code='return lerp(Base,float3(.026,.029,.032)*(1-saturate(Wet)*.04),Mask);'
            inputs(n,{'Wet':wet})
        elif description=='Optics and coating roughness':
            code='float dry=.48+(Grain.r-.5)*.012+(Grain.g-.5)*.004;return lerp(Base,lerp(dry,dry*.68,saturate(Wet)),Mask);'
            inputs(n,{'Wet':wet,'Grain':g})
        elif description=='Coated metal, nonmetal optics':code='return Mask;'
        n.set_editor_property('code',code)
    E.set_metadata_tag(m,'M24FinishReference',reference)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Material compile failed '+str(errors))
    save(m);materials[kind]=m
    R['materials'][kind]={'path':m.get_path_name(),'source':src,'spatial_mask_frame':'canonical donor inverse transform','metal_roughness':.48};record()

old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    for kind,entry in AUTH['devices'].items():
        name='SM_'+kind;path=ROOT+'/'+name
        options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_animations=False;options.override_full_name=True
        data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.remove_degenerates=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=ROOT;task.destination_name=name
        task.automated=True;task.replace_existing=False;task.save=False;task.options=options;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);mesh=load(path)
        if not task.imported_object_paths:raise RuntimeError('No imported mesh '+path)
        slots=list(mesh.static_materials)
        source_bindings={s['material'].split('.')[-1]:s['material'] for s in D['meshes'][kind]['slots']}
        for i,s in enumerate(slots):
            label=re.sub(r'[._]\d{3}$','',str(s.material_slot_name))
            if label=='M24_Tactical_Bearing' or 'GripMetal' in label or label=='M_Blessed_Graphite':mat=bearing
            elif label=='M_ASH12_'+kind+'_Body':mat=materials[kind]
            elif label in source_bindings:mat=load(source_bindings[label])
            else:raise RuntimeError('Missing material binding '+kind+' '+label)
            s.material_interface=mat;slots[i]=s
        mesh.set_editor_property('static_materials',slots)
        for label,position in entry['sockets'].items():
            socket=mesh.find_socket(label)
            if socket is None:
                socket=u.StaticMeshSocket(outer=mesh);socket.set_editor_property('socket_name',label);mesh.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(*position))
        E.set_metadata_tag(mesh,'SourceDevice',entry['source'])
        E.set_metadata_tag(mesh,'M24TacticalMount','Advanced chassis right rail; single primary slot; native M24Attachments::Mount; authored emitter axis')
        save(mesh)
        R['meshes'][kind]={'path':mesh.get_path_name(),'sockets':entry['sockets'],'materials':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in mesh.static_materials]};record()
        print('M24_TACTICAL_SAVED',kind,flush=True)
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
R['complete']=True;record();print('M24_TACTICAL_INSTALL_COMPLETE',flush=True)
