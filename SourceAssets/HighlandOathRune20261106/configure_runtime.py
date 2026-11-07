"""Scoped, idempotent catalog and rune-surface integration for the approved oath rune."""
from pathlib import Path
import json, shutil
ROOT=Path(__file__).resolve().parents[2]
P=Path(__file__).resolve().parent
def edit(path,old,new):
    path=ROOT/path
    text=path.read_text(encoding='utf-8-sig')
    if new in text:return
    if old not in text:raise RuntimeError(f'Missing integration anchor: {path}: {old[:70]}')
    path.write_text(text.replace(old,new,1),encoding='utf-8')

visual=Path('Source/FPSGAME/Weapons/MeleeRuneVisual.cpp')
edit(visual,'const int32 Mode=bBeiwei?10:', 'const int32 Mode=bOath?11:bBeiwei?10:')
edit(visual,'const FString DesiredBase=bThunderExclusive?', 'const FString DesiredBase=bOath?TEXT("M_SilverRuneSurface_HighlandOath"):bThunderExclusive?')
edit(visual,'auto* Material=LoadObject<UMaterialInterface>(nullptr,bWarhammer?', 'auto* Material=LoadObject<UMaterialInterface>(nullptr,bOath?TEXT("/Game/Weapons/HighlandClaymore20260922/OathRune20261106/M_SilverRuneSurface_HighlandOath"):bWarhammer?')
edit(visual,'const FString TexturePath=bWild?', 'const FString TexturePath=bOath?TEXT("/Game/Weapons/HighlandClaymore20260922/OathRune20261106/T_Mask_highland_oath_rune"):bWild?')
edit(visual,'HighlandMID->SetScalarParameterValue(TEXT("NativeGold"),0.f);', 'HighlandMID->SetScalarParameterValue(TEXT("NativeGold"),0.f);\n            HighlandMID->SetScalarParameterValue(TEXT("NativeOath"),bOath?1.f:0.f);')
edit('Source/FPSGAME/Weapons/FrostSwordRunes.h','if(IsThunderExclusive(Rune)&&Weapon!=ThunderGodHammer)return {};','if(Rune==TEXT("highland_oath_rune")&&Weapon!=TEXT("ue_highland_claymore"))return {};\n        if(IsThunderExclusive(Rune)&&Weapon!=ThunderGodHammer)return {};')
edit('Source/FPSGAME/Weapons/GunsmithModificationTier.h','(SlotKey==TEXT("blade_2") && Id==TEXT("wild_rune"))','(SlotKey==TEXT("blade_2") && (Id==TEXT("wild_rune")||Id==TEXT("highland_oath_rune")))')

icons=P/'Icons';textures=P/'Textures';icons.mkdir(exist_ok=True);textures.mkdir(exist_ok=True)
icon='ue_highland_claymore_blade_2_highland_oath_rune.png'
generated=Path('C:/Users/allan/.codex/generated_images/01a1a6e8-d97c-7b30-b4ff-9174f8b522f1')
shutil.copy2(P/'IconV2/OathRune_Framed_V2.png',icons/icon)
shutil.copy2(generated/'exec-2c906b31-0caa-4fc1-b145-40fcfd1a7120.png',textures/'T_Mask_highland_oath_rune.png')
shutil.copy2(icons/icon,ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/icon)
path=ROOT/'Content/ColdSteelData/melee-gunsmith.json'
before=path.read_bytes();data=json.loads(before.decode('utf-8-sig'))
column=next(c for c in data['columns'] if c['key']=='blade_2')
option={'id':'highland_oath_rune','name':'誓约符文','tier':'special','weapons':['ue_highland_claymore'],
 'description':'高地骑士的誓剑刻印，以三重誓环约束蓄积的力量，在完成蓄力的刹那释放裁决。',
 'effects':[{'text':'重击物理伤害+15%','benefit':1},{'text':'重击蓄力持续体力消耗-20%','benefit':1}],
 'special_effects':['裁决时刻｜首次蓄满后的0.35秒内释放重击，本次重击物理伤害额外+35%，韧性伤害+50%；首次有效命中返还本次出手实际消耗体力的25%。每次蓄力只触发一次。'],
 'stats':{'oath_heavy_physical_mult':1.15,'oath_charge_stamina_mult':.8},
 'icon':f'/Game/ColdSteelData/AttachmentIcons20260913/{Path(icon).stem}'}
index=next((i for i,o in enumerate(column['options']) if o['id']==option['id']),None)
if index is None:column['options'].append(option)
else:column['options'][index]=option
if path.read_bytes()!=before:raise RuntimeError('Catalog changed concurrently; refusing stale write')
(P/'catalog-before.json').write_bytes(before)
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'option.json').write_text(json.dumps(option,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Oath catalog, image sources and runtime surface routing authored.')
