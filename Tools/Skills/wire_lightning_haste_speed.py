import json
from integrate_lightning_haste import ROOT,edit,replace
import integrate_lightning_haste as store

def include(s,path):
    line=f'#include "{path}"\n'
    if line in s:return s
    end=s.index('\n',s.index('#include '))+1
    return s[:end]+line+s[end:]

def run():
    store.PROGRESS=ROOT/'SourceAssets/LightningHaste20261019/speed-integration-progress.json'
    store.COMPLETED=json.loads(store.PROGRESS.read_text(encoding='utf-8')) if store.PROGRESS.exists() else []
    edit('Source/FPSGAME/Combat/CombatStatusFormula.cpp',lambda s:replace(include(s,'../Skills/LightningHasteSpeed.h'),'return Mul*ZhenmoMovementMultiplier()*(Book?Book->FocusMovementMultiplier():1.f);','return Mul*ZhenmoMovementMultiplier()*(Book?Book->FocusMovementMultiplier():1.f)*LightningHaste::MoveSpeed(GetOwner());'))
    edit('Source/FPSGAME/Combat/ColdSteelFormulaBonuses.cpp',lambda s:replace(include(s,'../Skills/LightningHasteSpeed.h'),'void UColdSteelStatusModel::ApplySpellbookFocus(float& CastSpeed,float& ManaCost)const\n{','void UColdSteelStatusModel::ApplySpellbookFocus(float& CastSpeed,float& ManaCost)const\n{\n    CastSpeed*=LightningHaste::ActionSpeed(RuntimePawn());'))
    edit('Source/FPSGAME/Skills/ColdSteelSkillModel.cpp',lambda s:replace(include(s,'LightningHasteSpeed.h'),'{ return 1.f+DexterousHandsEffect().ReloadSpeed; }','{ return (1.f+DexterousHandsEffect().ReloadSpeed)*LightningHaste::ActionSpeed(RuntimePawn()); }'))
    edit('Source/FPSGAME/Weapons/WeaponStatEvaluation.cpp',lambda s:replace(include(s,'../Skills/LightningHasteSpeed.h'),'Result/=FMath::Max(0.05,1.+BowDrawSpeedBonus(Item,Model));','Result/=FMath::Max(0.05,1.+BowDrawSpeedBonus(Item,Model));\n        Result/=LightningHaste::ActionSpeed(Model->RuntimePawn());'))
    def melee(s):
        s=include(s,'../Skills/LightningHasteSpeed.h')
        s=replace(s,'    R.AttackSeconds=RuneSwordRhythm::AttackEnd/R.AttackRate;','    R.AttackRate*=LightningHaste::ActionSpeed(Profile?Profile->RuntimePawn():nullptr);\n    R.HeavyChargeSeconds/=LightningHaste::ActionSpeed(Profile?Profile->RuntimePawn():nullptr);\n    R.AttackSeconds=RuneSwordRhythm::AttackEnd/R.AttackRate;')
        return s
    edit('Source/FPSGAME/Weapons/MeleeWeaponStats.cpp',melee)
    edit('Source/FPSGAME/Weapons/RuneSwordComponent.cpp',lambda s:replace(include(s,'../Skills/LightningHasteSpeed.h'),'SwingRate=!Heavy&&bUseWeaponAttackSpeed?AttackRate:1.f;','SwingRate=!Heavy&&bUseWeaponAttackSpeed?AttackRate:LightningHaste::ActionSpeed(GetOwner());'))
    for name in ['RuneSwordUppercut.cpp','RuneSwordWhirlwind.cpp']:
        edit('Source/FPSGAME/Weapons/'+name,lambda s:replace(include(s,'../Skills/LightningHasteSpeed.h'),'SwingRate=1.f;','SwingRate=LightningHaste::ActionSpeed(GetOwner());'))
    def guard(s):
        s=include(s,'../Skills/LightningHasteSpeed.h')
        return s.replace('GuardPoseTime+Delta)','GuardPoseTime+Delta*LightningHaste::ActionSpeed(GetOwner()))').replace('GuardPoseTime-Delta*RuneSwordGuardTuning','GuardPoseTime-Delta*LightningHaste::ActionSpeed(GetOwner())*RuneSwordGuardTuning')
    edit('Source/FPSGAME/Weapons/RuneSwordGuard.cpp',guard)
    def toolguard(s):
        s=include(s,'../Skills/LightningHasteSpeed.h')
        s=s.replace('ToolGuardAge+=Delta;','ToolGuardAge+=Delta*LightningHaste::ActionSpeed(GetOwner());')
        s=s.replace('ToolGuardAge-Delta*WarhammerGuard::EnterSeconds','ToolGuardAge-Delta*LightningHaste::ActionSpeed(GetOwner())*WarhammerGuard::EnterSeconds')
        return s.replace('WarhammerGuard::ExitSeconds,ToolGuardAge+Delta)','WarhammerGuard::ExitSeconds,ToolGuardAge+Delta*LightningHaste::ActionSpeed(GetOwner()))')
    edit('Source/FPSGAME/Weapons/RuneSwordToolGuard.cpp',toolguard)
    edit('Source/FPSGAME/Skills/ColdSteelElectricMagicModel.cpp',lambda s:replace(include(s,'LightningHasteSpeed.h'),'C.MinCharge=T.MinCharge;C.MaxCharge=T.MaxCharge;','C.MinCharge=T.MinCharge/LightningHaste::ActionSpeed(RuntimePawn());C.MaxCharge=T.MaxCharge/LightningHaste::ActionSpeed(RuntimePawn());'))
    edit('Source/FPSGAME/FPSGAMECharacter.h',lambda s:replace(s,'class UFPSLightningHasteComponent* GetLightningHaste() const{return LightningHasteSkill;}','class UFPSLightningHasteComponent* GetLightningHaste() const{return LightningHasteSkill;}\n    float ADSActionRate=1.f;'))
    def character(s):
        s=include(s,'Skills/LightningHasteSpeed.h')
        old='return IsSaiga12KWeapon()?FMath::Max(double(Saiga12KWeaponAssets::MinimumAttackInterval),Interval):IsTubeShotgunWeapon()?FMath::Max(TubeShotgunAssets::MinimumInterval(ActiveInventoryWeaponDefinition),Interval):Interval;'
        s=replace(s,old,'const double Clamped=IsSaiga12KWeapon()?FMath::Max(double(Saiga12KWeaponAssets::MinimumAttackInterval),Interval):IsTubeShotgunWeapon()?FMath::Max(TubeShotgunAssets::MinimumInterval(ActiveInventoryWeaponDefinition),Interval):Interval;\n    return Clamped/LightningHaste::ActionSpeed(this);')
        s=replace(s,'const float Duration = FMath::Max(0.05f, bIsAiming ? ADSInDuration : ADSOutDuration);','const float Duration = FMath::Max(0.05f, bIsAiming ? ADSInDuration : ADSOutDuration)/ADSActionRate;')
        s=replace(s,'    ADSStartProgress = ADSProgress;','    ADSStartProgress = ADSProgress;\n    ADSActionRate=LightningHaste::ActionSpeed(this);')
        s=s.replace('WeaponStateDuration /= FirearmEquipRate;','const float EquipRate=FirearmEquipRate*LightningHaste::ActionSpeed(this);\n        WeaponStateDuration /= EquipRate;')
        s=s.replace('for(float& Cue : MechanicalCueTimes) Cue /= FirearmEquipRate;','for(float& Cue : MechanicalCueTimes) Cue /= EquipRate;').replace('ActionBlendIn /= FirearmEquipRate;','ActionBlendIn /= EquipRate;')
        return s
    edit('Source/FPSGAME/FPSGAMECharacter.cpp',character)
    def dual(s):
        s=include(s,'../Skills/LightningHasteSpeed.h')
        s=replace(s,'const double ShotInterval=FMath::Max(.001,H.Stats.Interval);','const float ActionSpeed=LightningHaste::ActionSpeed(GetOwner());\n    const double ShotInterval=FMath::Max(.001,H.Stats.Interval)/ActionSpeed;')
        return replace(s,'?H.Clips.FindRef(TEXT("fire"))->GetPlayLength()/float(ShotInterval):1.f;','?H.Clips.FindRef(TEXT("fire"))->GetPlayLength()/float(ShotInterval):ActionSpeed;')
    edit('Source/FPSGAME/Weapons/PistolDualWieldCombat.cpp',dual)
    edit('Source/FPSGAME/Movement/FPSPlayerDodge.cpp',lambda s:replace(include(s,'../Skills/LightningHasteSpeed.h'),'Movement->StartDodge(Direction,Distance,DodgeDuration)','Movement->StartDodge(Direction,Distance,DodgeDuration/LightningHaste::ActionSpeed(this))'))
    edit('Source/FPSGAME/Movement/FPSTraversalExecution.cpp',lambda s:replace(include(s,'../Skills/LightningHasteSpeed.h'),'PlaybackRate=bVault?GetDefault<UFPSTraversalSettings>()->VaultPlaybackRate:1.f;','PlaybackRate=(bVault?GetDefault<UFPSTraversalSettings>()->VaultPlaybackRate:1.f)*LightningHaste::ActionSpeed(C);'))
    print('Wired movement, melee, firearms, reload, bow draw, casting, charge, guards, ADS, equip, dodge, and traversal clocks.')

if __name__=='__main__':run()
