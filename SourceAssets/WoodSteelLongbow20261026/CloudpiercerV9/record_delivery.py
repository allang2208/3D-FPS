"""Record actual production/save/build results without running gameplay checks."""
from pathlib import Path
from datetime import datetime
import json

P = Path(__file__).parent
ROOT = Path('D:/FPS3D/FPSGAME')
load = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
assets = load(P / 'import-receipt.json')
catalog_path = sorted(P.glob('catalog-receipt-*.json'))[-1]
catalog = load(catalog_path)
build_paths = [
    P / 'build-FPSGAMEEditor.json',
    P / 'build-FPSGAME.json',
    P / 'HeaderRefresh/build-FPSGAMEEditor.json',
    P / 'HeaderRefresh2/build-FPSGAMEEditor.json',
]
builds = [{'receipt': str(path), **load(path)} for path in build_paths]
game_retry = P / 'HeaderRefresh2/build-FPSGAME.json'
if game_retry.exists():
    builds.append({'receipt': str(game_retry), **load(game_retry)})
build_complete = builds[-1]['target'] == 'FPSGAME' and builds[-1]['exit_code'] == 0
result = {
    'name': '穿云弓体', 'id': 'highland_cloudpiercer',
    'weapon': 'bow_woodsteel', 'slot': 'riser', 'tier': 'Special',
    'stats': catalog['option']['stats'],
    'model_source': str(P / 'HighlandLongbow_Cloudpiercer_Production.blend'),
    'asset_packages_saved': assets['complete'],
    'saved_packages': assets['saved'],
    'import_commandlet': load(P / 'import_assets-commandlet.json'),
    'catalog_receipt': str(catalog_path),
    'build_attempts': builds,
    'native_build_complete': build_complete,
    'build_blocker': None if build_complete else {
        'file': 'Source/FPSGAME/Skills/ElementalArrowTypes.h',
        'line': 24,
        'error': 'C2446: conditional expression mixes TCHAR string literal and NAME_None (EName).',
        'other_task_source_modified': False,
        'note': 'Initial Editor target succeeded. Game and later header-refresh builds did not finish successfully.'
    },
    'interactive_editor_launched': False, 'game_launched': False,
    'gameplay_tested': False, 'saved_at': datetime.now().isoformat(),
}
(P / 'completion.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

concept_path = P.parent / 'CloudpiercerConceptV8/design.json'
concept_raw = concept_path.read_bytes()
concept = json.loads(concept_raw)
backup = P / 'before-concept-design.json'
if not backup.exists():
    backup.write_bytes(concept_raw)
concept.update({
    'name_status': '正式', 'user_approved': True, 'tier': 'Special',
    'option_id': 'highland_cloudpiercer',
    'stage': 'integrated' if build_complete else 'assets_and_catalog_saved_build_blocked',
    'balance_values': catalog['option']['stats'],
    'interface_intent': '正式模型保留原 11 骨骨架、中央握持区、箭台、瞄具及上下弦挂点。',
    'production_source': str(P), 'runtime_integrated': True,
    'native_build_complete': build_complete, 'gameplay_tested': False,
    'production_receipt': str(P / 'completion.json'),
})
if concept_path.read_bytes() != concept_raw:
    raise RuntimeError('Preserving concurrent concept edit')
concept_path.write_text(json.dumps(concept, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

doc = ROOT / 'Docs/Weapons/wood-steel-longbow-20261026.md'
heading = '## 穿云弓体（2026-10-27，CloudpiercerV9）'
build_note = (
    '本批 Editor 与 Game 构建均完成。'
    if build_complete else
    '本批首次 Editor 构建成功；Game 构建及后续头文件重生成构建被工作区新增元素箭代码阻塞。最终编译错误位于 `Skills/ElementalArrowTypes.h:24`，条件表达式混用字符串与 `NAME_None`（C2446）。保留其他任务源码，完整程序构建尚未完成。'
)
section = f'''

{heading}

根据用户选定的穿云设计制作高地长弓专属特殊改造，稳定 ID `highland_cloudpiercer`，安装于弓体槽。模型使用深烟褐层压木、浅色边线、连续银钢双脊与菱纹护片；保留原握把、箭台、瞄具、弦挂点和 11 骨骨架。独立弓体约 89,242 三角面，新增装饰沿原模型三角面的蒙皮权重插值随弓臂变形。

数值：最大飞行距离 +45%、暴击伤害加成 +75%、物理伤害 +10%、拉弓速度加成 −35%、体力消耗 +55%、持续拉弓耗体 +55%。物理伤害使用 `physical_damage_mult=1.10`，同时作用于基础物理与附加物理，魔法伤害部分不变。玩家说明统一写“暴击伤害 +75%”，内部 `crit_damage_bonus=0.75` 仍按加法结算。最大飞行距离为箭矢飞行上限，体力两项分别为单次出箭及每秒持续拉弓消耗。单独安装于基础高地长弓时，最大飞行距离 69.6 m，满拉约 2.15 s；穿心箭沿统一拉弓速度结算，基础门槛约 4.62 s。已有装备、附魔与技能修正继续参与原计算链。

四个专用材质、一个骨骼网格和标准金属框图标纹理已通过后台 commandlet 保存（退出码 0），目录已定向接入。图标使用正式部件输入与已认可的厚倒角方框、四角铆钉、银色内环及深灰底板规范制作。特殊等级注册使本件使用独立图标。原木纹纹理和钢材复用；新增顶点色限制胡桃木染色范围，避免握持区或金属被整件染色。

制作源、FBX、图标提示词、导入及目录回执在 `SourceAssets/WoodSteelLongbow20261026/CloudpiercerV9/`，正式包目录为 `/Game/Weapons/WoodSteelLongbow20261026/CloudpiercerV9/`。最终执行状态见 `completion.json`。

{build_note} 未打开交互编辑器或游戏，未执行玩法、画面或联机测试。
'''
if heading not in doc.read_text(encoding='utf-8'):
    with doc.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(section)
print('CLOUDPIERCER_DELIVERY_RECORDED', flush=True)
