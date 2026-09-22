"""Record completed asset/data installation without running gameplay tests."""
import json
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
receipt = json.loads((P / 'install_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:
    raise RuntimeError('Installation is not complete.')
readme = P / 'README.md'
readme.write_text(readme.read_text(encoding='utf-8').replace(
    '当前状态：源模型、FBX 和菜单图标已制作，游戏内导入等待退出 PIE；尚未修改正式改造目录。',
    '当前状态：独立模型和菜单图标已导入并保存，正式改造目录已接入；未进行游戏测试。'), encoding='utf-8')
delivery_path = P.parent / 'DELIVERY.json'
delivery = json.loads(delivery_path.read_text(encoding='utf-8'))
delivery.setdefault('exclusive_modifications', {})['highland_broadblade'] = {
    'name': '阔锋重刃', 'slot': 'blade_1', 'source': 'Broadblade20260922',
    'mesh': receipt['assets'][0]['asset'], 'ue_integrated': True,
    'stats': receipt['stats'], 'tested': False,
    'note': 'Independent broad blade and production icon; no native code changes or player save edits.'}
delivery_path.write_text(json.dumps(delivery, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
doc = ROOT / 'Docs/Weapons/highland-claymore-20260922.md'
text = doc.read_text(encoding='utf-8')
marker = '## 专属剑身Ⅰ：阔锋重刃'
if marker not in text:
    text += '\n' + marker + '\n\n'
    text += '新增高地剑限定选项 `highland_broadblade`：主体设计宽度约 11 cm、宽肩平滑过渡、剑脊最多加厚 25%，中央符文保留原比例，剑尖长度与装配接口保持原规格。\n\n'
    text += '数值沿用重脊刃（伤害 +20%、造成硬直 +15%、攻速 −25%）；原有三种剑身Ⅰ继续保留。已导入独立模型及统一左向透明图标并保存目录。未测试，由用户测试。\n\n'
    text += '[制作源与接入记录](../../SourceAssets/HighlandClaymoreMeshy20260922/Broadblade20260922/README.md)\n'
    doc.write_text(text, encoding='utf-8')
print('HIGHLAND_BROADBLADE_DELIVERY_RECORDED')
