"""Save the blade-only vertical sutra mirror in the current editor or commandlet."""
from pathlib import Path
import json,runpy,shutil
import unreal as u
P=Path(__file__).resolve().parent;SOURCE=P.parent;ROOT=SOURCE.parents[1]
E,L=u.MaterialEditingLibrary,u.EditorAssetLibrary
replace=runpy.run_path(str(SOURCE/'rune_code.py'))['replace_jingang_branch']
new=(SOURCE/'jingang_emission.hlsl').read_text(encoding='utf-8')
catalog=json.loads((ROOT/'Content/ColdSteelData/xuanchi-zhenyue-modules.json').read_text(encoding='utf-8-sig'))
temporal=json.loads((ROOT/'Content/ColdSteelData/whirlwind-temporal-materials.json').read_text(encoding='utf-8-sig'))
paths={v for row in catalog['slots']['blade_1'].values() for v in row.get('materials',{}).values() if '/JingangRune20261006/Materials/' in v}
paths.update(temporal[p] for p in list(paths) if p in temporal)
receipt={'complete':False,'saved_assets':[],'operation':'Jingang source-strip V -> 1-V','runtime_tested':False}
def record():(P/'install-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for path in sorted(paths):
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Missing active Jingang blade material '+path)
    matches=[n for n in E.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionCustom) and '// Jingang mode 9:' in n.get_editor_property('code')]
    if len(matches)!=1:raise RuntimeError('Expected one Jingang branch in '+path)
    node=matches[0];old=node.get_editor_property('code')
    before=P/'Before'/(mat.get_name()+'.hlsl')
    if not before.exists():before.write_text(old,encoding='utf-8')
    package=ROOT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
    if not (P/'Before'/package.name).exists():shutil.copy2(package,P/'Before'/package.name)
    node.set_editor_property('code',replace(old,new))
    errors=E.recompile_material(mat)
    if errors:raise RuntimeError('Jingang blade material compilation failed '+str(errors))
    L.set_metadata_tag(mat,'JingangBladeOrientation','SourceStripVerticalMirror-20261006')
    if not u.EditorLoadingAndSavingUtils.save_packages([mat.get_outermost()],False):raise RuntimeError('Failed saving '+path)
    receipt['saved_assets'].append(mat.get_path_name());record()
if not paths:raise RuntimeError('No active Jingang blade materials in the module catalog')
receipt['complete']=True;record()
print('JINGANG_BLADE_VERTICAL_MIRROR_SAVED '+str(len(receipt['saved_assets'])),flush=True)
