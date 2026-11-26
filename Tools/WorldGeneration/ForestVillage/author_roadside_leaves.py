"""Blend four licensed Quixel leaf decals directly into the village terrain materials."""
from pathlib import Path
import os
import unreal as u
import author_trail_cover_materials as art

folder='/Game/ForestPathStudy/VillageRegion/WoodlandDressing/Leaves'
ed=u.MaterialEditingLibrary
lib=u.EditorAssetLibrary

def textures(src,field_only=False,*,reuse_surface=False):
    lib.make_directory(folder)
    requested=[('T_ShoulderLeafField','GRAYSCALE',False)]
    if not field_only:requested+= [('T_ShoulderLeafColor','DEFAULT',True),('T_ShoulderLeafSurface','MASKS',False)]
    for name,kind,srgb in requested:
        if reuse_surface and name=='T_ShoulderLeafSurface' and lib.does_asset_exist(folder+'/'+name):continue
        file=(src/'Dressing'/('T_ShoulderLeafField.png') if name=='T_ShoulderLeafField' and (src/'Dressing/T_ShoulderLeafField.png').exists() else src/(name+'.png'))
        task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
        task.replace_existing=True;task.automated=True;art.tools.import_asset_tasks([task])
        tex=art.asset(folder+'/'+name)
        if not tex:raise RuntimeError(str(file))
        tex.set_editor_property('srgb',srgb);tex.set_editor_property('compression_settings',getattr(u.TextureCompressionSettings,'TC_'+kind))
        for k in ('address_x','address_y'):tex.set_editor_property(k,u.TextureAddress.TA_CLAMP)
        if name.endswith('Color'):tex.set_editor_property('compression_no_alpha',False)
        art.save(tex)

def configure(mat,shade,root):
    from author_continuous_meadow import tagged
    sources=art.inputs(mat,shade)
    previous=art.inputs(mat,root).get('Roughness')
    consumer=shade if previous==shade else root
    if consumer==shade:previous=sources['GroundRoughness']
    if previous:
        pin='Roughness' if isinstance(previous,u.MaterialExpressionBreakMaterialAttributes) else str(ed.get_input_node_output_name_for_material_expression(consumer,previous) or '')
    else:
        previous=tagged(mat,u.MaterialExpressionConstant,'Road litter original roughness');previous.set_editor_property('r',.5);pin=''
    inputs=list(shade.get_editor_property('inputs'))
    for name in ('GroundRoughness','LeafField','LeafColor','LeafSurface'):
        if not any(str(k.get_editor_property('input_name'))==name for k in inputs):
            k=u.CustomInput();k.set_editor_property('input_name',name);inputs.append(k)
    shade.set_editor_property('inputs',inputs)
    outputs=list(shade.get_editor_property('additional_outputs'))
    if not any(str(k.get_editor_property('output_name'))=='LitterRoughness' for k in outputs):
        k=u.CustomOutput();k.set_editor_property('output_name','LitterRoughness')
        k.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1);outputs.append(k)
        shade.set_editor_property('additional_outputs',outputs)
    art.wire(previous,pin,shade,'GroundRoughness')
    for name,suffix,kind in [('LeafField','Field','LINEAR_GRAYSCALE'),('LeafColor','Color','COLOR'),('LeafSurface','Surface','MASKS')]:
        obj=tagged(mat,u.MaterialExpressionTextureObject,'Road litter '+suffix)
        obj.set_editor_property('texture',art.asset(folder+'/T_ShoulderLeaf'+suffix))
        obj.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind));art.wire(obj,'',shade,name)
    base=Path(__file__).with_name('continuous_meadow.ush').read_text(encoding='utf-8-sig')
    if base.count('return GroundColor;')!=1:raise RuntimeError('Missing meadow compositing output')
    code=base.replace('return GroundColor;',Path(__file__).with_name('roadside_leaves.ush').read_text(encoding='utf-8-sig'))
    if lib.does_asset_exist('/Game/ForestPathStudy/VillageRegion/CliffExposure/T_CliffField'):
        from author_cliff_exposure import wire_exposure
        code=wire_exposure(mat,shade,code)
    shade.set_editor_property('code',code);art.wire(shade,'LitterRoughness',root,'Roughness')

def install(src=None,*,reuse_surface=False):
    if src is None:
        from landscape_themes import preset
        src=art.src.parent/preset('RoadLandscape')['resources']['leaf_source']
    textures(src,reuse_surface=reuse_surface)
    for path in (art.ref+'/M_ForestReferenceMesh',art.dest+'/M_ForestVillageLandscape'):
        m=art.asset(path);nodes=ed.get_material_expressions(m)
        shade=next(n for n in nodes if n.get_editor_property('desc')=='R26 continuous ground cover')
        root=next(n for n in nodes if isinstance(n,u.MaterialExpressionMakeMaterialAttributes) and art.inputs(m,n).get('BaseColor')==shade)
        configure(m,shade,root);art.compile_mat(m)

