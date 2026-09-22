"""Record completed wild-rune authoring, asset install and required native build."""
import json
from pathlib import Path

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
receipt=json.loads((P/'install_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:raise RuntimeError('Rune assets must be installed first.')
build=(P/'build-native-02.log').read_text(encoding='utf-8-sig')
if 'Result: Succeeded' not in build:raise RuntimeError('Required Editor build did not complete.')
delivery=P.parent/'DELIVERY.json'
data=json.loads(delivery.read_text(encoding='utf-8'))
data.setdefault('exclusive_modifications',{})['wild_rune']={
    'name':'蛮荒符文','slot':'blade_2','source':P.name,'ue_integrated':True,
    'material':'/Game/Weapons/HighlandClaymore20260922/WildRune/M_SilverRuneSurface_HighlandWild',
    'stats':receipt['option']['stats'],'native_build':'FPSGAMEEditor Win64 Development: Succeeded (up to date)',
    'tested':False,'icon_generation':'Built-in imagegen; prompt and generated source retained'}
delivery.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
doc=ROOT/'Docs/Weapons/highland-claymore-20260922.md'
text=doc.read_text(encoding='utf-8')
heading='## 专属剑身Ⅱ：蛮荒符文'
if heading not in text:
    text+='\n'+heading+'\n\n'
    text+='新增高地限定 `wild_rune`，六段赤红獠牙刻纹、柔和呼吸光，原生刻纹随之染红。韧性伤害 +30%、物理防御穿透 +20%，覆盖该武器近战命中；不把削韧倍率混同于硬直持续时间。语义图标、材质、目录、命中结算与 UI 属性均已接入，常规 Editor 构建已完成，未测试。\n\n'
    text+='[蛮荒符文源文件、生成提示词与接入记录](../../SourceAssets/HighlandClaymoreMeshy20260922/WildRune20260922/README.md)\n'
    doc.write_text(text,encoding='utf-8')
print('HIGHLAND_WILD_RUNE_DELIVERY_RECORDED')
