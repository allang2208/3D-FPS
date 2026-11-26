import json
from integrate_lightning_haste import ROOT,edit,replace
from wire_lightning_haste_speed import include
import integrate_lightning_haste as store

def run():
    store.PROGRESS=ROOT/'SourceAssets/LightningHaste20261019/extra-actions-progress.json'
    store.COMPLETED=json.loads(store.PROGRESS.read_text(encoding='utf-8')) if store.PROGRESS.exists() else []
    edit('Source/FPSGAME/Items/FPSPotionUseComponent.h',lambda s:replace(s,'    double StartTime=0;','    double StartTime=0;\n    float UseRate=1.f;'))
    def potion(s):
        s=include(s,'../Skills/LightningHasteSpeed.h')
        s=replace(s,'StartTime=GetWorld()->GetTimeSeconds()+(bStowOffhand?OffhandLowerSeconds:0.f);','UseRate=LightningHaste::ActionSpeed(GetOwner());\n    StartTime=GetWorld()->GetTimeSeconds()+(bStowOffhand?OffhandLowerSeconds/UseRate:0.f);')
        return replace(s,'float(GetWorld()->GetTimeSeconds()-StartTime);','float(GetWorld()->GetTimeSeconds()-StartTime)*UseRate;')
    edit('Source/FPSGAME/Items/FPSPotionUseComponent.cpp',potion)
    def tool(s):
        s=include(include(s,'../FPSGAMECharacter.h'),'../Skills/LightningHasteSpeed.h')
        return replace(s,'    R.HeavyReleaseStaminaCost=R.StaminaCost*','    const float Haste=LightningHaste::ActionSpeed(Profile?Profile->RuntimePawn():nullptr);\n    R.RateScale*=Haste;R.SwingSeconds/=Haste;R.ContactSeconds/=Haste;R.HeavyChargeSeconds/=Haste;\n    R.HeavyReleaseStaminaCost=R.StaminaCost*')
    edit('Source/FPSGAME/Production/ProductionToolStats.cpp',tool)
    edit('Source/FPSGAME/Production/ProductionToolMotion.cpp',lambda s:include(s,'../Skills/LightningHasteSpeed.h').replace('EquipElapsed+=Delta;','EquipElapsed+=Delta*LightningHaste::ActionSpeed(GetOwner());').replace('InspectElapsed+=Delta;','InspectElapsed+=Delta*LightningHaste::ActionSpeed(GetOwner());'))
    def sword(s):
        s=include(s,'../Skills/LightningHasteSpeed.h')
        return replace(s,'Elapsed=FMath::Min(End,Elapsed+Delta);SamplePose(Elapsed);','Elapsed=FMath::Min(End,Elapsed+Delta*LightningHaste::ActionSpeed(GetOwner()));SamplePose(Elapsed);')
    edit('Source/FPSGAME/Weapons/RuneSwordComponent.cpp',sword)
    edit('Source/FPSGAME/FPSGAMECharacter.cpp',lambda s:replace(s,'WeaponStateDuration = Clip->GetPlayLength();\n    PlayWeaponAnimation(Clip, false);','WeaponStateDuration = Clip->GetPlayLength()/LightningHaste::ActionSpeed(this);\n    PlayWeaponAnimation(Clip, false,LightningHaste::ActionSpeed(this));'))
    edit('Source/FPSGAME/Skills/FPSQuickCombatComponent.h',lambda s:replace(s,'    float ActionDuration() const;','    float ActionRate=1.f;\n    float ActionSourceDuration() const;\n    float ActionSourceRemaining() const;\n    float ActionDuration() const;'))
    def quick(s):
        s=include(s,'LightningHasteSpeed.h')
        s=replace(s,'bool UFPSQuickCombatComponent::BeginAction()\n{','bool UFPSQuickCombatComponent::BeginAction()\n{\n    ActionRate=LightningHaste::ActionSpeed(GetOwner());')
        s=replace(s,'float UFPSQuickCombatComponent::ActionDuration() const','float UFPSQuickCombatComponent::ActionSourceDuration() const')
        s=replace(s,'float UFPSQuickCombatComponent::ActionRemaining() const','float UFPSQuickCombatComponent::ActionSourceRemaining() const')
        s=replace(s,'void UFPSQuickCombatComponent::AdvanceAction(float Delta)\n{','void UFPSQuickCombatComponent::AdvanceAction(float Delta)\n{\n    Delta*=ActionRate;')
        return s+'\nfloat UFPSQuickCombatComponent::ActionDuration() const{return ActionSourceDuration()/ActionRate;}\nfloat UFPSQuickCombatComponent::ActionRemaining() const{return ActionSourceRemaining()/ActionRate;}\n'
    edit('Source/FPSGAME/Skills/FPSQuickCombatComponent.cpp',quick)
    edit('Source/FPSGAME/Weapons/Bow/BowWeaponComponent.h',lambda s:replace(s,'    float NockSeconds = .68f, DrawSeconds = 1.4f, HoldSeconds = 2.2f, ReleaseSeconds = .3f,','    float StageActionRate=1.f;\n    float NockSeconds = .68f, DrawSeconds = 1.4f, HoldSeconds = 2.2f, ReleaseSeconds = .3f,'))
    def bow(s):
        s=include(s,'../../Skills/LightningHasteSpeed.h')
        s=replace(s,'    Stage = Next;','    StageActionRate=(Next==EBowStage::Drawing||Next==EBowStage::Holding||Next==EBowStage::Ready||Next==EBowStage::QuickCombat)?1.f:LightningHaste::ActionSpeed(GetOwner());\n    Stage = Next;')
        s=replace(s,'    Elapsed += Delta;','    Elapsed += Delta*StageActionRate;')
        return replace(s,'const float Remainder = Elapsed - StageSeconds;','const float Remainder = (Elapsed - StageSeconds)/StageActionRate;')
    edit('Source/FPSGAME/Weapons/Bow/BowWeaponComponent.cpp',bow)
    print('Wired consumables, gathering tools, inspections, quick combat, and bow handling.')

if __name__=='__main__':run()
