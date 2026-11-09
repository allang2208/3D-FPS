"""Save WS1.1 regional materials, fitted common optics, and current bindings."""
from pathlib import Path
import json,hashlib,unreal as u
r=Path(__file__).resolve().parent;p=r.parents[2]
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
D='/Game/Weapons/M249/Surface20261108';OPT='/Game/Weapons/M249/CommonOptics20261108'
inputs=json.loads((r/'current_assets.json').read_text());recipe=json.loads((r/'optic_recipe.json').read_text())
receipt_path=r/'install_receipt.json';old=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
R={'complete':False,'saved':old.get('saved',[]),'bindings':{},'optics':{},'material_recipes':{},'asset_hashes':old.get('asset_hashes',{}),'runtime_tested':False}
def record():receipt_path.write_text(json.dumps(R,indent=2),encoding='utf-8')
def disk(path):return p/'Content'/(path.removeprefix('/Game/').split('.')[0]+'.uasset')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing '+path)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    path=a.get_path_name().split('.')[0]
    if path not in R['saved']:R['saved'].append(path)
    R['asset_hashes'][path]=hashlib.sha256(disk(path).read_bytes()).hexdigest();record();return a
def clone(src,dst):
    if E.does_asset_exist(dst):
        if dst not in R['saved']:raise RuntimeError('Unowned destination retained '+dst)
        return load(dst)
    a=E.duplicate_asset(src,dst)
    if not a:raise RuntimeError('Clone failed '+src)
    return a
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE is running; preserve loaded assets')
dirty={x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(x.startswith('/Game/Weapons/M249/') for x in dirty):raise RuntimeError('Unsaved M249 packages retained')
for path,sha in inputs['hashes'].items():
    if path in dirty:raise RuntimeError('Unsaved source retained '+path)
    if hashlib.sha256(disk(path).read_bytes()).hexdigest()!=R['asset_hashes'].get(path,sha):raise RuntimeError('Concurrent source change retained '+path)
record()
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(src,dest,pin):
    n,out=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_expressions(n,out,dest,pin):raise RuntimeError('Material wire '+pin)
def output(src,prop):
    n,out=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_property(n,out,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Material output '+prop)
def custom(m,name,code,pins,size):
    n=node(m,u.MaterialExpressionCustom,description=name,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
    arr=[]
    for key in pins:
        item=u.CustomInput();item.set_editor_property('input_name',key);arr.append(item)
    n.set_editor_property('inputs',arr)
    for key,src in pins.items():wire(src,n,key)
    return n
def compile_save(m):
    errors=[str(x) for x in (L.recompile_material(m) or [])]
    if errors:raise RuntimeError('Material compilation '+str(errors[:4]))
    return save(m)
T={k:load('/Game/Weapons/M249/Textures/T_M249_'+k) for k in ('Color','ORM','Normal')}
masters={}
for static in (False,True):
    path=D+'/Master/M_M249RegionalSurface'+('_Static' if static else '')
    m=clone('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface',path)
    if E.get_metadata_tag(m,'M249SurfaceGraph')!='WS11_Regional_20261108':
        expr=L.get_material_expressions(m)
        params={str(n.get_editor_property('parameter_name')):n for n in expr if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter,u.MaterialExpressionTextureSampleParameter2D))}
        cs={str(n.get_editor_property('description')):n for n in expr if isinstance(n,u.MaterialExpressionCustom)}
        orm=node(m,u.MaterialExpressionTextureSampleParameter2D,parameter_name='SourceORM',texture=T['ORM'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS,group='M249 Source')
        poly=node(m,u.MaterialExpressionVectorParameter,parameter_name='PolymerColor',default_value=u.LinearColor(.019,.019,.018,1),group='M249 Finish')
        pr=node(m,u.MaterialExpressionScalarParameter,parameter_name='PolymerRoughness',default_value=.55,group='M249 Finish')
        identity=custom(m,'M249 material identity','return smoothstep(.2,.8,Mask);',{'Mask':(orm,'B')},1)
        region=custom(m,'M249 regional finish','return float4(lerp(Poly,Steel,Metal),lerp(PolyR,SteelR,Metal));',{'Poly':(poly,'RGB'),'Steel':(params['FinishColor'],'RGB'),'Metal':identity,'PolyR':pr,'SteelR':params['Roughness']},4)
        rgb=node(m,u.MaterialExpressionComponentMask,r=True,g=True,b=True);wire(region,rgb,'')
        rough=node(m,u.MaterialExpressionComponentMask,a=True);wire(region,rough,'')
        wire(rgb,cs['WS_ColorRough'],'Finish');wire(rough,cs['WS_ColorRough'],'Rough');wire((orm,'G'),cs['WS_ColorRough'],'SrcR')
        # Use source AO exactly once. Do not invent UV1 wear masks or change the
        # hand's UV channels. The original narrow edge artwork remains in Src.
        mask=custom(m,'M249 UV0 source cavity','float ao=saturate(AO);return float4(0,1-ao,ao,ao);',{'AO':(orm,'R')},4)
        for key in ('WS_Wear','WS_ColorRough','WS_MetalAO'):wire(mask,cs[key],'Mask')
        markings=custom(m,'M249 original markings','float white=smoothstep(.2,.6,min(Src.r,min(Src.g,Src.b)));float chroma=max(Src.r,max(Src.g,Src.b))-min(Src.r,min(Src.g,Src.b));return max(BaseWeight,max(white*.8,smoothstep(.012,.035,chroma)*.8));',{'Src':(params['SourceBaseColor'],'RGB'),'BaseWeight':params['SourceColorWeight']},1)
        wire(markings,cs['WS_ColorRough'],'SrcW');wire(identity,cs['WS_MetalAO'],'Metal');wire(identity,cs['WS_MetalAO'],'EdgeMetal')
        output((params['SourceBaseColor'],'A'),'OPACITY_MASK')
        m.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED);m.set_editor_property('two_sided',True)
        E.set_metadata_tag(m,'M249SurfaceGraph','WS11_Regional_20261108')
    for key,value in {'automatically_set_usage_in_editor':False,'used_with_skeletal_mesh':not static,'used_with_morph_targets':not static,'used_with_clothing':False}.items():m.set_editor_property(key,value)
    masters[static]=compile_save(m)
scalars={'SourceColorWeight':.16,'SourceRoughnessWeight':.08,'SourceRoughnessPivot':.5,'GrainTileCm':2.,'GrainRoughness':.012,'MottleRoughness':.005,'MottleColor':0.,'Stipple':0.,'EdgeWear':.025,'EdgeHighlight':.06,'EdgeRoughness':.34,'CavityDarken':.025,'CavityRoughness':.018,'ScratchAmount':0.,'HandlingPolish':0.,'AOStrength':.6,'MaskUVChannel':0.,'WeaponWetness':0.,'Specular':.5,'PolymerRoughness':.55}
instances={};binding_map={'skeletal':{},'static':{}}
def instance(slot,static):
    cache=(slot,static)
    if cache in instances:return instances[cache]
    short=slot.removeprefix('M249_');path=D+'/Materials/MI_M249_'+short+('_Static' if static else '')
    m=clone('/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanSatinSteel',path);L.set_material_instance_parent(m,masters[static])
    rough=.40 if any(k in slot for k in ('Barrel','Muzzle','Handle','Tray','Trigger')) else .44 if 'Optical' in slot else .42
    values=dict(scalars,Roughness=rough)
    if 'Box' in slot:values.update(GrainRoughness=.009,MottleRoughness=.004)
    for key,value in values.items():L.set_material_instance_scalar_parameter_value(m,key,value)
    for key,value in {'FinishColor':(.034,.035,.037),'PolymerColor':(.019,.019,.018),'EdgeColor':(.085,.088,.092)}.items():L.set_material_instance_vector_parameter_value(m,key,u.LinearColor(*value,1))
    for key,tex in {'SourceBaseColor':T['Color'],'SourceORM':T['ORM'],'SurfaceNormal':T['Normal']}.items():L.set_material_instance_texture_parameter_value(m,key,tex)
    L.update_material_instance(m);save(m);instances[cache]=m
    binding_map['static' if static else 'skeletal'][slot]=path
    R['material_recipes'][path]={'parent':m.parent.get_path_name(),'scalars':values,'source_normal':T['Normal'].get_path_name(),'uv':0,'identity':'original ORM B; nonmetal and metal endpoints','wetness':'one inherited WS1 layer'}
    return m
for path,rows in inputs['meshes'].items():
    if not path.startswith('/Game/Weapons/M249/'):continue
    mesh=load(path);static=isinstance(mesh,u.StaticMesh);prop='static_materials' if static else 'materials';slots=list(mesh.get_editor_property(prop));changed=False
    for i,s in enumerate(slots):
        name=str(s.material_slot_name)
        if rows[i]['material'].split('.')[0] not in ('/Game/Weapons/M249/Materials/M_M249_Surface','/Game/Weapons/M249/Materials/M_M249_OpticHousing'):continue
        s.material_interface=instance(name,static);slots[i]=s;changed=True
    if changed:
        mesh.set_editor_property(prop,slots);save(mesh)
        R['bindings'][path]=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in mesh.get_editor_property(prop)];record()
(r/'material_bindings.json').write_text(json.dumps(binding_map,indent=2))
# Independent shared optic variants preserve each original window, markings,
# matte interior and native UVs, with the M249 metal response on their housings.
optic_mats={}
for key,row in recipe['assets'].items():
    mesh=clone(row['source'],row['target'])
    for i,s in enumerate(mesh.static_materials):
        src=s.material_interface;source=src.get_path_name()
        if '/M24/FinishUnified20261103/Materials/' not in source:continue
        if source not in optic_mats:
            tag=hashlib.sha1(source.encode()).hexdigest()[:9];master=clone(src.get_base_material().get_path_name(),D+'/Master/M_M249Optic_'+tag)
            for name in ('automatically_set_usage_in_editor','used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):master.set_editor_property(name,False)
            for n in L.get_material_expressions(master):
                if isinstance(n,u.MaterialExpressionCustom) and 'M24 EOTH' in str(n.get_editor_property('description')):
                    code=n.get_editor_property('code').replace('float3(.026,.029,.032)','float3(.034,.035,.037)').replace('lerp(.59,.48,','lerp(.55,.42,')
                    n.set_editor_property('code',code)
            compile_save(master)
            mi=clone(source,D+'/Materials/MI_M249Optic_'+tag);L.set_material_instance_parent(mi,master)
            available={str(x) for x in L.get_scalar_parameter_names(mi)}
            changes={'R01_Roughness':.42,'R01_Grain':.012,'R01_Variation':.005,'R01_PolymerRoughness':.55,'Roughness':.42,'GrainRoughness':.012,'MottleRoughness':.005,'DryRoughness':.42}
            for name,value in changes.items():
                if name in available:L.set_material_instance_scalar_parameter_value(mi,name,value)
            available_v={str(x) for x in L.get_vector_parameter_names(mi)}
            for name,value in {'R01_ToneScale':(.034/.058,.035/.058,.037/.058),'R01_PolymerTint':(.019,.019,.018),'FinishColor':(.034,.035,.037),'SurfaceTint':(.034,.035,.037)}.items():
                if name in available_v:L.set_material_instance_vector_parameter_value(mi,name,u.LinearColor(*value,1))
            L.update_material_instance(mi);optic_mats[source]=save(mi)
        mesh.set_material(i,optic_mats[source])
    save(mesh);R['optics'][key]={'asset':mesh.get_path_name(),'source':row['source'],'sockets':row['sockets'],'materials':[s.material_interface.get_path_name() for s in mesh.static_materials]};record()
# Low forward rail for the two long bases; ordinary optical units stay on the
# original rail. No shared source mesh or optic size is changed.
railpath=recipe['rail']['target']
if not E.does_asset_exist(railpath):
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opts.import_mesh=True;opts.import_as_skeletal=False;opts.import_materials=False;opts.import_textures=False;opts.import_animations=False
    opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.auto_generate_collision=False;opts.static_mesh_import_data.generate_lightmap_u_vs=False
    opts.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=str(r/'SM_M249_CommonRail.fbx');task.destination_path=OPT;task.destination_name='SM_M249_CommonRail';task.automated=True;task.save=False;task.factory=u.FbxFactory();task.options=opts
    flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
    try:A.import_asset_tasks([task])
    finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
rail=load(railpath);railmaster=clone('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface',D+'/Master/M_M249RailSurface')
for name in ('automatically_set_usage_in_editor','used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):railmaster.set_editor_property(name,False)
compile_save(railmaster);mi=clone('/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanAnodized',D+'/Materials/MI_M249_CommonRail');L.set_material_instance_parent(mi,railmaster)
for name,value in {'Roughness':.44,'GrainRoughness':.012,'MottleRoughness':.005,'EdgeWear':.025,'ScratchAmount':0.}.items():L.set_material_instance_scalar_parameter_value(mi,name,value)
L.update_material_instance(mi);save(mi)
for i in range(len(rail.static_materials)):rail.set_material(i,mi)
u.ASH12AttachmentAssetTools.disable_runtime_fast_build(rail);save(rail)
feed_finish={};exec(compile((r.parent/'Finish29/bindings.py').read_text(),str(r.parent/'Finish29/bindings.py'),'exec'),feed_finish)
R['asset_hashes'].update(feed_finish['restore']())
R['complete']=True;record();print('M249_SURFACE_AND_COMMON_OPTICS_SAVED',len(R['saved']),flush=True)
