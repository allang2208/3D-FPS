"""Import and save fitted parts, private surface variants and sparse grips."""
import unreal as u,json,hashlib,gzip,gc
from pathlib import Path
r=Path(__file__).resolve().parent;p=r.parents[2];E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
D='/Game/Weapons/M249/CommonParts20261108';M='/Game/Weapons/M249/Surface20261108/Master'
inputs=json.loads((r/'inputs.json').read_text());recipe=json.loads((r/'parts_recipe.json').read_text())
receipt=r/'install_receipt.json';report=json.loads(receipt.read_text()) if receipt.exists() else {'saved':{},'materials':{},'meshes':{},'profiles':{},'runtime_tested':False}
report['complete']=False
def record():receipt.write_text(json.dumps(report,indent=2))
def disk(a):return p/'Content'/(a.split('.')[0].removeprefix('/Game/')+'.uasset')
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE is running; assets preserved')
dirty={q.get_name() for q in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(q.startswith((D,M+'/M_M249Part')) and q not in report.get('pending_import',[]) for q in dirty):raise RuntimeError('Unsaved common-part assets retained')
for src,sha in inputs['hashes'].items():
    if src.split('.')[0] in dirty or hashlib.sha256(disk(src).read_bytes()).hexdigest()!=sha:raise RuntimeError('Production source changed: '+src)
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing '+path)
    return a
def owned(path):
    if disk(path).exists() and path in report.get('pending_import',[]) and path not in report['saved']:
        # A normal editor exit may save a mesh imported immediately before a
        # Python interruption. Resume its slot binding without reimporting it.
        asset=load(path);source=Path(asset.get_editor_property('asset_import_data').get_first_filename()).resolve()
        expected=(r/'Exports'/(path.rsplit('/',1)[1]+'.fbx')).resolve()
        if source!=expected:raise RuntimeError('Pending import source changed '+path)
        backup=r/'Recovery';backup.mkdir(exist_ok=True);(backup/disk(path).name).write_bytes(disk(path).read_bytes())
        report['saved'][path]=hashlib.sha256(disk(path).read_bytes()).hexdigest();record()
    if disk(path).exists() and path not in report['saved']:raise RuntimeError('Unowned destination '+path)
    if path in report['saved'] and hashlib.sha256(disk(path).read_bytes()).hexdigest()!=report['saved'][path]:raise RuntimeError('Changed destination '+path)
def save(a):
    path=a.get_path_name().split('.')[0]
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+path)
    report['saved'][path]=hashlib.sha256(disk(path).read_bytes()).hexdigest();record();return a
def clone(src,dst):
    owned(dst)
    if disk(dst).exists():return load(dst),False
    a=E.duplicate_asset(src,dst)
    if not a:raise RuntimeError('Clone '+src)
    return a,True
def node(m,cls,**props):
    a=L.create_material_expression(m,cls)
    for k,v in props.items():a.set_editor_property(k,v)
    return a
def wire(src,dst,pin):
    a,out=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_expressions(a,out,dst,pin):raise RuntimeError('Wire '+pin)
def output(src,name):
    a,out=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_property(a,out,getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError('Output '+name)
def custom(m,label,code,pins,size):
    a=node(m,u.MaterialExpressionCustom,description=label,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)));values=[]
    for key in pins:
        v=u.CustomInput();v.set_editor_property('input_name',key);values.append(v)
    a.set_editor_property('inputs',values)
    for key,src in pins.items():wire(src,a,key)
    return a
def scalar(m,key,value):return node(m,u.MaterialExpressionScalarParameter,parameter_name=key,default_value=value)
def constant(m,value):return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*value,1)) if isinstance(value,tuple) else node(m,u.MaterialExpressionConstant,r=value)
def original(m,name,default):
    prop=getattr(u.MaterialProperty,'MP_'+name);a=L.get_material_property_input_node(m,prop)
    return (a,L.get_material_property_input_node_output_name(m,prop)) if a else constant(m,default)
def compile_save(m):
    errors=list(L.recompile_material(m) or [])
    if errors:raise RuntimeError('Material compile '+str(errors[:3]))
    return save(m)
beads=next(c['code'] for k,v in inputs['materials'].items() if 'R01_mount' in k for c in v['customs'] if c['description']=='WeatherBeads')
def wet_layer(m):
    data=custom(m,'M249 part single wet film',beads,{'UV':node(m,u.MaterialExpressionTextureCoordinate),'Wet':scalar(m,'WeaponWetness',0.),'Scale':scalar(m,'BeadScale',78.),'RainGravity':node(m,u.MaterialExpressionVectorParameter,parameter_name='RainGravity',default_value=u.LinearColor(0,1,0,0)),'RainTime':node(m,u.MaterialExpressionTime),'RainFlow':scalar(m,'RainFlowStrength',.65),'RainBeading':scalar(m,'RainBeadStrength',1.)},4)
    for prop,default,code,size in [('BASE_COLOR',(.034,.035,.037),'return Base*(1-Data.a*.065);',3),('ROUGHNESS',.42,'return lerp(lerp(Base,max(.12,Base*.76),Data.a),.085,Data.b*.72);',1),('NORMAL',(0,0,1),'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.12)+Data.xy*.55,Base.z));',3)]:
        output(custom(m,'M249 wet '+prop,code,{'Base':original(m,prop,default),'Data':data},size),prop)
cache={};parents={}
def material(src):
    if src=='M249_INTERFACE':return load('/Game/Weapons/M249/Surface20261108/Materials/MI_M249_CommonRail')
    if src in cache:return cache[src]
    data=inputs['materials'][src];asset=load(src);low=src.lower()
    if any(k in low for k in ('recess','titaniumtrim')):cache[src]=asset;return asset
    key=hashlib.sha256(src.encode()).hexdigest()[:10];basepath=data['base'];parentkey=hashlib.sha256(basepath.encode()).hexdigest()[:10]
    parent,new=clone(basepath,M+'/M_M249Part_'+parentkey)
    if new:
        for name in ('automatically_set_usage_in_editor','used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):parent.set_editor_property(name,False)
        # Current R01 graphs already preserve their source/region and rain layer.
        # For older single materials, change the dry input before any wet output.
        if 'R01_Roughness' not in data.get('scalars',{}):
            metal=('Stock_Graphite' in src or 'Stock_Steel' in src or 'Silencer' in src or 'Adapter' in src)
            if metal:
                for prop,default,code,size in [('BASE_COLOR',(.034,.035,.037),'float marks=smoothstep(.25,.65,min(Base.r,min(Base.g,Base.b)));return lerp(float3(.034,.035,.037),Base,max(.06,marks*.9));',3),('ROUGHNESS',.42,'return clamp(.42+(Base.r-.45)*.1,.36,.50);',1)]:
                    root=L.get_material_property_input_node(parent,getattr(u.MaterialProperty,'MP_'+prop))
                    existing_wet=isinstance(root,u.MaterialExpressionCustom) and 'Data' in str(root.get_editor_property('code'))
                    source=(L.get_inputs_for_material_expression(parent,root)[0] if existing_wet else original(parent,prop,default))
                    finish=custom(parent,'M249 dry '+prop,code,{'Base':source},size)
                    if existing_wet:wire(finish,root,'Base')
                    else:output(finish,prop)
            if not any(isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='WeaponWetness' for n in L.get_material_expressions(parent)):wet_layer(parent)
        compile_save(parent)
    if isinstance(asset,u.MaterialInstanceConstant):
        mi,newmi=clone(src,D+'/Materials/MI_M249Part_'+key);L.set_material_instance_parent(mi,parent)
        # Resolve inherited values before changing the parent to preserve source textures.
        for n,v in data.get('scalars',{}).items():L.set_material_instance_scalar_parameter_value(mi,n,v)
        for n,v in data.get('vectors',{}).items():L.set_material_instance_vector_parameter_value(mi,n,u.LinearColor(*v))
        for n,v in data.get('textures',{}).items():
            if v:L.set_material_instance_texture_parameter_value(mi,n,load(v))
        is_metal=any(k in low for k in ('_stock_metal_','_mount_','_accessory_','_muzzle_'))
        if is_metal:
            for n,v in {'R01_Roughness':.40 if '_muzzle_' in low else .42,'R01_GrainRoughness':.012,'R01_VariationRoughness':.005,'R01_SourceRoughnessWeight':.08,'R01_ColorWeight':.90,'PKM_MicroScratchStrength':0.}.items():
                if n in data.get('scalars',{}):L.set_material_instance_scalar_parameter_value(mi,n,v)
            if 'R01_FinishTint' in data.get('vectors',{}):L.set_material_instance_vector_parameter_value(mi,'R01_FinishTint',u.LinearColor(.034,.035,.037,1))
        L.update_material_instance(mi);result=save(mi)
    else:result=parent
    report['materials'][src]=result.get_path_name();record();cache[src]=result;return result
cv='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(cv);u.SystemLibrary.execute_console_command(None,cv+' 0')
try:
    for key,spec in recipe['parts'].items():
        dst=D+'/Meshes/SM_M249_'+key;owned(dst)
        if dst in report['saved'] and key in report['meshes']:continue
        mats={name:material(src) for name,src in spec['materials'].items()}
        task=u.AssetImportTask();task.filename=str(r/'Exports'/('SM_M249_'+key+'.fbx'));task.destination_path=D+'/Meshes';task.destination_name='SM_M249_'+key;task.automated=True;task.replace_existing=True;task.save=False
        opt=u.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.automated_import_should_detect_type=False
        opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.generate_lightmap_u_vs=False;opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;task.options=opt
        resume=dst in report.get('pending_import',[]) and disk(dst).exists()
        if dst not in report.setdefault('pending_import',[]):report['pending_import'].append(dst)
        record()
        if not resume:A.import_asset_tasks([task])
        mesh=load(dst);slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            name=str(slot.get_editor_property('imported_material_slot_name'))
            if name not in mats:name=str(slot.material_slot_name)
            if name not in mats:raise RuntimeError('Material slot '+key+' '+name)
            slot.material_interface=mats[name];slots[i]=slot
        mesh.set_editor_property('static_materials',slots)
        for name,pos in spec['sockets'].items():
            socket=mesh.find_socket(name)
            if not socket:socket=u.new_object(u.StaticMeshSocket,outer=mesh);socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
            socket.set_editor_property('relative_location',u.Vector(*pos))
        u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh);save(mesh)
        report['pending_import']=[q for q in report['pending_import'] if q!=dst]
        report['meshes'][key]=dict(path=dst,slots=[dict(slot=str(s.material_slot_name),material=s.material_interface.get_path_name()) for s in slots]);record()
        print('M249_COMMON_PART_SAVED',key,flush=True)
        gc.collect()
finally:u.SystemLibrary.execute_console_command(None,cv+' '+str(previous))
for family in ('vertical','canted','prism','angled'):
    dst=D+'/Profiles/DA_M249_'+family;owned(dst)
    if disk(dst).exists():profile=load(dst)
    else:
        factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
        profile=A.create_asset('DA_M249_'+family,D+'/Profiles',u.WeaponGripProfile,factory)
    if not profile.set_shared_clips_from_json(gzip.decompress((r/(family+'.json.gz')).read_bytes()).decode()):raise RuntimeError('Grip profile '+family)
    save(profile);report['profiles'][family]=dst;record();print('M249_GRIP_SAVED',family,flush=True)
dst=D+'/Audio/S_M249_Suppressed';owned(dst)
t=u.AssetImportTask();t.filename=str(r/'S_M249_Suppressed.wav');t.destination_path=D+'/Audio';t.destination_name='S_M249_Suppressed';t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t])
wave=load(dst);source=load('/Game/Weapons/M249/Audio/S_M249_Fire_01')
for name in ('volume','pitch','sound_class_object'):wave.set_editor_property(name,source.get_editor_property(name))
wave.set_editor_property('looping',False);wave.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE);wave.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM);save(wave)
report['complete']=True;record();print('M249_COMMON_PARTS_INSTALLED',len(report['meshes']),len(report['profiles']),flush=True)
