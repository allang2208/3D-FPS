"""Update this weapon's delivery notes after successful thickness import."""
import json
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
receipt = json.loads((P / 'install_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:
    raise RuntimeError('Thickness revision installation is incomplete.')
path = P.parent / 'DELIVERY.json'
data = json.loads(path.read_text(encoding='utf-8'))
entry = data['exclusive_modifications']['highland_broadblade']
entry.update(source=P.name, previous_source='Broadblade20260922',
             mesh=receipt['mesh'], ue_integrated=True, tested=False,
             geometry_revision='ThickV2', intended_middle_spine_mm=[15, 17],
             note='Added up to 8.4 mm of spine thickness with broad supported faces and a tapered grinding bevel. Width, length and gameplay stats preserved. UI icon updated.')
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

doc = ROOT / 'Docs/Weapons/highland-claymore-20260922.md'
text = doc.read_text(encoding='utf-8')
heading = '### 阔锋重刃厚度修订 V2'
if heading not in text:
    text += '\n' + heading + '\n\n'
    text += '根据剑身过薄的反馈，当前模型已切换到加厚 V2：中段剑脊设计厚度约 15–17 mm，两侧刃面一并增加体积，并通过磨刃面逐渐过渡到薄刃口。宽度、长度、符文比例与改造属性沿用前版。模型、专属图标和目录引用已保存，未进行游戏测试。\n\n'
    text += '[V2 可编辑源与接入记录](../../SourceAssets/HighlandClaymoreMeshy20260922/BroadbladeThicknessV2_20260922/README.md)\n'
    doc.write_text(text, encoding='utf-8')

old_doc = P.parent / 'Broadblade20260922/README.md'
text = old_doc.read_text(encoding='utf-8')
previous = '当前状态：独立模型和菜单图标已导入并保存，正式改造目录已接入；未进行游戏测试。'
text = text.replace(previous, '版本说明：下文为 V1 初版制作记录。当前游戏已采用[加厚 V2](../BroadbladeThicknessV2_20260922/README.md)，初版源文件继续保留。')
old_doc.write_text(text, encoding='utf-8')
print('HIGHLAND_BROADBLADE_THICK_V2_DELIVERY_RECORDED')
