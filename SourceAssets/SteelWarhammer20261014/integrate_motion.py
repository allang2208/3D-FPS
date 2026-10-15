"""One-time scoped integration of the warhammer into the existing pose executor."""
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
def edit(path,fn):
    p=R/path;old=p.read_text(encoding='utf-8-sig');new=fn(old)
    if new==old:return
    backup=P/'Before'/path;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_text(old,encoding='utf-8')
    p.write_text(new,encoding='utf-8',newline='\n')
def component(s):
    # Resource preparation remains limited to the two actual harvesting tools.
    s=s.replace('Kind==TEXT("axe") || Kind==TEXT("pickaxe")','UsesTwoHandMotion()')
    s=s.replace('(Kind!=TEXT("axe") && Kind!=TEXT("pickaxe"))','!UsesTwoHandMotion()')
    s=s.replace('Kind==TEXT("pickaxe")?FMath::Max','UsesPickaxeMotion()?FMath::Max')
    s=s.replace('bHitConfirmed && Kind==TEXT("pickaxe")?','bHitConfirmed && UsesPickaxeMotion()?')
    s=s.replace('    if(UsesTwoHandMotion())\n        return TraceAxeContact','    if(Kind==TEXT("warhammer"))return false;\n    if(UsesTwoHandMotion())\n        return TraceAxeContact')
    s=s.replace('    if(Kind!=TEXT("shovel")){ShowFeedback', '    if(Kind==TEXT("warhammer"))return;\n    if(Kind!=TEXT("shovel")){ShowFeedback')
    s=s.replace('Feedback=HasReadyPresentation()?((UsesTwoHandMotion())?', 'Feedback=Kind==TEXT("warhammer")?TEXT("双手战锤 · 左键下砸 · G / 滚轮切换武器"):HasReadyPresentation()?((UsesTwoHandMotion())?')
    # SpendStamina publishes a new inventory snapshot; never reuse its old pointer.
    s=s.replace('AxeStrike=ColdSteelSkills::Snapshot(Character.Get(),Item);','AxeStrike=ColdSteelSkills::Snapshot(Character.Get(),Profile->ActiveProductionTool());')
    return s
edit('Source/FPSGAME/Production/ProductionToolComponent.cpp',component)
edit('Source/FPSGAME/Production/ProductionToolMotion.cpp',lambda s:s.replace('(Kind!=TEXT("axe") && Kind!=TEXT("pickaxe"))','!UsesTwoHandMotion()').replace('Kind==TEXT("axe") || Kind==TEXT("pickaxe")','UsesTwoHandMotion()').replace('Kind==TEXT("pickaxe")','UsesPickaxeMotion()'))
edit('Source/FPSGAME/Production/ProductionAxeLocomotion.cpp',lambda s:s.replace('Kind==TEXT("pickaxe")','UsesPickaxeMotion()'))
def contact(s):
    s=s.replace('    auto Classify=[&]', '    if(Kind==TEXT("warhammer"))Reason=TEXT("双手战锤 · 左键下砸");\n\n    auto Classify=[&]')
    s=s.replace('const float Limit=bEnemy?AxeCombatReach:AxeHarvestReach;', 'const float Limit=(bEnemy || Kind==TEXT("warhammer"))?AxeCombatReach:AxeHarvestReach;')
    s=s.replace('        FString TreeReason;', '        if(Kind==TEXT("warhammer"))return false;\n        FString TreeReason;')
    s=s.replace('Feedback=Kind==TEXT("pickaxe")?', 'Feedback=Kind==TEXT("warhammer")?TEXT("战锤命中敌人"):Kind==TEXT("pickaxe")?')
    return s
edit('Source/FPSGAME/Production/ProductionAxeContact.cpp',contact)
def body(s):
    # Motion lookup still uses the established pickaxe body family, while inventory retains blunt identity.
    s=s.replace('State.Weapon=FName(*Tool->Kind);','State.Weapon=FName(Tool->UsesPickaxeMotion()?TEXT("pickaxe"):*Tool->Kind);')
    s=s.replace('Tool->Kind==TEXT("pickaxe")?ProductionPickaxeImpact', 'Tool->UsesPickaxeMotion()?ProductionPickaxeImpact')
    return s
edit('Source/FPSGAME/Characters/FPSPlayerBodyActions.cpp',body)
edit('Source/FPSGAME/UI/ColdSteelWarehouseModel.cpp',lambda s:s.replace('TEXT("ue_xuanchi_zhenyue")})','TEXT("ue_xuanchi_zhenyue"), TEXT("ue_steel_warhammer")})'))
def net(s):
    s=s.replace('    if (Item && ColdSteelInventory::IsMeleeWeapon(*Item))\n', '    if (Item && ColdSteelInventory::IsTwoHandedBlunt(*Item))return Panel;\n\n    if (Item && ColdSteelInventory::IsMeleeWeapon(*Item))\n',1)
    s=s.replace('    if (Report.AttackForm != 0) Shot.AttackForm = static_cast<EMonsterAttackForm>(Report.AttackForm);','    if(Declared&&ColdSteelInventory::IsTwoHandedBlunt(*Declared))Shot.AttackForm=EMonsterAttackForm::Blunt;\n    else if (Report.AttackForm != 0) Shot.AttackForm = static_cast<EMonsterAttackForm>(Report.AttackForm);')
    return s
edit('Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp',net)
print('Warhammer motion, category routing, body pose and damage integration written.')
