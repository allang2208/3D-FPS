import json
import integrate_melee_masteries as task
from integrate_melee_masteries import ROOT,WORK,rep,inc,edit

def run():
    task.PROGRESS=WORK/'training-progress.json'
    task.DONE=json.loads(task.PROGRESS.read_text(encoding='utf-8')) if task.PROGRESS.exists() else []
    def normal(s):
        s=inc(inc(s,'../Skills/ColdSteelSkillRules.h'),'../Multiplayer/ColdSteelAuthorityContext.h')
        s=inc(s,'../UI/ColdSteelStatusModel.h')
        s=rep(s,'    bool Confirmed=false;','    bool Confirmed=false;int32 MasteryHits=0;\n    const auto* Profile=ColdSteelAuthority::ForPawn(Pawn);')
        s=rep(s,'        if(!ResolveAxeEnemyContact(Hit))continue;','        const bool Eligible=ColdSteelSkills::IsMasteryTrainingTarget(Pawn,Hit.GetActor());\n        AxeStrike.ExtraMasteryExperience=Eligible&&MasteryHits==1&&Profile?Profile->MasteryDefinition(AxeStrike.MasteryId).MultiHitExperience:0;\n        if(!ResolveAxeEnemyContact(Hit))continue;\n        if(Eligible)++MasteryHits;')
        return rep(s,'    FProductionResource Resource;FHitResult Glass;FString Reason;','    AxeStrike.ExtraMasteryExperience=0;\n    FProductionResource Resource;FHitResult Glass;FString Reason;')
    edit('Source/FPSGAME/Production/ProductionBluntContact.cpp',normal)
    edit('Source/FPSGAME/Production/WarhammerShockwave.h',lambda s:rep(s,'    float PreviousRadius=0.f;','    float PreviousRadius=0.f;\n    int32 MasteryHits=0;'))
    def wave(s):
        s=inc(s,'../UI/ColdSteelStatusModel.h')
        s=rep(s,'        const float Damage=ColdSteelSkills::ApplyHit(Pawn,Hit,Shot.DamagePanel.Total(),(Point-Origin).GetSafeNormal(),Shot,&Result);','        const bool Eligible=ColdSteelSkills::IsMasteryTrainingTarget(Pawn,Target);\n        auto HitShot=Shot;HitShot.ExtraMasteryExperience=Eligible&&MasteryHits==1&&Profile?Profile->MasteryDefinition(Shot.MasteryId).MultiHitExperience:0;\n        const float Damage=ColdSteelSkills::ApplyHit(Pawn,Hit,Shot.DamagePanel.Total(),(Point-Origin).GetSafeNormal(),HitShot,&Result);\n        if(Eligible&&(Damage>0.f||Result.bKilled))++MasteryHits;')
        return s
    edit('Source/FPSGAME/Production/WarhammerShockwave.cpp',wave)
    def whirl(s):
        return rep(s,'        const float Applied=ColdSteelSkills::ApplyHit(Pawn,Hit,BluntWhirlwindCast.Damage,Direction,BluntWhirlwindShot,&Result);','        const bool Eligible=ColdSteelSkills::IsMasteryTrainingTarget(Pawn,Target);\n        auto HitShot=BluntWhirlwindShot;HitShot.ExtraMasteryExperience=Eligible&&BluntWhirlwindHitCount==1?Profile->MasteryDefinition(HitShot.MasteryId).MultiHitExperience:0;\n        const float Applied=ColdSteelSkills::ApplyHit(Pawn,Hit,BluntWhirlwindCast.Damage,Direction,HitShot,&Result);').replace('if(Combat&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining")))\n        {++BluntWhirlwindHitCount;','if(Eligible)\n        {++BluntWhirlwindHitCount;')
    edit('Source/FPSGAME/Production/ProductionBluntWhirlwind.cpp',whirl)
    def quick(s):
        s=rep(s,'    TSet<TWeakObjectPtr<AActor>> Seen;','    TSet<TWeakObjectPtr<AActor>> Seen;int32 MasteryHits=0;')
        return rep(s,'        const float Applied=ColdSteelSkills::ApplyHit(Player,Hit,Stats.Damage,Direction,Shot,&Result);','        const bool Eligible=ColdSteelSkills::IsMasteryTrainingTarget(Player,Target);\n        auto HitShot=Shot;HitShot.ExtraMasteryExperience=Eligible&&MasteryHits==1?Profile->MasteryDefinition(Shot.MasteryId).MultiHitExperience:0;\n        const float Applied=ColdSteelSkills::ApplyHit(Player,Hit,Stats.Damage,Direction,HitShot,&Result);\n        if(Eligible&&(Applied>0.f||Result.bKilled))++MasteryHits;')
    edit('Source/FPSGAME/Skills/WarhammerQuickCombat.cpp',quick)
    # One snapshot identifies one weapon action, including its multi-target reports.
    edit('Source/FPSGAME/Skills/ColdSteelSkillTypes.h',lambda s:rep(s,'    FName MasteryId;','    FName MasteryId;\n    uint32 MasteryAttackSerial=0;'))
    def shot(s):
        return rep(s,'Shot.MasteryId=M->WeaponMastery(Item?Item:M->Equipped());','Shot.MasteryId=M->WeaponMastery(Item?Item:M->Equipped());\n        if(IsMeleeMastery(Shot.MasteryId)){static uint32 NextMasteryAttack=0;if(++NextMasteryAttack==0)++NextMasteryAttack;Shot.MasteryAttackSerial=NextMasteryAttack;}')
    edit('Source/FPSGAME/Skills/ColdSteelSkillRules.cpp',shot)
    def state_h(s):
        s=rep(s,'    UPROPERTY() uint32 GuardAttackSerial = 0;','    UPROPERTY() uint32 GuardAttackSerial = 0;\n    UPROPERTY() uint32 MasteryAttackSerial = 0;')
        return rep(s,'    TSet<TWeakObjectPtr<AActor>> QuickCombatTargets;','    TSet<TWeakObjectPtr<AActor>> QuickCombatTargets;\n    uint32 LastMasteryAttackSerial=0;\n    int32 MeleeMasteryHits=0;\n    TWeakObjectPtr<APawn> MeleeMasteryPawn;\n    FString MeleeMasteryWeapon;\n    TSet<TWeakObjectPtr<AActor>> MeleeMasteryTargets;')
    edit('Source/FPSGAME/Multiplayer/ColdSteelPlayerState.h',state_h)
    def network(s):
        s=rep(s,'    Report.GuardAttackSerial=Shot.GuardAttackSerial;','    Report.GuardAttackSerial=Shot.GuardAttackSerial;\n    Report.MasteryAttackSerial=Shot.MasteryAttackSerial;')
        s=rep(s,'    FWeaponDamageResult Receipt;\n    if(Report.AttackMeta&0x20)','    FWeaponDamageResult Receipt;\n    // Recompute multi-target training from accepted contacts; never trust client XP.\n    const bool MasteryEligible=ColdSteelSkills::IsMeleeMastery(Shot.MasteryId)&&!Shot.bRicochet\n        &&Report.MasteryAttackSerial&&ColdSteelSkills::IsMasteryTrainingTarget(Shooter,Report.Target);\n    if(MasteryEligible&&(MeleeMasteryPawn.Get()!=Shooter||static_cast<int32>(Report.MasteryAttackSerial-LastMasteryAttackSerial)>0))\n    {\n        LastMasteryAttackSerial=Report.MasteryAttackSerial;MeleeMasteryPawn=Shooter;\n        MeleeMasteryWeapon=Report.ItemDefinition;MeleeMasteryHits=0;MeleeMasteryTargets.Reset();\n    }\n    const bool NewMasteryTarget=MasteryEligible&&Report.MasteryAttackSerial==LastMasteryAttackSerial\n        &&MeleeMasteryWeapon==Report.ItemDefinition&&!MeleeMasteryTargets.Contains(Report.Target.Get());\n    if(NewMasteryTarget&&MeleeMasteryHits==1)Shot.ExtraMasteryExperience=Model->MasteryDefinition(Shot.MasteryId).MultiHitExperience;\n    if(Report.AttackMeta&0x20)')
        s=rep(s,'if(WhirlwindHits==1)Shot.ExtraMasteryExperience=Model->MasteryDefinition(TEXT("swordMastery")).MultiHitExperience;','if(WhirlwindHits==1&&MasteryEligible)Shot.ExtraMasteryExperience=Model->MasteryDefinition(Shot.MasteryId).MultiHitExperience;')
        return rep(s,'    if(Report.AttackMeta&0x20)ConfirmSwordWhirlwindHit','    if(NewMasteryTarget&&(Applied>0.f||Receipt.bKilled)){MeleeMasteryTargets.Add(Report.Target.Get());++MeleeMasteryHits;}\n    if(Report.AttackMeta&0x20)ConfirmSwordWhirlwindHit')
    edit('Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp',network)
    print('Wired blunt direct/area/quick-melee training and authoritative melee action grouping.')

if __name__=='__main__':run()
