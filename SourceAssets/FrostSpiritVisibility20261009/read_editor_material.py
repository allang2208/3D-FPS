from pathlib import Path
import hashlib,json
import unreal as u
P=Path(__file__).resolve().parent
ASSET='/Game/Weapons/FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit'
m=u.load_asset(ASSET)
E=u.MaterialEditingLibrary
row={'project_dir':u.Paths.project_dir(),'exists':bool(m),'dirty':False}
if m:
    row.update(asset=m.get_path_name(),revision=u.EditorAssetLibrary.get_metadata_tag(m,'RuneAppearanceRevision'),
               dirty=m.get_outermost().get_path_name() in {x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()})
    shader=next(n for n in E.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'))
    code=shader.get_editor_property('code')
    before=json.loads((P/'state_before.json').read_text(encoding='utf-8'))
    previous=next(n['code'] for n in before['nodes'] if n['class']=='MaterialExpressionCustom' and 'RuneTexture' in n.get('code',''))
    row.update(matches_before=code==previous,matches_authored=code==(P/'spirit_visible.hlsl').read_text(encoding='utf-8'),
               front=str(E.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL)))
(P/'editor_material_state.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
print(json.dumps(row))
