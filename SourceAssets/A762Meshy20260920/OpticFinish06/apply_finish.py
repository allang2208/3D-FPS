"""A762 optic finishes: original semantic masks, actual receiver PBR, stable mesh paths."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent; P='/Game/Weapons/A762/OpticFinish06'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
src=json.loads((O.parent/'Accessories05/sources.json').read_text())
prior=json.loads((O/'before.json').read_text())
source_masks=json.loads((O/'source_masks.json').read_text())
reference='/Game/Weapons/A762/Refinement03/Materials/M_A762_UpperReceiver03'
ref=u.load_asset(reference)
color=L.get_material_default_vector_parameter_value(ref,'FinishColor')
metal=L.get_material_default_scalar_parameter_value(ref,'Metallic')
rough=L.get_material_default_scalar_parameter_value(ref,'RoughnessCenter')
finish=u.load_asset('/Game/Weapons/A762/Refinement03/Textures/T_A762_RebuiltFinish')
report={'status':'in_progress','reference':reference,'color':[color.r,color.g,color.b],'metallic':metal,'roughness_center':rough,'roughness_variation':.018,'uv':2,'physical_tile_m':[.05,.05],'meshes':{},'game_tested':False,'rendered':False}
overrides={}
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def clone(s,p):
    a=u.load_asset(p) if E.does_asset_exist(p) else E.duplicate_asset(s,p)
    if not a:raise RuntimeError('Duplicate failed '+p)
    return a
def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def link(a,p,b,i):
    if not L.connect_material_expressions(a,p,b,i):raise RuntimeError('Cannot connect '+i)
def write():
    (O/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def signature(m,name):
    prop=getattr(u.MaterialProperty,'MP_'+name);n=L.get_material_property_input_node(m,prop)
    return [n.get_name() if n else None,str(L.get_material_property_input_node_output_name(m,prop))]
for key,idx in [('holographic',0),('panoramic_red_dot',2),('prism_scope_2x',2),('lpvo_1_6x',2),('lpvo_ring',0)]:
    path='/Game/Weapons/A762/Accessories05/Meshes/SM_A762_'+key
    mesh=u.load_asset(path); slots=mesh.static_materials
    if S.get_num_uv_channels(mesh,0)<3:raise RuntimeError('Missing coating UV2 '+key)
    if key in ['prism_scope_2x','lpvo_1_6x','lpvo_ring']:
        if not any('ReceiverFinishMetalRegion' in x['colors'] for x in source_masks[key]):raise RuntimeError('Missing interior mask '+key)
    backup=clone(path,P+'/Before/SM_A762_'+key);save(backup)
    donor=src['meshes'][key]['materials'][idx]['path']
    matpath=P+'/Materials/M_A762_'+key
    m=clone(donor,matpath)
    if str(E.get_metadata_tag(m,'A762OpticFinishRevision'))!='06':
        protected={n:signature(m,n) for n in ['NORMAL','AMBIENT_OCCLUSION','OPACITY','OPACITY_MASK','EMISSIVE_COLOR']}
        blends={}
        for name in ['BASE_COLOR','METALLIC','ROUGHNESS','SPECULAR']:
            n=L.get_material_property_input_node(m,getattr(u.MaterialProperty,'MP_'+name))
            if not isinstance(n,u.MaterialExpressionLinearInterpolate):raise RuntimeError('Unexpected donor finish output '+key+' '+name)
            inputs=L.get_inputs_for_material_expression(m,n)
            if not isinstance(inputs[1],u.MaterialExpressionMaterialFunctionCall):raise RuntimeError('Donor finish has changed '+key)
            blends[name]=n
        bc=node(m,u.MaterialExpressionVectorParameter,parameter_name='A762CoatingColor',default_value=color)
        mt=node(m,u.MaterialExpressionScalarParameter,parameter_name='A762CoatingMetallic',default_value=metal)
        rc=node(m,u.MaterialExpressionScalarParameter,parameter_name='A762CoatingRoughness',default_value=rough)
        sp=node(m,u.MaterialExpressionScalarParameter,parameter_name='A762CoatingSpecular',default_value=.5)
        uv=node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=2,u_tiling=2.4,v_tiling=1.)
        tx=node(m,u.MaterialExpressionTextureSample,texture=finish,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
        link(uv,'',tx,'UVs')
        centered=node(m,u.MaterialExpressionAdd,const_b=-.5);link(tx,'R',centered,'A')
        amp=node(m,u.MaterialExpressionMultiply,const_b=.018);link(centered,'',amp,'A')
        rf=node(m,u.MaterialExpressionAdd);link(rc,'',rf,'A');link(amp,'',rf,'B')
        for name,n in [('BASE_COLOR',bc),('METALLIC',mt),('ROUGHNESS',rf),('SPECULAR',sp)]:
            # Replace only the donor coating input. Alpha retains original UV0
            # material identity, white-mark protection, and inner-wall vertex mask.
            link(n,'',blends[name],'B')
        # Remove disconnected M4 coating nodes, not the original optic shading.
        for n in list(L.get_material_expressions(m)):
            remove=False
            if isinstance(n,u.MaterialExpressionMaterialFunctionCall):
                f=n.get_editor_property('material_function');remove=bool(f and 'MF_PhongToMetalRoughness' in f.get_path_name())
            if isinstance(n,u.MaterialExpressionTextureSample):
                t=n.get_editor_property('texture');remove=bool(t and '/AttachmentFinish20260913/M4/' in t.get_path_name())
            if remove:L.delete_material_expression(m,n)
        for name,sig in protected.items():
            if signature(m,name)!=sig:raise RuntimeError('Protected optical/normal output changed '+key+' '+name)
        E.set_metadata_tag(m,'A762OpticFinishRevision','06')
        E.set_metadata_tag(m,'WeaponFinishReference',reference)
        E.set_metadata_tag(m,'WeaponFinishRegions','Original UV0 metallic + white mark protection; original vertex R inner-wall exclusion')
        E.set_metadata_tag(m,'WeaponFinishUV','UV2, 0.05 x 0.05 m; original UV0 structural normals retained')
        L.recompile_material(m)
    save(m)
    target='A762_'+key+'_'+str(idx)
    for i,s in enumerate(slots):
        if str(s.material_slot_name)==target:s.material_interface=m;slots[i]=s
    mesh.set_editor_property('static_materials',slots)
    E.set_metadata_tag(mesh,'WeaponFinishReference',reference)
    E.set_metadata_tag(mesh,'A762OpticFinishRevision','06');save(mesh)
    actual=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in mesh.static_materials]
    old={s['slot']:s['material'] for s in prior['meshes'][key]['slots']}
    for s in actual:
        expected=m.get_path_name() if s['slot']==target else old[s['slot']]
        if s['material']!=expected:raise RuntimeError('Material readback mismatch '+key+' '+s['slot'])
    report['meshes'][key]={'mesh':path,'backup':backup.get_path_name(),'slots':actual,'uv_channels':S.get_num_uv_channels(mesh,0),'protected_outputs':{n:signature(m,n) for n in ['NORMAL','AMBIENT_OCCLUSION','OPACITY_MASK','EMISSIVE_COLOR']}}
    overrides[key+':'+str(idx)]=m.get_path_name();write()
(O.parent/'Accessories05/finish_overrides.json').write_text(json.dumps(overrides,indent=2),encoding='utf-8')
report['status']='saved_and_binding_checked';write()
u.log('A762_OPTIC_FINISH06_SAVED_AND_BINDING_CHECKED: 4 optics + LPVO ring')
