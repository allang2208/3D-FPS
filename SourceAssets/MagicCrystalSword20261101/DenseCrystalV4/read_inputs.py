from pathlib import Path
import json
import unreal as u

P=Path(__file__).resolve().parent
E=u.EditorAssetLibrary; L=u.MaterialEditingLibrary
D='/Game/Weapons/FrostCrystalSword20260915/HighEnergyGlass20261102/'
targets=[D+'M_FrostCrystalSword_HighEnergyGlass',D+'M_FrostCrystalSword_HighEnergyGlass_Preview']
state={'pie':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),
       'dirty_targets':[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if x.get_path_name() in targets],
       'materials':[]}
for path in targets:
    m=E.load_asset(path)
    if not m: raise RuntimeError('Missing '+path)
    info={'path':path,'blend':str(m.get_editor_property('blend_mode')),
          'revision':E.get_metadata_tag(m,'HighEnergyGlassRevision'),
          'parameters':{},'custom':[]}
    for n in L.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionScalarParameter):
            info['parameters'][str(n.get_editor_property('parameter_name'))]=n.get_editor_property('default_value')
        if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc')).startswith('HighEnergyGlassV2'):
            info['custom'].append({'desc':str(n.get_editor_property('desc')),'code':str(n.get_editor_property('code'))})
    state['materials'].append(info)
(P/'current-inputs.json').write_text(json.dumps(state,indent=2)+'\n',encoding='utf8')
print(json.dumps({'pie':state['pie'],'dirty_targets':state['dirty_targets'],
                  'materials':[{'path':m['path'],'revision':m['revision'],'blend':m['blend'],'parameters':m['parameters']} for m in state['materials']]}))
