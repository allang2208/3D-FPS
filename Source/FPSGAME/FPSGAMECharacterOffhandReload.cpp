#include "FPSGAMECharacter.h"
#include "FPSGAMEPlayerController.h"
#include "UI/ColdSteelStatusModel.h"
#include "Weapons/Spellbook/SpellbookComponent.h"
#include "Monsters/FPSCombatHealthComponent.h"
#include "Multiplayer/ColdSteelAuthorityContext.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "TimerManager.h"

float AFPSGAMECharacter::GetReloadSeconds(bool bEmpty) const
{
    const float Native=bEmpty?EmptyReloadDuration:ReloadDuration;
    if(!IsPistolWeapon()||HasOffhandPistol())return Native;
    const auto* Profile=ColdSteelAuthority::ForPawn(this);
    const auto* Main=Profile?Profile->Equipped():nullptr;
    if(!Main||Main->InstanceId!=ActiveInventoryWeapon||Profile->ActiveProductionTool())return Native;
    const auto* Off=Profile->Equipped(Main->Cell==6?8:11);
    // The authority's shot/reload ledger must price the same handling time as
    // the owning client, using this pawn's shadow profile rather than the host's.
    return Off&&!ColdSteelInventory::IsDualPistol(*Off)
        ?Native+FOffhandReloadHandoff::LowerSeconds+FOffhandReloadHandoff::RaiseSeconds:Native;
}

float AFPSGAMECharacter::GetOffhandReloadLowerWeight() const
{
    return GetWorld()?OffhandReload.LowerWeight(GetWorld()->GetTimeSeconds()):0.f;
}
float AFPSGAMECharacter::GetOffhandReloadProgress() const
{
    return GetWorld()?OffhandReload.Progress(GetWorld()->GetTimeSeconds()):0.f;
}

bool AFPSGAMECharacter::TryBeginOffhandReload()
{
    // This call re-enters ReloadPressed only after the lower stage has ended.
    if(OffhandReload.Phase==EOffhandReloadPhase::Reload)return false;
    if(OffhandReload.Active())return true;
    if(!bInventoryWeaponReady||!IsPistolWeapon()||HasOffhandPistol())return false;
    const auto* Profile=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    const auto* Main=Profile?Profile->Equipped():nullptr;
    if(!Main||Main->InstanceId!=ActiveInventoryWeapon||Profile->ActiveProductionTool())return false;
    const int32 Slot=Main->Cell==6?8:11;
    const auto* Off=Profile->Equipped(Slot);
    // Equipment identity, not spellbook type or current mesh visibility, owns
    // this cost. Future non-pistol offhands use the same action gate.
    if(!Off||ColdSteelInventory::IsDualPistol(*Off))return false;
    if(Spellbook)Spellbook->CancelFocus();
    OffhandReload.Phase=EOffhandReloadPhase::Lower;
    OffhandReload.Weapon=Main->InstanceId;OffhandReload.Offhand=Off->InstanceId;OffhandReload.Slot=Slot;
    OffhandReload.StartedAt=GetWorld()->GetTimeSeconds();
    GetWorldTimerManager().ClearTimer(FireTimerHandle);SetAimingState(false);
    bRevolverReloadAfterFire=bReloadAfterCasting=false;
    return true;
}

void AFPSGAMECharacter::ReturnOffhandAfterReload()
{
    if(!OffhandReload.Active()||OffhandReload.Phase==EOffhandReloadPhase::Raise)return;
    if(OffhandReload.bEarlyReturn)
    {
        // The left hand is already taking the offhand. Finishing the native
        // clip must not restart that return or briefly restore the pistol grip.
        OffhandReload.Phase=EOffhandReloadPhase::Raise;OffhandReload.StartedAt=OffhandReload.ReturnStartedAt;return;
    }
    const double Now=GetWorld()->GetTimeSeconds();
    OffhandReload.bReloadArmExit=OffhandReload.Phase==EOffhandReloadPhase::Reload&&IsReloading();
    // The empty hand may already be reaching the gun at the end of lowering.
    // Cancelling there must recover that displayed hand before revealing the book.
    OffhandReload.bReturnFromReload=OffhandReload.Phase==EOffhandReloadPhase::Reload||
        (OffhandReload.Phase==EOffhandReloadPhase::Lower&&OffhandReload.Progress(Now)>=FOffhandReloadHandoff::BodyLowerTransferStart);
    OffhandReload.ReturnWeight=OffhandReload.LowerWeight(Now);
    OffhandReload.RaiseDuration=FOffhandReloadHandoff::RaiseSeconds*OffhandReload.ReturnWeight;
    OffhandReload.StartedAt=Now;OffhandReload.Phase=EOffhandReloadPhase::Raise;
}

void AFPSGAMECharacter::BeginOffhandReloadReturnIfReady(float SourceTime)
{
    // AdvanceReloadStages calls this only after any required cycle is completed.
    if(OffhandReload.Phase!=EOffhandReloadPhase::Reload||OffhandReload.bEarlyReturn||!bReloadAmmoCommitted)return;
    // M1911/G18/Pit Viper share the native 120 fps magazine contacts. Normal
    // loading must also finish the seat at 128; empty loading keeps slide release.
    const float Release=bUseM1911&&!bPendingEmptyReload?FMath::Max(ReloadStages.Ready,128.f/120.f):ReloadStages.Ready;
    if(SourceTime<Release+2.f/120.f)return;
    const double Now=GetWorld()->GetTimeSeconds();
    OffhandReload.bEarlyReturn=OffhandReload.bReturnFromReload=OffhandReload.bReloadArmExit=true;
    OffhandReload.ReturnStartedAt=Now;OffhandReload.ReturnWeight=1.f;
    // The hand skips the regrip tail, but gameplay keeps the existing deadline.
    OffhandReload.RaiseDuration=FMath::Max(0.f,float(WeaponActionStartedAt+WeaponStateDuration-Now))+FOffhandReloadHandoff::RaiseSeconds;
}

void AFPSGAMECharacter::CancelOffhandReload()
{
    if(!OffhandReload.Active())return;
    OffhandReload=FOffhandReloadHandoff();
    PendingAmmoType.Reset();PendingAmmoWeapon.Reset();
    bReloadAfterCasting=bRevolverReloadAfterFire=false;
}

void AFPSGAMECharacter::AdvanceOffhandReload()
{
    if(!OffhandReload.Active())return;
    const auto* Profile=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    const auto* Off=Profile?Profile->Equipped(OffhandReload.Slot):nullptr;
    const auto* Health=FindComponentByClass<UFPSCombatHealthComponent>();
    if(!bInventoryWeaponReady||!IsPistolWeapon()||HasOffhandPistol()||ActiveInventoryWeapon!=OffhandReload.Weapon||
        !Off||Off->InstanceId!=OffhandReload.Offhand||IsTraversing()||(Health&&Health->IsDead())||
        AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(GetController())))
    {
        CancelOffhandReload();InterruptReload();return;
    }
    const double Now=GetWorld()->GetTimeSeconds();
    if(OffhandReload.Phase==EOffhandReloadPhase::Lower&&Now-OffhandReload.StartedAt>=FOffhandReloadHandoff::LowerSeconds)
    {
        OffhandReload.Phase=EOffhandReloadPhase::Reload;
        ReloadPressed();
        // Eligibility or an unavailable clip may reject the deferred reload.
        // Release the pending ammo selection as well as the visual handoff.
        if(!IsReloading())
        {PendingAmmoType.Reset();PendingAmmoWeapon.Reset();ReturnOffhandAfterReload();}
    }
    else if(OffhandReload.Phase==EOffhandReloadPhase::Raise&&Now-OffhandReload.StartedAt>=OffhandReload.RaiseDuration)
    {
        OffhandReload=FOffhandReloadHandoff();
        SetAimingState(bAimHeld);ResumeWeaponPose();
    }
}
