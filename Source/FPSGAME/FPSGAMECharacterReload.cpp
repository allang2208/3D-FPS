#include "FPSGAMECharacter.h"
#include "FPSGAMEPlayerController.h"
#include "UI/ColdSteelStatusModel.h"
#include "Weapons/DanWesson715WeaponAssets.h"
#include "Weapons/RSH12WeaponAssets.h"
#include "Weapons/FPSGunplayAnimInstance.h"
#include "Weapons/LMG201WeaponAssets.h"
#include "Weapons/PistolDualWieldComponent.h"
#include "Monsters/FPSCombatHealthComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

bool AFPSGAMECharacter::NeedsReloadCycle() const
{
    const auto* Profile=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    const auto* Item=Profile?Profile->FindItem(ActiveInventoryWeapon):nullptr;
    return Item && WeaponReloadStages::NeedsCycle(*Item);
}

void AFPSGAMECharacter::NotifyCowboyReload()
{
    if(const UWorld* World=GetWorld())CowboyReloadHintUntil=World->GetTimeSeconds()+2.0;
}

float AFPSGAMECharacter::GetCowboyReloadHintOpacity() const
{
    const UWorld* World=GetWorld();
    return World?FMath::Clamp(float((CowboyReloadHintUntil-World->GetTimeSeconds())/.3),0.f,1.f):0.f;
}

void AFPSGAMECharacter::TryCowboyReload()
{
    if(DualPistols && DualPistols->IsActive())
    {
        DualPistols->TryCowboyReload();
        return;
    }
    if(!bInventoryWeaponReady || !IsPistolWeapon())return;
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const FString WeaponId=ActiveInventoryWeapon;
    if(!Profile || Profile->ReloadCowboyPistol(WeaponId,MagazineCapacity)<=0)return;
    // Publish ammo first: a failed save or an empty pouch must leave any ongoing
    // reload untouched. Successful publication already refreshed the counters.
    InterruptReload();
    bRevolverReloadAfterFire=bReloadAfterCasting=false;
    PendingAmmoType.Reset();PendingAmmoWeapon.Reset();
    PlaySound2D(bUseDanWesson715?MagOutSound.Get():MagInsertSound.Get(),.8f);
}

void AFPSGAMECharacter::InitializeReloadStages(bool CycleOnly)
{
    ReloadStages=WeaponReloadStages::ForWeapon(ActiveInventoryWeaponDefinition,bPendingEmptyReload,
        bDrumInstalled,bRevolverSingleReload,RevolverReloadCount);
    if(HasLMG201ClothBox())ReloadStages={LMG201WeaponAssets::ClothEventTime(LMG201WeaponAssets::ClothBoxSeat,bPendingEmptyReload),
        LMG201WeaponAssets::ClothEventTime(LMG201WeaponAssets::ClothBoxSeat,bPendingEmptyReload),
        LMG201WeaponAssets::ClothEventTime(LMG201WeaponAssets::ClothCoverClose,bPendingEmptyReload)};
    bReloadCycleOnly=CycleOnly;
    bReloadAmmoCommitted=CycleOnly;
    ReloadResumeElapsed=0.f;
    if(!bUsingM4Infima && !HasLMG201ClothBox() && bPendingEmptyReload && MechanicalCueTimes.Num()>=5)
    {
        // The installed AKM/A762 clips pull at 314 and release at 344 (120 Hz).
        // Keep these audible when resuming at frame 270 instead of replaying
        // the obsolete early charge cues from the original source table.
        MechanicalCueTimes[3]=ReloadRuntimeTime(314.f/120.f);
        MechanicalCueTimes[4]=ReloadRuntimeTime(344.f/120.f);
    }
    if(!CycleOnly)return;
    // Retain the complete source/runtime mapping, including the nonlinear drum
    // clock. Only move its origin; ammo, sounds and camera consume that same clock.
    ReloadResumeElapsed=ReloadRuntimeTime(ReloadStages.CycleBegin);
    WeaponActionStartedAt-=ReloadResumeElapsed;
    WeaponStateElapsed=ActionElapsed=ReloadResumeElapsed;
    RevolverReloadCommitted=RevolverReloadCount;
    bRevolverCasesCleared=true;
    const float CueClock=(bUsingM4Infima||HasLMG201ClothBox())?ReloadStages.CycleBegin:ReloadResumeElapsed;
    while(NextMechanicalCue<MechanicalCueTimes.Num() && MechanicalCueTimes[NextMechanicalCue]<CueClock)
        ++NextMechanicalCue;
}

bool AFPSGAMECharacter::AdvanceReloadStages()
{
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile || !ActiveActionAnimation){InterruptReload();return false;}
    const float Source=ReloadSourceTime(WeaponStateElapsed);
    if(bUseDanWesson715 && !bReloadCycleOnly)
    {
        if(!bRevolverCasesCleared && PendingAmmoType.IsEmpty())
        {
            const float Scale=bRevolverSingleReload?1.f:DanWesson715WeaponAssets::EmptyReload/DanWesson715WeaponAssets::NormalReload;
            const float At=bPendingEmptyReload?DanWesson715WeaponAssets::EmptyCaseClear*Scale:DanWesson715WeaponAssets::Open;
            if(Source+1.e-6f>=At)
            {
                if(!Profile->ClearRevolverSpentCases(!bRevolverSingleReload)){InterruptReload();return false;}
                bRevolverCasesCleared=true;
            }
        }
        if(bRevolverSingleReload)
        {
            while(RevolverReloadCommitted<RevolverReloadCount && Source+1.e-6f>=DanWesson715WeaponAssets::SingleSeatTime(RevolverReloadCommitted,bPendingEmptyReload))
            {
                const bool Last=RevolverReloadCommitted+1==RevolverReloadCount;
                const bool Switching=!PendingAmmoType.IsEmpty();
                const bool Inserted=Switching
                    ? Profile->CommitAmmoSwitch(PendingAmmoWeapon,PendingAmmoType,MagazineCapacity,true,1,Last)
                    : Profile->ConsumeAmmo(1,Last,true,true)==1;
                if(!Inserted){InterruptReload();return false;}
                PendingAmmoType.Reset();PendingAmmoWeapon.Reset();
                bRevolverCasesCleared=true;
                bReloadAmmoCommitted=true;
                ++RevolverReloadCommitted;
            }
        }
    }
    if(!bReloadAmmoCommitted && !(bUseDanWesson715 && bRevolverSingleReload) && Source+1.e-6f>=ReloadStages.Insert)
    {
        const int32 PendingCycle=HasLMG201ClothBox()?2:bPendingEmptyReload || bUseDanWesson715 ? 1
            : (ActiveInventoryWeaponDefinition==TEXT("ue_pkm_lowpoly")) ? 2 : 0;
        const bool Inserted=!PendingAmmoType.IsEmpty()
            ? Profile->CommitAmmoSwitch(PendingAmmoWeapon,PendingAmmoType,MagazineCapacity,PendingCycle)
            : Profile->ConsumeAmmo(MagazineCapacity-MagazineAmmo,true,false,PendingCycle)>0;
        if(!Inserted){InterruptReload();return false;}
        bReloadAmmoCommitted=true;
        PendingAmmoType.Reset();PendingAmmoWeapon.Reset();
    }
    if(bReloadAmmoCommitted && Source+1.e-6f>=ReloadStages.Ready && NeedsReloadCycle())
        if(!Profile->CompleteWeaponReloadCycle(ActiveInventoryWeapon)){InterruptReload();return false;}
    return true;
}

void AFPSGAMECharacter::InterruptReload()
{
    if(WeaponState!=EAKMWeaponState::Reloading && WeaponState!=EAKMWeaponState::ReloadingEmpty)return;
    StopMechanicalAudio();
    WeaponStateDuration=FMath::Max(0.f,float(GetWorld()->GetTimeSeconds()-WeaponActionStartedAt));
    FinishWeaponAction();
    ActiveActionAnimation=nullptr;ActionElapsed=ActionDuration=0.f;
    if(GunplayAnimation)GunplayAnimation->ActionAlpha=0.f;
    bPendingEmptyReload=false;
}

void AFPSGAMECharacter::ServicePendingReloadCycle()
{
    if(IsDualWieldingPistols() || !bInventoryWeaponReady || IsWeaponBusy() || IsChoosingAmmo()
        || IsCastBlockingLeftHandAction() || !NeedsReloadCycle())return;
    if(AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(GetController())))return;
    if(const auto* Health=FindComponentByClass<UFPSCombatHealthComponent>();Health && Health->IsDead())return;
    ReloadPressed();
}
