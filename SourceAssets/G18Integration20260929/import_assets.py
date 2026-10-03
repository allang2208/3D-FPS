"""Headless G18 production import. Only new G18 packages and its profile keys."""
import ast,copy,hashlib,json,re,time
from pathlib import Path
import unreal as u
O=Path(__file__).parent;PROJECT=O.parents[1];DEST='/Game/Weapons/G18/Integrated20260929'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
receipt={'saved':[],'meshes':{},'animations':{},'materials':{},'attachments':{},'game_tested':False}
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Required G18 production dependency missing: '+path)
    return a
def save(a):
    if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outermost()],False):raise RuntimeError('Could not save '+a.get_path_name())
    if a.get_path_name() not in receipt['saved']:receipt['saved'].append(a.get_path_name())
    record();return a
def create(name,folder,cls,factory):
    return load(folder+'/'+name) if E.does_asset_exist(folder+'/'+name) else A.create_asset(name,folder,cls,factory)
def imported(file,folder,name,options=None):
    signature=hashlib.sha256(Path(file).read_bytes()).hexdigest();path=folder+'/'+name
    if E.does_asset_exist(path):
        a=load(path)
        if E.get_metadata_tag(a,'G18SourceSHA256')==signature:return a
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    if options:task.options=options;task.factory=u.FbxFactory()
    A.import_asset_tasks([task]);a=load(path);E.set_metadata_tag(a,'G18SourceSHA256',signature);save(a);return a

tree=ast.parse((PROJECT/'Tools/Weather/build_natural_weather.py').read_text(encoding='utf8'))
helpers={'unreal':u,'LIB':L};wanted={'node','wire','prop','scalar','constant','vector','custom'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted],type_ignores=[]),'G18 weather graph helpers','exec'),helpers)
node,custom,prop,scalar,constant,vector=[helpers[k] for k in ('node','custom','prop','scalar','constant','vector')]
textures={}
for file in sorted((O/'Textures').glob('*.png')):
    tex=imported(file,DEST+'/Textures',file.stem);normal='Normal' in file.stem;mask='Roughness' in file.stem or 'Metallic' in file.stem
    tex.srgb=not(normal or mask);tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS if mask else u.TextureCompressionSettings.TC_DEFAULT
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if normal else u.TextureGroup.TEXTUREGROUP_WEAPON
    # Retain the supplied DirectX tangent-space convention for Unreal.
    if normal:tex.set_editor_property('flip_green_channel',False)
    save(tex);textures[file.stem]=tex
def graph_finish(mat,base,rough,normal,metal,skeletal):
    wet=scalar(mat,'WeaponWetness',0);uv=node(mat,u.MaterialExpressionTextureCoordinate)
    beads=custom(mat,(PROJECT/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text(),dict(UV=uv,Wet=wet),4,'G18 rain beads')
    prop(custom(mat,'return Base*(1-Data.a*.07);',dict(Base=base,Data=beads),3),'BASE_COLOR')
    prop(custom(mat,'return lerp(lerp(Base,max(.085,Base*.70),Data.a),.065,Data.b*.8);',dict(Base=rough,Data=beads),1),'ROUGHNESS')
    prop(custom(mat,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));',dict(Base=normal,Data=beads),3),'NORMAL')
    if isinstance(metal,tuple):
        L.connect_material_property(metal[0],metal[1],u.MaterialProperty.MP_METALLIC)
    else:prop(metal,'METALLIC')
    mat.set_editor_property('used_with_skeletal_mesh',skeletal)
    if skeletal:L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    L.recompile_material(mat);save(mat);receipt['materials'][mat.get_path_name()]=mat.get_path_name()
body=create('M_G18_SourcePBR',DEST+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(body)
samples={}
for name,tex in textures.items():
    n=node(body,u.MaterialExpressionTextureSample);n.texture=tex
    n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if 'Normal' in name else u.MaterialSamplerType.SAMPLERTYPE_MASKS if 'Metallic' in name or 'Roughness' in name else u.MaterialSamplerType.SAMPLERTYPE_COLOR
    samples[name]=n
graph_finish(body,samples['T_G18_Base_color'],(samples['T_G18_Roughness'],'R'),samples['T_G18_Normal_DirectX'],(samples['T_G18_Metallic'],'R'),True)
E.set_metadata_tag(body,'Source','User g18.zip: original UV, base colour, metallic, roughness and DirectX normal');save(body)
finish=create('M_G18_AttachmentFinish',DEST+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(finish)
graph_finish(finish,vector(finish,(.017,.020,.024)),constant(finish,.44),vector(finish,(0,0,1)),constant(finish,.85),False)
wetmap={body.get_path_name():body,finish.get_path_name():finish}

flag='Interchange.FeatureFlags.Import.FBX';old_flag=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    profiles=json.loads((PROJECT/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))['profiles'];new_profiles={}
    for key,relative,profile in [('single','Single','M1911'),('r','Dual/r','M1911_r'),('l','Dual/l','M1911_l')]:
        folder=O/relative;auth=json.loads((folder/'authoring.json').read_text())
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
        opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
        opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        opt.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
        mesh=imported(folder/auth['mesh'],DEST+'/'+relative,Path(auth['mesh']).stem,opt)
        donor_key=next(k for k,v in profiles.items() if v.get('rig_profile')==profile)
        entry=copy.deepcopy(profiles[donor_key]);bare=load(entry['base'])
        skin={}
        for name,slot in zip(('UpperArm','Forearm','Hand'),bare.materials):skin[name]=slot.material_interface
        slots=list(mesh.materials);arm_ids=[]
        for i,slot in enumerate(slots):
            name=str(slot.material_slot_name)
            if 'Manny' in name:
                arm_ids.append(i);part=next((p for p in skin if p.lower() in name.lower()),'Hand');slot.material_interface=skin[part]
            else:slot.material_interface=body
            slots[i]=slot
        mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None)
        for lod in range(S.get_lod_count(mesh)):
            settings=S.get_lod_build_settings(mesh,lod);settings.use_full_precision_u_vs=True;S.set_lod_build_settings(mesh,lod,settings)
        E.set_metadata_tag(mesh,'SourceAttribution','User-provided g18.zip; source licence not bundled; local project use only. Native V7 arms use existing project provenance.')
        save(mesh);save(mesh.skeleton)
        entry.update(native_bare_arms=True,hide_source_materials=arm_ids)
        entry.pop('original_gloved_source',None)
        new_profiles[mesh.get_path_name()]=entry
        receipt['meshes'][key]={'asset':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'arm_materials':arm_ids,'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}}
        for kind,clip in auth['clips'].items():
            file=folder/clip['file'];opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
            opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton
            opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
            opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
            a=imported(file,DEST+'/'+relative+'/Animations',file.stem,opt)
            a.set_editor_property('bone_compression_settings',load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
            save(a);receipt['animations'][key+'/'+kind]={'asset':a.get_path_name(),'duration':a.get_play_length()}
        record();print('G18_FAMILY_SAVED',key,flush=True)

    parts=json.loads((O/'attachment_authoring.json').read_text());material_cache={}
    def own_finish(source):
        path=source.get_path_name()
        if path in material_cache:return material_cache[path]
        base=source
        while isinstance(base,u.MaterialInstance):base=base.get_editor_property('parent')
        # Preserve optical and translucent slots verbatim; only opaque housing
        # gets a weapon-specific finish, with original structure/normal graphs.
        if base.blend_mode not in (u.BlendMode.BLEND_OPAQUE,u.BlendMode.BLEND_MASKED):return source
        name='M_G18_Finish_'+hashlib.sha1(path.encode()).hexdigest()[:10]
        result_name=('MI_G18_Finish_' if isinstance(source,u.MaterialInstanceConstant) else 'M_G18_Finish_')+hashlib.sha1(path.encode()).hexdigest()[:10]
        if E.does_asset_exist(DEST+'/Materials/'+result_name):
            result=load(DEST+'/Materials/'+result_name)
            wetmap[result.get_path_name()]=result;material_cache[path]=result;return result
        mat=load(DEST+'/Materials/'+name) if E.does_asset_exist(DEST+'/Materials/'+name) else A.duplicate_asset(name,DEST+'/Materials',base)
        original=L.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR)
        output=L.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_BASE_COLOR)
        normal=L.get_material_property_input_node(mat,u.MaterialProperty.MP_NORMAL)
        nout=L.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_NORMAL)
        bc=custom(mat,'float l=dot(Source,float3(.2126,.7152,.0722)); return lerp(float3(.017,.020,.024)*(.75+l*3),Source,smoothstep(.55,.85,l));',dict(Source=(original,output) if original else vector(mat,(.017,.020,.024))),3,'G18 dark steel with source markings')
        graph_finish(mat,bc,constant(mat,.44),(normal,nout) if normal else vector(mat,(0,0,1)),constant(mat,.85),False)
        # Restore instance texture/switch values on a private instance when the
        # source normal graph depends on its parameters.
        result=mat
        if isinstance(source,u.MaterialInstanceConstant):
            name='MI_G18_Finish_'+hashlib.sha1(path.encode()).hexdigest()[:10]
            result=load(DEST+'/Materials/'+name) if E.does_asset_exist(DEST+'/Materials/'+name) else A.duplicate_asset(name,DEST+'/Materials',source)
            L.set_material_instance_parent(result,mat);L.update_material_instance(result);save(result)
        wetmap[result.get_path_name()]=result;material_cache[path]=result;return result
    for key,entry in parts.items():
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
        opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.generate_lightmap_u_vs=False
        opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        mesh=imported(entry['fbx'],DEST+'/Attachments','SM_G18_'+key,opt)
        old=load(entry['source_asset']) if entry['source_asset'] else None
        bindings={re.sub(r'[._]\d{3}$','',str(s.material_slot_name)):s.material_interface for s in old.static_materials} if old else {}
        aliases={'M_HoloBody':'Holosight','M_HoloReticle':'Red_Dot','M_Panoramic_Glass':'Panoramic_Glass','M_Panoramic_Reticle':'Panoramic_Reticle','M_Panoramic_Body':'Panoramic_Body'} if key in ('holographic','panoramic_red_dot') else {}
        slots=list(mesh.static_materials)
        for i,slot in enumerate(slots):
            name=re.sub(r'[._]\d{3}$','',str(slot.material_slot_name));source=bindings.get(aliases.get(name,name))
            if name in entry.get('material_overrides',{}):mat=load(entry['material_overrides'][name])
            elif name in ('M_G18_SourcePBR','M_G18_Magazine'):mat=body
            elif source:
                identity=(name+' '+source.get_path_name()).lower()
                mat=source if any(t in identity for t in ('glass','lens','reticle','emiss','rubber','recess','polymer','optical','tactical_laser','tactical_flashlight')) else own_finish(source)
            else:mat=finish
            slot.material_interface=mat;slots[i]=slot
        mesh.set_editor_property('static_materials',slots);save(mesh)
        receipt['attachments'][key]={'asset':mesh.get_path_name(),'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in slots}};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(old_flag))

for file in sorted((O/'Audio').glob('*.wav')):imported(file,DEST+'/Audio',file.stem)
cues={'MagOut':'/Game/Weapons/M4HK416Audio/S_HK416_MagOut','MagInsert':'/Game/Weapons/M4HK416Audio/S_HK416_MagInsert','MagSeat':'/Game/Weapons/M4HK416Audio/S_HK416_MagSeat',
    'Equip':'/Game/Weapons/M4AnimationAuditFinal/S_HK416_Equip','ChargePull':'/Game/Weapons/AKM/Audio/S_AKM_ChargePull',
    'ChargeRelease':'/Game/Weapons/M4AnimationAuditFinal/S_HK416_BoltRelease','DryClick':'/Game/Weapons/AKM/Audio/S_AKM_DryClick','CriticalHit':'/Game/Weapons/AKM/Audio/S_AKM_CriticalHit'}
for cue,source in cues.items():
    name='S_G18_'+cue;path=DEST+'/Audio/'+name
    a=load(path) if E.does_asset_exist(path) else A.duplicate_asset(name,DEST+'/Audio',load(source));save(a)
receipt['mechanical_audio_sources']=cues
factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeatherPresentationAssets)
for drum_name in ('M_G18_Drum50_PBR','M_G18_Drum50_Neck'):
    drum_mat=DEST.replace('/Integrated20260929','/Drum50_20261003')+'/Materials/'+drum_name
    if E.does_asset_exist(drum_mat):wetmap[drum_mat]=load(drum_mat)
library=create('DA_G18_WetMaterials',DEST,u.WeatherPresentationAssets,factory);library.set_editor_property('wet_materials',wetmap);save(library)
for file in [PROJECT/'Content/ColdSteelData/Icons/ue_g18.png']+list((PROJECT/'Content/ColdSteelData/AttachmentIcons20260913').glob('ue_g18_*.png')):
    folder='/Game/ColdSteelData/Icons' if file.name=='ue_g18.png' else DEST+'/Icons'
    tex=imported(file,folder,file.stem);tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;save(tex)

# Append only the new profile entries; retain current outfit recipes and their
# native M1911 arm references, whose arm bone binds are unchanged in this rig.
config=PROJECT/'Content/ColdSteelData/modular_outfits.json';text=config.read_text(encoding='utf-8-sig')
start=text.index('{',text.index('"profiles"'));data,size=json.JSONDecoder().raw_decode(text[start:]);end=start+size
data.update(new_profiles);replacement=json.dumps(data,ensure_ascii=False,indent=2)
if config.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Outfit catalog changed during G18 publication')
config.write_text(text[:start]+replacement+text[end:],encoding='utf8')
script=O/'publish_catalog.py';exec(compile(script.read_text(encoding='utf8'),str(script),'exec'),{'__file__':str(script),'__name__':'__main__'})
receipt['status']='imported_and_saved';receipt['profiles']=list(new_profiles);record()
print('G18_IMPORT_AND_SAVE_COMPLETE',flush=True)
