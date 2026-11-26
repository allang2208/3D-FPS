import json
from integrate_lightning_haste import ROOT, edit, replace
from wire_lightning_haste_speed import include
import integrate_lightning_haste as store

def run():
    store.PROGRESS=ROOT/'SourceAssets/LightningHaste20261019/handling-progress.json'
    store.COMPLETED=json.loads(store.PROGRESS.read_text(encoding='utf-8')) if store.PROGRESS.exists() else []
    edit('Source/FPSGAME/Weapons/Unarmed/FPSUnarmedIdleComponent.cpp',lambda s:replace(include(s,'../../Skills/LightningHasteSpeed.h'),'VisibleAge+=Delta;','VisibleAge+=Delta*LightningHaste::ActionSpeed(GetOwner());'))
    edit('Source/FPSGAME/Weapons/Staff/StaffIllumination.cpp',lambda s:replace(include(s,'../../Skills/LightningHasteSpeed.h'),'IlluminationGestureAge+=Delta;','IlluminationGestureAge+=Delta*LightningHaste::ActionSpeed(GetOwner());'))
    edit('Source/FPSGAME/Items/FPSPotionUseComponent.cpp',lambda s:replace(s,'float(GetWorld()->GetTimeSeconds()-BowReturnStartedAt)-BowReturnHoldSeconds','float(GetWorld()->GetTimeSeconds()-BowReturnStartedAt)*UseRate-BowReturnHoldSeconds'))
    edit('Source/FPSGAME/Movement/FPSDoorPushComponent.h',lambda s:replace(s,'    float ServerAge=0.f;','    float ServerAge=0.f;\n    float ActionRate=1.f,ServerActionRate=1.f;'))
    def door(s):
        s=include(s,'../Skills/LightningHasteSpeed.h')
        s=replace(s,'    Age=0.f;bContactResolved=false;', '    ActionRate=LightningHaste::ActionSpeed(GetOwner());\n    Age=0.f;bContactResolved=false;')
        s=replace(s,'        Age+=Delta;','        Age+=Delta*ActionRate;')
        s=replace(s,'    LastServerRequest=Now;ServerSequence=', '    ServerActionRate=LightningHaste::ActionSpeed(GetOwner());\n    LastServerRequest=Now;ServerSequence=')
        return replace(s,'    ServerAge+=DeltaSeconds;','    ServerAge+=DeltaSeconds*ServerActionRate;')
    edit('Source/FPSGAME/Movement/FPSDoorPushComponent.cpp',door)
    edit('Source/FPSGAME/Weapons/Spellbook/SpellbookComponent.h',lambda s:replace(s,'    float FocusAge=-1.f,','    float FocusActionRate=1.f;\n    float FocusAge=-1.f,'))
    def book(s):
        s=include(s,'../../Skills/LightningHasteSpeed.h')
        s=replace(s,'GetWorld()->GetTimeSeconds()-NetFocusStartedAt>=SpellbookFocusMotion::OpenLength;','(GetWorld()->GetTimeSeconds()-NetFocusStartedAt)*FocusActionRate>=SpellbookFocusMotion::OpenLength;')
        s=replace(s,'    FocusAge=PagePhase=PageAlpha=OpenAlpha=0.f;', '    FocusActionRate=LightningHaste::ActionSpeed(GetOwner());\n    FocusAge=PagePhase=PageAlpha=OpenAlpha=0.f;')
        return replace(s,'if(bFocusInterrupted){AdvanceFocusInterrupt(Delta);return;}','if(bFocusInterrupted){AdvanceFocusInterrupt(Delta);return;}\n    Delta*=FocusActionRate;')
    edit('Source/FPSGAME/Weapons/Spellbook/SpellbookFocus.cpp',book)
    def book_net(s):
        s=include(s,'../../Skills/LightningHasteSpeed.h')
        s=replace(s,'        NetFocusStartedAt=Now;','        FocusActionRate=LightningHaste::ActionSpeed(GetOwner());\n        NetFocusStartedAt=Now;')
        s=replace(s,'FMath::Clamp(Now-NetFocusStartedAt,0.0,double(SpellbookFocusMotion::OpenLength));','FMath::Clamp((Now-NetFocusStartedAt)*FocusActionRate,0.0,double(SpellbookFocusMotion::OpenLength))/FocusActionRate;')
        # Interrupt recovery is imposed control; only map its entry pose to the accelerated opening.
        return replace(s,'const float Age=float(FMath::Max(0.0,Now-NetFocusStartedAt));','const float Age=float(FMath::Max(0.0,Now-NetFocusStartedAt))*FocusActionRate;')
    edit('Source/FPSGAME/Weapons/Spellbook/SpellbookFocusNetwork.cpp',book_net)
    def dual(s):
        s=include(s,'../Skills/LightningHasteSpeed.h')
        s=replace(s,'if(Name==TEXT("equip"))H.ActionRate*=static_cast<float>(H.Stats.EquipRate());','if(Name==TEXT("equip"))H.ActionRate*=static_cast<float>(H.Stats.EquipRate())*LightningHaste::ActionSpeed(GetOwner());')
        return replace(s,'Delta,1.f/BlendDuration);','Delta,LightningHaste::ActionSpeed(GetOwner())/BlendDuration);')
    edit('Source/FPSGAME/Weapons/PistolDualWieldComponent.cpp',dual)
    edit('Source/FPSGAME/FPSGAMECharacter.cpp',lambda s:replace(replace(s,'StartTime + FMath::Max(0.0f, SprintToFireDuration))','StartTime + FMath::Max(0.0f, SprintToFireDuration)/LightningHaste::ActionSpeed(this))'),'FMath::Exp(-SprintBlendRate * DeltaSeconds)','FMath::Exp(-SprintBlendRate * DeltaSeconds*LightningHaste::ActionSpeed(this))'))
    print('Integrated book handling, staff light gesture, unarmed ready, door push and item recovery.')

if __name__=='__main__':run()
