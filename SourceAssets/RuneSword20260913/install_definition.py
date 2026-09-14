"""Add only the sword definition; preserve concurrent catalog changes."""
import json
from pathlib import Path
P=Path(__file__).parents[2];path=P/'Content/ColdSteelData/items.json'
data=json.loads(path.read_text(encoding='utf-8-sig'))
folder='/Game/Weapons/AzureRunesword20260913'
item={'id':'ue_rune_sword','name':'苍蓝星辉·双手符文剑','category':'weapon_melee','type':'双手符文剑','weaponType':'sword','weaponTypeTag':'双手剑','equipSlot':'weapon','isTwoHanded':True,'rarity':'epic','grade':'epic','stack_max':1,'grid_w':2,'grid_h':4,'price':3200,'level':1,'enhanceLevel':0,
      'desc':'苍蓝符文镶嵌于剑脊。右手握护手下方、左手握剑首上方；左键交替挥砍，收势阶段再次点击可衔接下一斩。',
      'ue_icon':'Icons/ue_rune_sword.png','melee_damage':55,'melee_reach_cm':180,'attack_seconds':1.775,'contact_start':.85,'contact_end':.965,
      'viewmodel_mesh':folder+'/SK_AzureRunesword_Manny.SK_AzureRunesword_Manny','world_mesh':folder+'/SM_AzureRunesword.SM_AzureRunesword','animation_folder':folder,
      'swing_sound':folder+'/Sword_Swing.Sword_Swing','hit_sound':folder+'/Sword_Hit.Sword_Hit'}
if 'ue_rune_sword' not in data:
    text=path.read_text(encoding='utf-8-sig');end=text.rfind('}')
    path.write_text(text[:end].rstrip()+',\n  "ue_rune_sword": '+json.dumps(item,ensure_ascii=False,indent=2).replace('\n','\n  ')+'\n}\n',encoding='utf-8')
config=P/'Config/DefaultGame.ini';text=config.read_text(encoding='utf-8-sig')
entry='+DirectoriesToAlwaysCook=(Path="'+folder+'")'
if entry not in text:
    text=text.replace('[/Script/UnrealEd.ProjectPackagingSettings]','[/Script/UnrealEd.ProjectPackagingSettings]\n'+entry,1)
    config.write_text(text,encoding='utf-8')
(Path(__file__).parent/'item_definition.json').write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding='utf-8')
