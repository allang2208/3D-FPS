"""One equipment label material and a shatter-only copy of the shared glass impact."""
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent;BASE='/Game/Dungeons/FacilityDetailRepair20261010'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
def owned(path):
    if not E.does_asset_exist(path):return None
    a=u.load_asset(path)
    if E.get_metadata_tag(a,'FacilityDetailRepair.Owner')!='20261010':raise RuntimeError('Preserve unowned asset '+path)
    return a
def save(a):
    E.set_metadata_tag(a,'FacilityDetailRepair.Owner','20261010')
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def install():
    saved=[];path=BASE+'/Textures/T_FacilityDetail_Plates';tex=owned(path)
    if not tex:
        t=u.AssetImportTask();t.filename=str(ROOT/'Authored/Textures/T_FacilityDetail_Plates.png');t.destination_path,t.destination_name=path.rsplit('/',1)
        t.automated=True;t.save=False;t.factory=u.TextureFactory();A.import_asset_tasks([t]);tex=u.load_asset(path)
        tex.set_editor_property('srgb',True);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
        tex.set_editor_property('max_texture_size',2048);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD)
        tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP);save(tex)
    saved.append(path);path=BASE+'/Materials/M_FacilityDetail_Plates';mat=owned(path)
    if not mat:
        mat=A.create_asset(path.rsplit('/',1)[1],BASE+'/Materials',u.Material,u.MaterialFactoryNew());mat.set_editor_property('used_with_instanced_static_meshes',True)
        sample=L.create_material_expression(mat,u.MaterialExpressionTextureSample);sample.set_editor_property('texture',tex)
        slab=L.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels);slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        rough=L.create_material_expression(mat,u.MaterialExpressionConstant);rough.set_editor_property('r',.57)
        metal=L.create_material_expression(mat,u.MaterialExpressionConstant);metal.set_editor_property('r',.12)
        for src,out,pin,prop in ((sample,'RGB','BaseColor','MP_BASE_COLOR'),(rough,'','Roughness','MP_ROUGHNESS'),(metal,'','Metallic','MP_METALLIC')):
            L.connect_material_expressions(src,out,slab,pin);L.connect_material_property(src,out,getattr(u.MaterialProperty,prop))
        L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        if L.recompile_material(mat):raise RuntimeError('Label material compile failed')
        save(mat)
    saved.append(path);path=BASE+'/FX/NS_GlassShatter_NoMarks';system=owned(path)
    if not system:
        system=E.duplicate_asset('/Game/NiagaraExamples/FX_Weapons/Impacts/NS_Impact_Glass',path)
        if not system:raise RuntimeError('Shatter copy failed')
        # The active LightDecal version has BOTH a projected decal and a static
        # emitter-source glass-crack sprite. Disable renderers, not just spawning.
        removed=[]
        for name in ('NiagaraDecalRendererProperties_2','NiagaraSpriteRendererProperties_2'):
            renderer=u.load_object(None,path+'.NS_GlassShatter_NoMarks:LightDecal_2.'+name)
            if not renderer:raise RuntimeError('Missing glass mark renderer '+name)
            renderer.modify();renderer.set_editor_property('is_enabled',False);removed.append(renderer.get_path_name())
        if not u.RainAssetEditor.compile_rain(system):raise RuntimeError('Shatter compile failed')
        E.set_metadata_tag(system,'FacilityDetailRepair.RemovedRenderers',';'.join(removed));save(system)
    # A running editor may have constructed this CDO before the new package was
    # imported. Bind its preload now; the constructor supplies it on next launch.
    default=u.get_default_object(u.WardGlassBurst)
    for component in default.get_components_by_class(u.NiagaraComponent):
        if component.get_name()=='GlassGlints':component.set_asset(system)
    saved.append(path);return saved
