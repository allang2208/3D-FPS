"""Persist a single original-robe cloth binding using UE's editor utility."""
import unreal as u,json
from pathlib import Path
def repair_original_robe_cloth(mesh):
    path=mesh.get_path_name()
    cls=u.load_class(None,'/Script/ChaosClothAssetToolset.ChaosClothAssetToolset')
    if not cls:raise RuntimeError('Start the editor with -EnablePlugins=ChaosClothAssetToolset for cloth authoring')
    tool=u.get_default_object(cls)
    sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    sections=list(range(sub.get_num_sections(mesh,0)))
    slots=list(mesh.materials)
    target=next(i for i in sections if 'OriginalRobe' in str(slots[sub.get_lod_material_slot(mesh,0,i)].get_editor_property('imported_material_slot_name')))
    before={i:tool.call_method('GetSectionClothing',args=(path,0,i)) for i in sections}
    assets=list(mesh.get_editor_property('mesh_clothing_assets'))
    selected=next((a for a in assets if a.get_name()==before[target]),assets[-1])
    print('V05_CLOTH_INPUT '+json.dumps({'bindings':before,'selected':selected.get_name(),'asset_count':len(assets)}))
    mesh.modify();selected.modify()
    for index,name in before.items():
        if name and not tool.call_method('RemoveClothingFromSection',args=(path,0,index)):
            raise RuntimeError('Cannot detach old cloth section '+str(index))
    # The editor utility owns the cloth LOD mapping when unbinding/rebinding.
    mesh.call_method('SetMeshClothingAssets',args=([selected],))
    if not tool.call_method('AssignClothingToSection',args=(path,selected.get_name(),0,target,0)):
        raise RuntimeError('Original robe binding failed')
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Original robe save failed')
    after={i:tool.call_method('GetSectionClothing',args=(path,0,i)) for i in sections}
    report={'mesh':path,'before':before,'after':after,'original_robe_section':target,
        'clothing_assets_before':[a.get_name() for a in assets],
        'clothing_assets':[a.get_name() for a in mesh.get_editor_property('mesh_clothing_assets')],
        'render_sections':len(sections),'runtime_tested':False}
    Path('D:/FPS3D/FPSGAME/Saved/WitchV05-cloth-binding-repair.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    mesh=u.load_asset('/Game/Monsters/WitchMeshy/OriginalRobeV05/SK_Witch_Meshy')
    print(json.dumps(repair_original_robe_cloth(mesh)))
