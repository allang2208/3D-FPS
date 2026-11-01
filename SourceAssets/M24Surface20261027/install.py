"""Save the M24 regional WS1.1 finish and Palma-style game attachment.
Preserves the accepted V9 mesh topology, skeleton, morphs and all animations.
"""
import unreal as u,json,runpy
from pathlib import Path
O=Path(__file__).resolve().parent;D='/Game/Weapons/M24/Surface20261027';N='/Game/Weapons/M24/CustomScope20261026'
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()
R={'complete':False,'saved':[],'materials':{},'meshes':{},'runtime_tested':False}
def record():(O/'install_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
def load(p):
    a=u.load_asset(p)
    if not a:raise RuntimeError('Missing '+p)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    p=a.get_path_name()
    if p not in R['saved']:R['saved'].append(p)
    record();return a
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(D) for p in dirty):raise RuntimeError('M24 surface assets have unsaved edits; retained without overwriting')
runpy.run_path(str(O/'read_assets.py'))
inputs=json.loads((O/'current_assets.json').read_text())
if any(p in dirty for p in inputs['meshes']):raise RuntimeError('M24 source mesh has unsaved edits')

def texture(name,kind):
    t=u.AssetImportTask();t.filename=str(O/'Textures'/(name+'.png'));t.destination_path=D+'/Textures';t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);a=load(t.destination_path+'/'+name)
    a.srgb=False;a.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if kind=='normal' else u.TextureCompressionSettings.TC_MASKS
    a.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind=='normal' else u.TextureGroup.TEXTUREGROUP_WEAPON
    if kind=='normal':a.flip_green_channel=True
    save(a);return a
T={g:{k:texture('T_M24_'+g+'_'+suffix,kind) for k,suffix,kind in [('normal','Refined_N','normal'),('region','Regions','mask'),('mask','SurfaceMask','mask')]} for g in ('Body','Scope')}

def regional_master(static):
    p=D+'/Materials/M_M24RegionalSurface'+('_Static' if static else '')
    m=load(p) if E.does_asset_exist(p) else E.duplicate_asset('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface',p)
    def node(cls,**props):
        n=L.create_material_expression(m,cls)
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def wire(src,dest,pin):
        n,out=src if isinstance(src,tuple) else (src,'')
        if not L.connect_material_expressions(n,out,dest,pin):raise RuntimeError('Material wire '+pin)
    def custom(name,code,pins,size):
        n=node(u.MaterialExpressionCustom,description=name,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
        a=[]
        for name in pins:
            pin=u.CustomInput();pin.set_editor_property('input_name',name);a.append(pin)
        n.set_editor_property('inputs',a)
        for name,src in pins.items():wire(src,n,name)
        return n
    if E.get_metadata_tag(m,'M24SurfaceGraph')!='WS11_Regional_20261027':
        ex=L.get_material_expressions(m)
        params={str(n.get_editor_property('parameter_name')):n for n in ex if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter,u.MaterialExpressionTextureSampleParameter2D))}
        customs={str(n.get_editor_property('description')):n for n in ex if isinstance(n,u.MaterialExpressionCustom)}
        orm=node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='SourceORM',texture=load(N+'/Textures/T_M24_Body_ORM'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS,group='M24 Source')
        reg=node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='FinishRegions',texture=T['Body']['region'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS,group='M24 Source')
        poly=node(u.MaterialExpressionVectorParameter,parameter_name='PolymerColor',default_value=u.LinearColor(.019,.019,.018,1),group='M24 Finish')
        metal=custom('M24_MaterialIdentity','return smoothstep(.2,.8,Mask);',{'Mask':(orm,'B')},1)
        cr=custom('M24_RegionFinish','float rubber=smoothstep(.64,.70,Region.g); float3 dielectric=lerp(Poly,float3(.011,.011,.010),rubber); return float4(lerp(dielectric,MetalColor,Metal),lerp(Region.g,Region.r,Metal));',{'Region':(reg,'RGB'),'Poly':(poly,'RGB'),'MetalColor':(params['FinishColor'],'RGB'),'Metal':metal},4)
        rgb=node(u.MaterialExpressionComponentMask,r=True,g=True,b=True);wire(cr,rgb,'')
        rough=node(u.MaterialExpressionComponentMask,a=True);wire(cr,rough,'')
        wire(rgb,customs['WS_ColorRough'],'Finish');wire(rough,customs['WS_ColorRough'],'Rough')
        wire((orm,'G'),customs['WS_ColorRough'],'SrcR')
        preserve=custom('M24_SourceMarkings','float white=smoothstep(.20,.60,min(Src.r,min(Src.g,Src.b))); return saturate(max(max(BaseWeight,white*.82),Region.b));',{'Src':(params['SourceBaseColor'],'RGB'),'Region':(reg,'RGB'),'BaseWeight':params['SourceColorWeight']},1)
        wire(preserve,customs['WS_ColorRough'],'SrcW')
        wire(metal,customs['WS_MetalAO'],'Metal');wire(metal,customs['WS_MetalAO'],'EdgeMetal')
        E.set_metadata_tag(m,'M24SurfaceGraph','WS11_Regional_20261027')
    for prop,value in {'automatically_set_usage_in_editor':False,'used_with_skeletal_mesh':not static,'used_with_morph_targets':not static,'used_with_clothing':False}.items():m.set_editor_property(prop,value)
    errors=[str(x) for x in (L.recompile_material(m) or [])]
    if errors:raise RuntimeError('Material compile '+str(errors[:5]))
    save(m);return m
masters={False:regional_master(False),True:regional_master(True)}

def instance(group,static):
    name='MI_M24_'+group+('_Static' if static else '')
    p=D+'/Materials/'+name;m=load(p) if E.does_asset_exist(p) else A.create_asset(name,D+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(m,masters[static])
    scalars={'Metallic':1,'EdgeMetallic':1,'Roughness':.4,'SourceColorWeight':.20 if group=='Body' else .24,'SourceRoughnessWeight':.08,'SourceRoughnessPivot':.5,'GrainTileCm':2,'GrainRoughness':.012,'MottleRoughness':.005,'MottleColor':0,'Stipple':0,'EdgeWear':.025,'EdgeHighlight':.06,'EdgeRoughness':.34,'CavityDarken':.025,'CavityRoughness':.018,'ScratchAmount':0,'HandlingPolish':0,'AOStrength':.55,'MaskUVChannel':0,'WeaponWetness':0,'Specular':.5}
    for k,v in scalars.items():L.set_material_instance_scalar_parameter_value(m,k,v)
    for k,v in {'FinishColor':(.034,.036,.039),'PolymerColor':(.019,.019,.018),'EdgeColor':(.095,.100,.108)}.items():L.set_material_instance_vector_parameter_value(m,k,u.LinearColor(*v,1))
    tex={'SourceBaseColor':load(N+'/Textures/T_M24_'+group+'_BC'),'SourceORM':load(N+'/Textures/T_M24_'+group+'_ORM'),'SurfaceNormal':T[group]['normal'],'SurfaceMask':T[group]['mask'],'FinishRegions':T[group]['region']}
    for k,v in tex.items():L.set_material_instance_texture_parameter_value(m,k,v)
    L.update_material_instance(m);save(m);R['materials'][name]={'parent':m.parent.get_path_name(),'textures':{k:L.get_material_instance_texture_parameter_value(m,k).get_path_name() for k in tex},'roughness_regions':'region_recipe.json','scalars':scalars};record();return m
MI={(g,st):instance(g,st) for g in ('Body','Scope') for st in (False,True)}
for src,rows in inputs['meshes'].items():
    static=not src.endswith('SK_M24_HoldV9');name=src.rsplit('/',1)[1] if static else 'SK_M24_SurfaceV9';dst=D+'/'+name
    mesh=load(dst) if E.does_asset_exist(dst) else E.duplicate_asset(src,dst)
    slots=list(mesh.static_materials if static else mesh.materials)
    for i,s in enumerate(slots):
        group={'M24_Body':'Body','M24_Scope':'Scope'}.get(str(s.material_slot_name))
        if group:s.material_interface=MI[(group,static)];slots[i]=s
    mesh.set_editor_property('static_materials' if static else 'materials',slots)
    E.set_metadata_tag(mesh,'M24SurfaceRecipe','WS1.1 regional finish; retained V9 geometry/UV/weights/morphs and original glass; SourceAssets/M24Surface20261027')
    save(mesh);R['meshes'][name]={'asset':mesh.get_path_name(),'source':src,'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in slots]};record()

# A static-only copy retains the same standard wet graph without skeletal shader usages.
imaster_path=D+'/Materials/M_M24IronSurface'
imaster=load(imaster_path) if E.does_asset_exist(imaster_path) else E.duplicate_asset('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface',imaster_path)
for prop in ('automatically_set_usage_in_editor','used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing'):imaster.set_editor_property(prop,False)
err=[str(x) for x in (L.recompile_material(imaster) or [])]
if err:raise RuntimeError(str(err))
save(imaster)
ironmat={}
for key,preset,col,rough in [('M24_IronSatin','CleanSatinSteel',(.028,.029,.031),.39),('M24_IronInterior','Interior',(.006,.006,.006),.72),('M24_IronMarking','CleanPolymer',(.38,.38,.36),.48)]:
    path=D+'/Materials/MI_'+key
    m=load(path) if E.does_asset_exist(path) else E.duplicate_asset('/Game/Weapons/WeaponSurface/Presets/MI_WS_'+preset,path)
    L.set_material_instance_parent(m,imaster);L.set_material_instance_vector_parameter_value(m,'FinishColor',u.LinearColor(*col,1));L.set_material_instance_scalar_parameter_value(m,'Roughness',rough)
    L.set_material_instance_scalar_parameter_value(m,'Metallic',1 if key=='M24_IronSatin' else 0);L.set_material_instance_scalar_parameter_value(m,'EdgeMetallic',1 if key=='M24_IronSatin' else 0)
    L.update_material_instance(m);save(m);ironmat[key]=m
row=json.loads((O/'sight_authoring.json').read_text());flag='Interchange.FeatureFlags.Import.FBX';prev=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    t=u.AssetImportTask();t.filename=row['file'];t.destination_path=D;t.destination_name='SM_M24_m24_palma_iron';t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False;t.factory=u.FbxFactory();t.options=opt;A.import_asset_tasks([t])
    mesh=load(D+'/'+t.destination_name)
    for i,s in enumerate(mesh.static_materials):mesh.set_material(i,ironmat[str(s.material_slot_name)])
    for key,pos in row['sockets_ue_cm'].items():
        socket=mesh.find_socket(key)
        if not socket:socket=u.StaticMeshSocket(outer=mesh);socket.set_editor_property('socket_name',key);mesh.add_socket(socket)
        socket.set_editor_property('relative_location',u.Vector(*pos))
    sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    bs=sub.get_lod_build_settings(mesh,0);bs.recompute_normals=False;bs.recompute_tangents=True;bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True;sub.set_lod_build_settings(mesh,0,bs)
    u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
    save(mesh);R['meshes']['m24_palma_iron']={'asset':mesh.get_path_name(),'sockets':{k:[mesh.find_socket(k).relative_location.x,mesh.find_socket(k).relative_location.y,mesh.find_socket(k).relative_location.z] for k in row['sockets_ue_cm']},'reference':'TM9-1005-306-10 figs 2-22/2-23; visual game fit'}
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prev))
R['complete']=True;record();print('M24_SURFACE_AND_IRON_SAVED',len(R['saved']),flush=True)
