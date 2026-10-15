"""Register the first two-handed blunt weapon without changing existing definitions."""
import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1];DATA=ROOT/'Content/ColdSteelData';D='/Game/Weapons/SteelWarhammer20261014'
def append_json(filename,key,value):
    p=DATA/filename;text=p.read_text(encoding='utf-8-sig');obj=json.loads(text)
    if key in obj:raise RuntimeError('Definition already exists: '+key)
    before=P/'Before'/filename
    if not before.exists():before.parent.mkdir(parents=True,exist_ok=True);before.write_bytes(p.read_bytes())
    end=text.rfind('}');text=text[:end].rstrip()+',\n  '+json.dumps(key)+': '+json.dumps(value,ensure_ascii=False,indent=2).replace('\n','\n  ')+'\n'+text[end:]
    p.write_text(text,encoding='utf-8',newline='\n')
item={
 'id':'ue_steel_warhammer','name':'锻钢战锤','category':'weapon_melee','type':'双手战锤','weaponType':'blunt','weaponTypeTag':'双手钝器','equipSlot':'weapon','isTwoHanded':True,
 'stack_max':1,'grid_w':2,'grid_h':4,'price':3200,'level':1,'enhanceLevel':0,
 'desc':'以锻钢锤头配长柄制成的双手战锤。双手分握锤柄，便于蓄势挥击与回收；沉重锤头要求使用者把握出手后的收势节奏。',
 'ue_icon':'Icons/ue_steel_warhammer.png','icon_fallback':'战锤','melee_damage':49.5,'melee_reach_cm':180,'combat_reach_cm':360,'combat_sweep_radius_cm':24,
 'attack_seconds':2.04125,'swing_seconds':2.04125,'contact_seconds':1.24125,'toughness_damage_mult':1.,
 'tool_kind':'warhammer','tool_scale':1.,'tool_mesh':D+'/SM_SteelWarhammer.SM_SteelWarhammer','world_mesh':D+'/SM_SteelWarhammer.SM_SteelWarhammer',
 'tool_viewmodel':D+'/SK_SteelWarhammer_BareArmsV7.SK_SteelWarhammer_BareArmsV7','viewmodel_mesh':D+'/SK_SteelWarhammer_BareArmsV7.SK_SteelWarhammer_BareArmsV7',
 'tool_animation_prefix':'/Game/Items/ProductionTools/RusticPickaxe20260919/A_RusticPickaxe_',
 'tool_swing_sound':'/Game/Items/ProductionTools/GripMotion20260913/S_Harvest_Swing.S_Harvest_Swing',
 'tool_sound':'/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick.S_MeleeHit_Quick',
 'hit_sound':'/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick.S_MeleeHit_Quick','harvest_reach_cm':0,'harvest_sweep_radius_cm':0
}
append_json('items.json','ue_steel_warhammer',item)
# Coefficients are 90% of XuanChi ZhenYue; the hammer uses STR/CON (2026-10-14).
append_json('combat-weapon-formulas.json','ue_steel_warhammer',{'source':'STEEL_WARHAMMER_ZHENYUE_90_STR_CON_V2','base':40.5,'enhanceFlat':5.04,'attrs':[{'key':'str','base':4.59,'perEnhance':.909},{'key':'con','base':3.6,'perEnhance':.621}]})
shutil.copy2(P/'Export/ue_steel_warhammer.png',DATA/'Icons/ue_steel_warhammer.png')
(P/'item_definition.json').write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding='utf-8')
print('Registered ue_steel_warhammer item, attack formula, and inventory PNG.')
