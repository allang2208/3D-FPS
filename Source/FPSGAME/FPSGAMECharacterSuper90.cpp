#include "FPSGAMECharacter.h"
#include "Weapons/Super90WeaponAssets.h"
#include "Weapons/Super90SpeedloaderAssets.h"
#include "UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "TimerManager.h"

void AFPSGAMECharacter::BeginSuper90Reload()
{
    using namespace Super90WeaponAssets;
    if(!bInventoryWeaponReady || IsWeaponBusy() || IsCastBlockingLeftHandAction())return;
    const bool CycleOnly=NeedsReloadCycle();
    if(!CycleOnly && (MagazineAmmo>=MagazineCapacity || (!HasInfiniteReserveAmmo()&&ReserveAmmo<=0)))return;
    // Preserve only the final recoil window, not the source's appended inspection.
    if(IsRevolverFireActionPlaying()){bRevolverReloadAfterFire=true;return;}
    bRevolverReloadAfterFire=false;
    bPendingEmptyReload=CycleOnly||MagazineAmmo==0;
    // One action owns the raise, every shell, and the final return to the grip.
    // The normal variant keeps the bolt closed throughout the same feed loops.
    Super90ReloadCount=CycleOnly?0:FMath::Min(MagazineCapacity-MagazineAmmo,HasInfiniteReserveAmmo()?MagazineCapacity:ReserveAmmo);
    bSuper90SpeedReload=bSuper90LoaderInstalled;
    UAnimSequence* Clip=bPendingEmptyReload?ReloadEmptyAnimation.Get():ReloadAnimation.Get();
    if(bSuper90SpeedReload)
    {
        Super90ReloadCount=FMath::Min(Super90ReloadCount,Super90SpeedloaderAssets::Capacity);
        const auto& Clips=bPendingEmptyReload?Super90LoaderEmpty:Super90LoaderNormal;
        Clip=Clips.IsValidIndex(Super90ReloadCount)?Clips[Super90ReloadCount].Get():nullptr;
    }
    Super90SingleLength=Clip?Clip->GetPlayLength():SingleReload;
    if(!Clip){bSuper90SpeedReload=false;return;}
    Super90ReloadCommitted=0;
    bSuper90CancelReload=false;
    bReloadCycleOnly=CycleOnly;
    bReloadAmmoCommitted=CycleOnly;
    bReloadAfterCasting=false;
    ReloadResumeElapsed=0.f;
    StopMechanicalAudio();
    SetAimingState(false);
    ExitSprintForWeapon();
    GetWorldTimerManager().ClearTimer(FireTimerHandle);
    // Normal reload stats still describe one shell, not an entire seven-shell fill.
    Super90ReloadRate=bPendingEmptyReload?FullReload/FMath::Max(.01f,EmptyReloadDuration):SingleReload/FMath::Max(.01f,ReloadDuration);
    if(bSuper90SpeedReload)Super90ReloadRate=bPendingEmptyReload
        ?Super90SpeedloaderAssets::EmptyReference/FMath::Max(.01f,EmptyReloadDuration)
        :Super90SpeedloaderAssets::NormalReference/FMath::Max(.01f,ReloadDuration);
    Super90ReloadTail=TailForCount(Super90ReloadCount);
    WeaponState=bPendingEmptyReload?EAKMWeaponState::ReloadingEmpty:EAKMWeaponState::Reloading;
    WeaponActionStartedAt=GetWorld()->GetTimeSeconds();
    WeaponStateElapsed=0.f;
    WeaponStateDuration=(Super90ReloadTail+Super90SingleLength-TailBegin)/Super90ReloadRate;
    if(bSuper90SpeedReload)WeaponStateDuration=Super90SingleLength/Super90ReloadRate;
    PlayWeaponAnimation(Clip,false,Super90ReloadRate);
    ActionDuration=WeaponStateDuration;
    UpdateSuper90SpeedloaderVisual();
    if(bSuper90SpeedReload)
    {
        SetSuper90LoaderCues();return;
    }
    ReloadStages={Insert,TailBegin,BoltRelease};
    MechanicalCueTimes.Reset();MechanicalCueSounds.Reset();NextMechanicalCue=0;
    for(int32 I=0;I<Super90ReloadCount;++I)
    {
        MechanicalCueTimes.Add(Insert+I*LoopStep);
        MechanicalCueSounds.Add(MagInsertSound);
    }
    if(bPendingEmptyReload){MechanicalCueTimes.Add(BoltRelease);MechanicalCueSounds.Add(ChargeReleaseSound);}
}

float AFPSGAMECharacter::Super90ReloadSourceTime(float RuntimeTime) const
{
    using namespace Super90WeaponAssets;
    const float Time=FMath::Max(0.f,RuntimeTime)*Super90ReloadRate;
    if(bSuper90SpeedReload)return FMath::Min(Time,Super90SingleLength);
    // Skip unused feed loops only once, after the last shell. Both variants
    // stay canted until this boundary; only the empty variant closes the bolt.
    return Time>=Super90ReloadTail
        ? FMath::Min(Super90SingleLength,TailBegin+Time-Super90ReloadTail)
        : FMath::Min(Time,Super90SingleLength);
}

bool AFPSGAMECharacter::AdvanceSuper90Reload()
{
    using namespace Super90WeaponAssets;
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile||!ActiveActionAnimation){InterruptReload();return false;}
    // Contacts use the uncut clock. Jumping to the animation tail must never
    // commit shells whose source frames were skipped.
    const float FeedTime=WeaponStateElapsed*Super90ReloadRate;
    if(bSuper90SpeedReload)
    {
        using namespace Super90SpeedloaderAssets;
        if(bSuper90CancelReload && Super90ReloadCommitted<Super90ReloadCount)
        {
            // Count variants have identical poses until this shell seats. Keep
            // the clock and change only the following withdrawal/return tail.
            const int32 StopAfter=FMath::Min(Super90ReloadCommitted+1,Super90ReloadCount);
            if(StopAfter<Super90ReloadCount)
            {
                const auto& Clips=bPendingEmptyReload?Super90LoaderEmpty:Super90LoaderNormal;
                Super90ReloadCount=StopAfter;ActiveActionAnimation=Clips[StopAfter];
                Super90SingleLength=ActiveActionAnimation->GetPlayLength();
                WeaponStateDuration=ActionDuration=Super90SingleLength/Super90ReloadRate;
                SetSuper90LoaderCues();
            }
        }
        while(Super90ReloadCommitted<Super90ReloadCount && FeedTime+1.e-6f>=Super90SpeedloaderAssets::Insert+Super90ReloadCommitted*Step)
        {
            const bool Final=Super90ReloadCommitted+1==Super90ReloadCount;
            if(Profile->ConsumeAmmo(1,Final,true,bPendingEmptyReload?1:0)!=1){InterruptReload();return false;}
            ++Super90ReloadCommitted;bReloadAmmoCommitted=true;
        }
        if(bPendingEmptyReload && FeedTime+1.e-6f>=Release(Super90ReloadCount) && NeedsReloadCycle())
            if(!Profile->CompleteWeaponReloadCycle(ActiveInventoryWeapon)){InterruptReload();return false;}
        UpdateSuper90SpeedloaderVisual();return true;
    }
    if(bSuper90CancelReload && Super90ReloadCount>0)
    {
        // Seat the shell already in hand, then leave the loop. A request in
        // the short post-insert window can return without fetching another.
        const int32 StopAfter=FMath::Clamp(Super90ReloadCommitted+
            (FeedTime>TailForCount(Super90ReloadCommitted)+1.e-6f?1:0),1,Super90ReloadCount);
        if(StopAfter<Super90ReloadCount)
        {
            Super90ReloadCount=StopAfter;
            Super90ReloadTail=TailForCount(StopAfter);
            WeaponStateDuration=ActionDuration=(Super90ReloadTail+Super90SingleLength-TailBegin)/Super90ReloadRate;
            MechanicalCueTimes.SetNum(StopAfter);MechanicalCueSounds.SetNum(StopAfter);
            if(bPendingEmptyReload){MechanicalCueTimes.Add(BoltRelease);MechanicalCueSounds.Add(ChargeReleaseSound);}
        }
    }
    while(Super90ReloadCommitted<Super90ReloadCount && FeedTime+1.e-6f>=Insert+Super90ReloadCommitted*LoopStep)
    {
        const bool Final=Super90ReloadCommitted+1==Super90ReloadCount;
        if(Profile->ConsumeAmmo(1,Final,true,bPendingEmptyReload?1:0)!=1){InterruptReload();return false;}
        ++Super90ReloadCommitted;bReloadAmmoCommitted=true;
    }
    if(bPendingEmptyReload && Super90ReloadSourceTime(WeaponStateElapsed)+1.e-6f>=BoltRelease && NeedsReloadCycle())
        if(!Profile->CompleteWeaponReloadCycle(ActiveInventoryWeapon)){InterruptReload();return false;}
    UpdateSuper90SpeedloaderVisual();
    return true;
}

void AFPSGAMECharacter::FinishSuper90Reload()
{
    RecoilPatternIndex=0;bPendingEmptyReload=false;
    FinishWeaponAction();
}
