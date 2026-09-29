"""Save the full grey-metal liner on existing native meshes; no geometry import."""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1'
OUT=R/'FullMetal20260928'
DEST='/Game/Characters/ModularOutfit20260924/SteelGauntletV1/FullMetal20260928'
MATERIAL=DEST+'/M_GreyMetalLiner'
DESCRIPTION='手背、腕部与拇指采用平滑相连的钢质护面，其余四指配独立指节甲，整只手套覆以细密灰色金属护层。可单独穿戴并搭配上衣。'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()


def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())


def material():
    mat=u.load_asset(MATERIAL)
    if not mat:mat=A.create_asset('M_GreyMetalLiner',DEST,u.Material,u.MaterialFactoryNew())
    for node in list(L.get_material_expressions(mat)):L.delete_material_expression(mat,node)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_STATIC_MESH)
    uv=L.create_material_expression(mat,u.MaterialExpressionTextureCoordinate)
    uv.set_editor_property('u_tiling',.25/(.0007*8));uv.set_editor_property('v_tiling',.25/(.0006*8))
    for label in ('BaseColor','ORM','Normal'):
        name='T_GauntletGreyMail_'+label
        task=u.AssetImportTask();task.filename=str(OUT/'Textures'/(name+'.png'))
        task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
        A.import_asset_tasks([task]);tex=u.load_asset(DEST+'/'+name)
        if not tex:raise RuntimeError('Cannot import '+name)
        tex.set_editor_property('srgb',label=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if label=='Normal'
            else u.TextureCompressionSettings.TC_MASKS if label=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
        if label=='Normal':tex.set_editor_property('flip_green_channel',True)
        save(tex)
        node=L.create_material_expression(mat,u.MaterialExpressionTextureSampleParameter2D)
        node.set_editor_property('parameter_name',label);node.set_editor_property('texture',tex)
        node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if label=='Normal'
            else u.MaterialSamplerType.SAMPLERTYPE_MASKS if label=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        if not L.connect_material_expressions(uv,'',node,'UVs'):raise RuntimeError('Cannot connect metal UV')
        outputs=[('RGB',u.MaterialProperty.MP_BASE_COLOR)] if label=='BaseColor' else [('RGB',u.MaterialProperty.MP_NORMAL)] if label=='Normal' else [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]
        for channel,prop in outputs:
            if not L.connect_material_property(node,channel,prop):raise RuntimeError('Cannot connect '+label)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Metal liner compilation failed '+str(errors))
    save(mat);return mat


def bind_skeletal(mesh,metal):
    slots=list(mesh.get_editor_property('materials'))
    slots[0].set_editor_property('material_interface',metal)
    mesh.set_editor_property('materials',slots);save(mesh)


def main():
    receipt=json.loads((R/'saved-assets.json').read_text(encoding='utf-8'))
    targets=[v['mesh'] for v in receipt['profiles'].values()]+[receipt['pickup']]
    package_names={p.split('.')[0] for p in targets}
    dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
           if p.get_name() in package_names or p.get_name().startswith(DEST+'/')]
    if dirty:raise RuntimeError('Unsaved target gauntlet packages: '+', '.join(dirty))
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor.is_in_play_in_editor():raise RuntimeError('End PIE before saving the gauntlet material change.')
    before=OUT/'before-materials.json'
    if not before.exists():
        snapshot={}
        for path in targets:
            mesh=u.load_asset(path)
            slots=mesh.get_editor_property('materials' if isinstance(mesh,u.SkeletalMesh) else 'static_materials')
            snapshot[path]=[s.material_interface.get_path_name() if s.material_interface else '' for s in slots]
        write(before,snapshot)
    metal=material();saved=[]
    for path in targets:
        mesh=u.load_asset(path)
        if isinstance(mesh,u.SkeletalMesh):bind_skeletal(mesh,metal)
        else:
            # Existing pickup has liner slot zero and articulated steel slot one.
            mesh.set_material(0,metal);save(mesh)
        saved.append(path)
    receipt['liner_materials']={k:metal.get_path_name() for k in receipt['liner_materials']}
    receipt['liner_finish']='full grey flexible metal; no leather'
    write(R/'saved-assets.json',receipt)
    itempath=P/'Content/ColdSteelData/items.json'
    items=json.loads(itempath.read_text(encoding='utf-8-sig'))
    items['ue_steel_gauntlets']['desc']=DESCRIPTION
    write(itempath,items)
    published_path=R/'published.json'
    published=json.loads(published_path.read_text(encoding='utf-8'))
    published['liner_materials']=receipt['liner_materials']
    published['item_definition']['desc']=DESCRIPTION
    write(published_path,published)
    write(OUT/'install-receipt.json',dict(complete=True,material=metal.get_path_name(),saved_meshes=saved,
        native_profiles=len(receipt['profiles']),geometry_changed=False,runtime_tested=False,preview_rendered=False))
    print('STEEL_GREY_METAL_LINER_SAVED profiles='+str(len(receipt['profiles']))+' pickup=1')


if __name__=='__main__':main()
