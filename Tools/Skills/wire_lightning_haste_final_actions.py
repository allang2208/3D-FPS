import json
from integrate_lightning_haste import ROOT, edit, replace
from wire_lightning_haste_speed import include
import integrate_lightning_haste as store

def run():
    store.PROGRESS=ROOT/'SourceAssets/LightningHaste20261019/final-actions-progress.json'
    store.COMPLETED=json.loads(store.PROGRESS.read_text(encoding='utf-8')) if store.PROGRESS.exists() else []
    def staff(s):
        s=include(s,'../../Skills/LightningHasteSpeed.h')
        s=replace(s,'Duration=FMath::Max(.1,double(ColdSteelWeaponStats::Interval(I,P,.5)));','Duration=FMath::Max(.1,double(ColdSteelWeaponStats::Interval(I,P,.5)))/LightningHaste::ActionSpeed(GetOwner());')
        return replace(s,'EquipAge+=Delta;','EquipAge+=Delta*LightningHaste::ActionSpeed(GetOwner());')
    edit('Source/FPSGAME/Weapons/Staff/StaffWeaponComponent.cpp',staff)
    edit('Source/FPSGAME/Weapons/Bow/BowWeaponComponent.cpp',lambda s:replace(s,'void UBowWeaponComponent::AdvanceAimWeight(float Delta, bool bTarget)\n{','void UBowWeaponComponent::AdvanceAimWeight(float Delta, bool bTarget)\n{\n    Delta*=LightningHaste::ActionSpeed(GetOwner());'))
    def character(s):
        s=replace(s,'float ShotAnimationRate = 1.0f;','const float HasteShotRate=LightningHaste::ActionSpeed(this);\n    float ShotAnimationRate = HasteShotRate;')
        s=replace(s,'ShotAnimationRate = FMath::Max(1.0f,','ShotAnimationRate = FMath::Max(HasteShotRate,')
        s=replace(s,'ShotAnimationRate=FMath::Max(1.f,','ShotAnimationRate=FMath::Max(HasteShotRate,')
        s=replace(s,'WeaponStateDuration = 0.18f + FMath::Max(0.1f, ReloadEmptyAnimation->GetPlayLength() - StartAt);\n        PlayWeaponAnimation(ReloadEmptyAnimation, false, 1.0f, StartAt);\n        ActionBlendIn = 0.18f;', 'const float EquipRate=LightningHaste::ActionSpeed(this);\n        WeaponStateDuration = (0.18f + FMath::Max(0.1f, ReloadEmptyAnimation->GetPlayLength() - StartAt))/EquipRate;\n        PlayWeaponAnimation(ReloadEmptyAnimation, false, EquipRate, StartAt);\n        ActionBlendIn = 0.18f/EquipRate;')
        return s
    edit('Source/FPSGAME/FPSGAMECharacter.cpp',character)
    def tool_header(s):
        s=replace(s,'    float RateScale=1.f;','    float RateScale=1.f;\n    float HasteActionRate=1.f;')
        s=replace(s,'return bBluntSprintAttack?1.f:RateScale;','return bBluntSprintAttack?HasteActionRate:RateScale;')
        return replace(s,'?WarhammerSprint::LiftSeconds:0.f;','?WarhammerSprint::LiftSeconds/HasteActionRate:0.f;')
    edit('Source/FPSGAME/Production/ProductionToolComponent.h',tool_header)
    edit('Source/FPSGAME/Production/ProductionToolComponent.cpp',lambda s:replace(include(s,'../Skills/LightningHasteSpeed.h'),'    RateScale=float(ToolStats.RateScale);','    RateScale=float(ToolStats.RateScale);\n    HasteActionRate=LightningHaste::ActionSpeed(GetOwner());'))
    edit('Source/FPSGAME/Production/ProductionBluntAuthority.cpp',lambda s:replace(replace(s,'const float ActionRate=bSprintAttack?1.f:RateScale;','const float ActionRate=bSprintAttack?HasteActionRate:RateScale;'),'const float Lift=bSprintAttack?WarhammerSprint::LiftSeconds:0.f;','const float Lift=bSprintAttack?WarhammerSprint::LiftSeconds/HasteActionRate:0.f;'))
    edit('Source/FPSGAME/Production/ProductionToolMotion.cpp',lambda s:s.replace('CaptureLocomotionEntry(WarhammerSprint::LiftSeconds)','CaptureLocomotionEntry(BluntLiftSeconds())').replace('PostureEase(0.f,WarhammerSprint::LiftSeconds,Elapsed)','PostureEase(0.f,BluntLiftSeconds(),Elapsed)'))
    edit('Source/FPSGAME/Production/ProductionBluntHeavy.cpp',lambda s:replace(s,'BluntChargeReturnAge+Delta);','BluntChargeReturnAge+Delta*HasteActionRate);'))
    def uppercut(s):
        s=replace(s,'+RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End)+HitPause;','+(RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End)+HitPause)/HasteActionRate;')
        return replace(s,'    const float Pause=FMath::Min(Delta,BluntUppercutPause);','    Delta*=HasteActionRate;\n    const float Pause=FMath::Min(Delta,BluntUppercutPause);')
    edit('Source/FPSGAME/Production/ProductionBluntUppercut.cpp',uppercut)
    def whirlwind(s):
        s=replace(s,'+T.ReadySeconds+T.SpinSeconds+T.RecoverSeconds+T.HitStopBudget;','+(T.ReadySeconds+T.SpinSeconds+T.RecoverSeconds+T.HitStopBudget)/HasteActionRate;')
        return replace(s,'    const float Pause=FMath::Min(Delta,BluntWhirlwindPause);','    Delta*=HasteActionRate;\n    const float Pause=FMath::Min(Delta,BluntWhirlwindPause);')
    edit('Source/FPSGAME/Production/ProductionBluntWhirlwind.cpp',whirlwind)
    def whirlwind_net(s):
        s=include(s,'../Skills/LightningHasteSpeed.h')
        s=replace(s,'WhirlwindReadySeconds=T.ReadySeconds;WhirlwindMoveSeconds=T.ReadySeconds+T.SpinSeconds;', 'const float ActionRate=LightningHaste::ActionSpeed(Pawn);\n    WhirlwindReadySeconds=T.ReadySeconds/ActionRate;WhirlwindMoveSeconds=(T.ReadySeconds+T.SpinSeconds)/ActionRate;')
        s=replace(s,'+WhirlwindMoveSeconds+T.RecoverSeconds+(Zhufeng?0.f:T.HitStopBudget)+.35;','+WhirlwindMoveSeconds+T.RecoverSeconds/ActionRate+(Zhufeng?0.f:T.HitStopBudget)+.35;')
        return replace(s,'/RuneSwordOverheadRhythm::DashWindupSeconds:0.f;','/RuneSwordOverheadRhythm::DashWindupSeconds*ActionRate:0.f;')
    edit('Source/FPSGAME/Multiplayer/ColdSteelWhirlwindAuthority.cpp',whirlwind_net)
    edit('Source/FPSGAME/Multiplayer/ColdSteelUppercutAuthority.cpp',lambda s:replace(include(s,'../Skills/LightningHasteSpeed.h'),'UppercutUntil=GetWorld()->GetTimeSeconds()+RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End)\n        -RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::ReleaseStart)+.35;','UppercutUntil=GetWorld()->GetTimeSeconds()+(RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End)\n        -RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::ReleaseStart))/LightningHaste::ActionSpeed(Pawn)+.35;'))
    def movement(s):
        s=include(s,'../Skills/LightningHasteSpeed.h')
        s=replace(s,'    switch(R.Kind)','    const float ActionRate=LightningHaste::ActionSpeed(Player);\n    switch(R.Kind)')
        s=replace(s,'RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End)-RuneSwordUppercutMotion::ReleaseStart:', '(RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End)-RuneSwordUppercutMotion::ReleaseStart)/ActionRate:')
        s=replace(s,'Recovery=.5f;break;','Recovery=.5f/ActionRate;break;')
        return replace(s,'Recovery=W.ReadySeconds+W.SpinSeconds+W.RecoverSeconds;','Recovery=(W.ReadySeconds+W.SpinSeconds+W.RecoverSeconds)/ActionRate;')
    edit('Source/FPSGAME/Movement/FPSMeleeMovementNetwork.cpp',movement)
    def lifecycle(s):
        s=replace(s,'if(GetOwner()->HasAuthority()&&State.bActive){State.bActive=false;GetOwner()->ForceNetUpdate();}','if(State.bActive){State.bActive=false;if(GetOwner()->HasAuthority())GetOwner()->ForceNetUpdate();}')
        return replace(s,'if(Remaining()<=0&&(RewardModel.IsValid()||bAwaiting))End(true);','if(Remaining()<=0&&(State.bActive||Prediction.bActive||RewardModel.IsValid()||bAwaiting))End(true);')
    edit('Source/FPSGAME/Skills/FPSLightningHasteComponent.cpp',lifecycle)
    edit('Source/FPSGAME/Skills/FPSQuickCombatComponent.cpp',lambda s:replace(replace(s,'    ActionRate=LightningHaste::ActionSpeed(GetOwner());\n    auto* Profile=Model();','    auto* Profile=Model();'),'    if(IsOccupyingLeftHand())return false;','    if(IsOccupyingLeftHand())return false;\n    ActionRate=LightningHaste::ActionSpeed(GetOwner());'))
    edit('Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp',lambda s:replace(s,'bUnarmed?double(StaffQuickCombatMotion::Length):','bUnarmed?double(StaffQuickCombatMotion::Length)/LightningHaste::ActionSpeed(Shooter):') if False else replace(include(s,'../Skills/LightningHasteSpeed.h'),'bUnarmed?double(StaffQuickCombatMotion::Length):','bUnarmed?double(StaffQuickCombatMotion::Length)/LightningHaste::ActionSpeed(Shooter):'))
    edit('Config/DefaultGame.ini',lambda s:replace(s,'+DirectoriesToAlwaysCook=(Path="/Game/Skills/ElectricMagic")','+DirectoriesToAlwaysCook=(Path="/Game/Skills/ElectricMagic")\n+DirectoriesToAlwaysCook=(Path="/Game/Skills/LightningHaste20261019")'))
    edit('Tools/Skills/wire_lightning_haste_ui_network.py',lambda s:s.replace('EGlyph::Bolt','EGlyph::Lightning'))
    print('Completed remaining action, authority, cooking and buff expiry integration.')

if __name__=='__main__': run()
