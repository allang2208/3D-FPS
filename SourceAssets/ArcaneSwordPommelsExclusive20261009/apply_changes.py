from pathlib import Path
import shutil
P=Path('D:/FPS3D/FPSGAME')
B=P/'SourceAssets/ArcaneSwordPommelsExclusive20261009/Before'
paths=['Content/ColdSteelData/melee-gunsmith.json','Content/ColdSteelData/shared-sword-pommels.json','Source/FPSGAME/Weapons/GunsmithModificationTier.h','Source/FPSGAME/Weapons/ModularSwordVisual.cpp']
for rel in paths:
    dest=B/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(P/rel,dest)
def replace(path,old,new):
    p=P/path
    text=p.read_bytes().decode('utf-8')
    eol='\r\n' if '\r\n' in text else '\n'
    old=old.replace('\n',eol);new=new.replace('\n',eol)
    if text.count(old)!=1:raise RuntimeError('Intervening edit or unexpected source at '+path)
    p.write_bytes(text.replace(old,new).encode('utf-8'))
for key,name in [('pommel_mana_orb','魔力球配重'),('ballast_rune','凝碧星核')]:
    old=f'          "id": "{key}",\n          "name": "{name}",'
    new=old+'\n          "weapons": [\n            "ue_frost_crystal_sword",\n            "ue_rune_sword"\n          ],'
    replace(paths[0],old,new)
    old=f'    "{key}": {{\n      "mesh":'
    new=f'    "{key}": {{\n      "weapons": [\n        "ue_frost_crystal_sword",\n        "ue_rune_sword"\n      ],\n      "mesh":'
    replace(paths[1],old,new)
    replace(paths[1],f'"appearance": "{name} · 剑类通用配重"',f'"appearance": "{name} · 寒晶与苍蓝星辉专属特殊改造"')
replace(paths[0],'"description": "银色支架包覆蓝色魔力晶球，手持时强化魔法伤害并提高魔法值消耗。"','"description": "寒晶与苍蓝星辉双手剑专属。银色支架包覆蓝色魔力晶球，手持时强化魔法伤害并提高魔法值消耗。"')
replace(paths[0],'"description": "银色护架包覆凝碧星核，快速近战（配重锤打击）命中施加魔法易伤。"','"description": "寒晶与苍蓝星辉双手剑专属。银色护架包覆凝碧星核，快速近战（配重锤打击）命中施加魔法易伤。"')
replace(paths[2],'''        VipGrip || SiMuzzle || G18Drum ||
''','''        VipGrip || SiMuzzle || G18Drum ||
        ((Weapon==TEXT("ue_frost_crystal_sword")||Weapon==TEXT("ue_rune_sword")) &&
            SlotKey==TEXT("pommel") && (Id==TEXT("pommel_mana_orb")||Id==TEXT("ballast_rune"))) ||
''')
replace(paths[3],'''            auto Spec=MakeShared<FJsonObject>();Spec->Values=Pair.Value->AsObject()->Values;
            const TSharedPtr<FJsonObject>* Interfaces=nullptr,*Fitting=nullptr;''','''            auto Spec=MakeShared<FJsonObject>();Spec->Values=Pair.Value->AsObject()->Values;
            // Shared geometry follows the same weapon restriction as the workbench.
            // Unsupported legacy selections then resolve to this sword's factory pommel.
            const TArray<TSharedPtr<FJsonValue>>* Compatible=nullptr;
            if(Spec->TryGetArrayField(TEXT("weapons"),Compatible)&&!Compatible->IsEmpty()&&
                !Compatible->ContainsByPredicate([&](const TSharedPtr<FJsonValue>& Id){return Id->AsString()==Item.Definition;}))
            {Choices->RemoveField(Pair.Key);continue;}
            const TSharedPtr<FJsonObject>* Interfaces=nullptr,*Fitting=nullptr;''')
