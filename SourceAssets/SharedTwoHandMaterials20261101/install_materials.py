"""Share the five established finishes with actual blade/head surfaces; retain rune graphs."""
from pathlib import Path
import json, shutil, runpy
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;REV='SharedTwoHandFinish20261101V1'
protect_blade_decorations=runpy.run_path(str(ROOT/'SourceAssets/ZhanmadaoDecorationPreservation20261110/decoration_material.py'))['apply_decoration_protection']
apply_zhanmadao_damascus=runpy.run_path(str(ROOT/'SourceAssets/ZhanmadaoDamascus20261111/materials.py'))['apply_if_installed']
apply_shared_damascus=runpy.run_path(str(P/'damascus_v3.py'))['apply_registered']
def apply_damascus(material):
    return apply_zhanmadao_damascus(material) or apply_shared_damascus(material)
inventory=json.loads((P/'surface-inventory.json').read_text(encoding='utf8'))
# Separate inlays, rune bands, energy cores and optical crystal remain authored materials.
exclude={'M_MeteorBronze','M_MeteorRuneBand','M_MeteorLavaCore','M_Chixiao_Brass_V1','M_Zhufeng_Brass_V1',
 'M_StarOath_FineInlay_PBRV3','M_StarOath_Optical_Crystal','M_StarOath_Rune_Energy',
 'M_FinalToll_Rune_Energy','M_FinalToll_FineInlay_PBRV3','M_AzureRunesword'}
paths=[p for p in inventory['materials'] if p.rsplit('.',1)[-1] not in exclude]
paths.extend(['/Game/Weapons/RuneboundWarhammer20261022/SwiftManaRuneV1/M_RuneboundSwiftRuneSurface.M_RuneboundSwiftRuneSurface',
 '/Game/Weapons/RuneboundWarhammer20261022/DestructionRedImpactV2/M_RuneboundDestructionRuneSurface.M_RuneboundDestructionRuneSurface'])
if u.EditorLevelLibrary.get_pie_worlds(False):raise RuntimeError('PIE running; preserve the current session')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_path_name() in [p.split('.')[0] for p in paths]:raise RuntimeError('Unsaved target '+package.get_path_name())
install_common_graph=runpy.run_path(str(P/'common_finish_graph.py'))['install']
texture=u.load_asset('/Game/Weapons/AzureRunesword20260913/MeteoricIronRefinement20261101/T_MeteoricCrystalFieldV2')
if not texture:raise RuntimeError('Meteor crystal field missing')
saved=[]
for path in paths:
    m=u.load_asset(path)
    if E.get_metadata_tag(m,'SharedTwoHandFinishRevision')==REV:
        protected=protect_blade_decorations(m)
        upgraded=apply_damascus(m)
        if protected or upgraded:
            errors=L.recompile_material(m)
            if errors:raise RuntimeError('Blade decoration shader compilation '+str(errors))
            if not E.save_loaded_asset(m,False):raise RuntimeError('Save '+path)
        saved.append({'asset':path,'already_current':True});continue
    if any(isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='BladeFinishMode' for n in L.get_material_expressions(m)):
        raise RuntimeError('Unexpected existing finish on '+path)
    disk=ROOT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
    backup=P/'BeforeAssets'/disk.relative_to(ROOT/'Content');backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(disk,backup)
    install_common_graph(m, texture)
    protect_blade_decorations(m)
    apply_damascus(m)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Shader compilation '+path+' '+str(errors))
    E.set_metadata_tag(m,'SharedTwoHandFinishRevision',REV)
    if not E.save_loaded_asset(m,False):raise RuntimeError('Save '+path)
    saved.append({'asset':path,'saved':True,'emission_preserved':True,'compile_errors':list(errors)})
    print('SHARED_FINISH_SAVED',len(saved),len(paths),path)
(P/'material-receipt.json').write_text(json.dumps({'revision':REV,'materials':saved,'protected_materials':sorted(exclude)},indent=2)+'\n',encoding='utf8')
print('SHARED_TWO_HAND_FINISH_COMPLETE',len(saved))
