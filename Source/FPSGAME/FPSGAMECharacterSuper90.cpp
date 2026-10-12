#include "FPSGAMECharacter.h"
#include "Weapons/Super90WeaponAssets.h"
#include "Weapons/Super90SpeedloaderAssets.h"
#include "Weapons/Super90LoaderPushTiming.h"
#include "UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "TimerManager.h"
#include "Multiplayer/ColdSteelPlayerState.h"

void AFPSGAMECharacter::BeginSuper90Reload()
{
    using namespace Super90WeaponAssets;
    // Remote pawns are reloaded by PlayerState authority, never by their
    // automatic empty-magazine tick against the host's local inventory.
    if(!IsLocallyControlled()&&GetNetMode()!=NM_Standalone)return;
    if(!bInventoryWeaponReady || IsWeaponBusy() || IsCastBlockingLeftHandAction())return;
    auto* PS=GetPlayerState<AColdSteelPlayerState>();
    if(GetNetMode()==NM_Client&&(!PS||!PS->IsSuper90ServerReady(ActiveInventoryWeapon)||PS->IsSuper90ReloadPending()))return;
    auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const bool Switching=!PendingAmmoType.IsEmpty();
    if(Switching&&(!Profile||!Profile->CanSwitchAmmo(PendingAmmoWeapon,PendingAmmoType)))return;
    const bool CycleOnly=!Switching&&NeedsReloadCycle();
    if(!Switching&&!CycleOnly && (MagazineAmmo>=MagazineCapacity || (!HasInfiniteReserveAmmo()&&ReserveAmmo<=0)))return;
    // Preserve only the final recoil window, not the source's appended inspection.
    if(IsRevolverFireActionPlaying()){bRevolverReloadAfterFire=true;return;}
    bRevolverReloadAfterFire=false;
    bPendingEmptyReload=Switching||CycleOnly||MagazineAmmo==0;
    // One action owns the raise, every shell, and the final return to the grip.
    // The normal variant keeps the bolt closed throughout the same feed loops.
    const int32 Available=Switching?int32(FMath::Min<int64>(MagazineCapacity,Profile->PouchCount(PendingAmmoType)))
        :HasInfiniteReserveAmmo()?MagazineCapacity:ReserveAmmo;
    Super90ReloadCount=CycleOnly?0:FMath::Min(MagazineCapacity-(Switching?0:MagazineAmmo),Available);
    bSuper90SpeedReload=bSuper90LoaderInstalled;
    UAnimSequence* Clip=bPendingEmptyReload?ReloadEmptyAnimation.Get():ReloadAnimation.Get();
    if(bSuper90SpeedReload)
    {
        // The loader refills the magazine in one push. Its authored shell
        // variants cap the visual count, never the amount the weapon can take.
        const int32 ClipCount=FMath::Min(Super90ReloadCount,Super90SpeedloaderAssets::Capacity);
        const auto& Clips=bPendingEmptyReload?Super90LoaderEmpty:Super90LoaderNormal;
        Clip=Clips.IsValidIndex(ClipCount)?Clips[ClipCount].Get():nullptr;
    }
    else if(CycleOnly)
    {
        // A resumed pending chamber needs the cycle itself, without replaying
        // the feeding hand's return or displaying any loader props.
        Clip=Super90LoaderEmpty.IsValidIndex(0)?Super90LoaderEmpty[0].Get():nullptr;
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
        ?Super90SpeedloaderAssets::EmptyPacedReference/FMath::Max(.01f,EmptyReloadDuration)
        :Super90SpeedloaderAssets::NormalPacedReference/FMath::Max(.01f,ReloadDuration);
    // Native shell loops use a tail boundary; loader presentation retains its
    // original contact clock while ammo commits once at the end of the push.
    Super90ReloadTail=bSuper90SpeedReload?Super90SpeedloaderAssets::FirstContact(Super90ReloadCount):TailForCount(Super90ReloadCount);
    WeaponState=bPendingEmptyReload?EAKMWeaponState::ReloadingEmpty:EAKMWeaponState::Reloading;
    WeaponActionStartedAt=GetWorld()->GetTimeSeconds();
    WeaponStateElapsed=0.f;
    WeaponStateDuration=(Super90ReloadTail+Super90SingleLength-TailBegin)/Super90ReloadRate;
    if(bSuper90SpeedReload||CycleOnly)WeaponStateDuration=Super90SingleLength/Super90ReloadRate;
    if(bSuper90SpeedReload && Super90ReloadCount>0)
        WeaponStateDuration=(Super90SingleLength+Super90LoaderPushTiming::ExtraDuration)/Super90ReloadRate;
    PlayWeaponAnimation(Clip,false,Super90ReloadRate);
    ActionDuration=WeaponStateDuration;
    if(GetNetMode()==NM_Client)PS->RequestSuper90Reload(ActiveInventoryWeapon,PendingAmmoType);
    UpdateSuper90SpeedloaderVisual();
    SetSuper90ReloadCues();
}

void AFPSGAMECharacter::SetSuper90ReloadCues()
{
    using namespace Super90WeaponAssets;
    if(bSuper90SpeedReload)
    {
        SetSuper90LoaderCues();return;
    }
    ReloadStages={Insert,TailBegin,bReloadCycleOnly?CycleBoltReady:BoltRelease};
    MechanicalCueTimes.Reset();MechanicalCueSounds.Reset();NextMechanicalCue=0;
    for(int32 I=0;I<Super90ReloadCount;++I)
    {
        MechanicalCueTimes.Add(Insert+I*LoopStep);
        MechanicalCueSounds.Add(MagInsertSound);
    }
    if(bPendingEmptyReload)
    {
        if(bReloadCycleOnly)
        {
            MechanicalCueTimes.Add(CycleBoltReleaseCue);
            MechanicalCueSounds.Add(ChargeReleaseSound);
        }
        else
        {
            MechanicalCueTimes.Add(NativeBoltReleaseCue);
            MechanicalCueSounds.Add(ChargeReleaseSound);
        }
    }
    const float SourceTime=Super90ReloadSourceTime(WeaponStateElapsed);
    while(NextMechanicalCue<MechanicalCueTimes.Num()&&MechanicalCueTimes[NextMechanicalCue]<SourceTime)
        ++NextMechanicalCue;
}

void AFPSGAMECharacter::ReconcileSuper90Reload(const FSuper90NetAmmoState& Receipt)
{
    if(!IsSuper90Weapon()||!IsReloading()||ActiveInventoryWeapon!=Receipt.ReloadWeapon)return;
    // Once accepted, the server's stop boundary wins over the earlier local
    // prediction. Re-running that prediction would shorten the plan again.
    if(Receipt.ReloadStopRequested)bSuper90CancelReload=false;
    if(Super90ReloadCount==Receipt.ReloadCount&&bPendingEmptyReload==Receipt.ReloadEmpty
        &&bSuper90SpeedReload==Receipt.ReloadLoader&&bReloadCycleOnly==Receipt.ReloadCycleOnly
        &&FMath::IsNearlyEqual(Super90ReloadRate,Receipt.ReloadRate))return;

    using namespace Super90WeaponAssets;
    UAnimSequence* Clip=Receipt.ReloadEmpty?ReloadEmptyAnimation.Get():ReloadAnimation.Get();
    if(Receipt.ReloadLoader||Receipt.ReloadCycleOnly)
    {
        const auto& Clips=Receipt.ReloadEmpty?Super90LoaderEmpty:Super90LoaderNormal;
        const int32 Index=FMath::Min(Receipt.ReloadCount,Super90SpeedloaderAssets::Capacity);
        Clip=Clips.IsValidIndex(Index)?Clips[Index].Get():nullptr;
    }
    if(!Clip)return;
    // Preserve the in-progress feed clock; never restart the accepted gesture
    // or re-consume ammunition when a count/rate correction arrives.
    const float FeedTime=WeaponStateElapsed*Super90ReloadRate;
    Super90ReloadCount=Receipt.ReloadCount;
    Super90ReloadCommitted=FMath::Min(Super90ReloadCommitted,Super90ReloadCount);
    bPendingEmptyReload=Receipt.ReloadEmpty;bSuper90SpeedReload=Receipt.ReloadLoader;
    bReloadCycleOnly=Receipt.ReloadCycleOnly;
    Super90ReloadRate=Receipt.ReloadRate;Super90SingleLength=Clip->GetPlayLength();
    Super90ReloadTail=bSuper90SpeedReload?Super90SpeedloaderAssets::FirstContact(Super90ReloadCount):TailForCount(Super90ReloadCount);
    WeaponState=bPendingEmptyReload?EAKMWeaponState::ReloadingEmpty:EAKMWeaponState::Reloading;
    WeaponStateElapsed=FeedTime/Super90ReloadRate;
    WeaponActionStartedAt=GetWorld()->GetTimeSeconds()-WeaponStateElapsed;
    WeaponStateDuration=(Super90ReloadTail+Super90SingleLength-TailBegin)/Super90ReloadRate;
    if(bSuper90SpeedReload||bReloadCycleOnly)
        WeaponStateDuration=(Super90SingleLength+(bSuper90SpeedReload&&Super90ReloadCount>0?Super90LoaderPushTiming::ExtraDuration:0.f))/Super90ReloadRate;
    PlayWeaponAnimation(Clip,false,Super90ReloadRate);
    ActionElapsed=WeaponStateElapsed;ActionDuration=WeaponStateDuration;
    SetSuper90ReloadCues();UpdateSuper90SpeedloaderVisual();
}

float AFPSGAMECharacter::Super90ReloadSourceTime(float RuntimeTime) const
{
    using namespace Super90WeaponAssets;
    const float Time=FMath::Max(0.f,RuntimeTime)*Super90ReloadRate;
    if(bSuper90SpeedReload)
        return FMath::Min(Super90ReloadCount>0?Super90LoaderPushTiming::SourceTime(Time):Time,Super90SingleLength);
    if(bReloadCycleOnly)
        return FMath::Min(Time,Super90SingleLength);
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
    const bool NetworkOwner=GetNetMode()==NM_Client;
    if(NetworkOwner&&bSuper90CancelReload)
        if(auto* PS=GetPlayerState<AColdSteelPlayerState>())PS->CancelSuper90Reload(true);
    if(bSuper90SpeedReload)
    {
        using namespace Super90SpeedloaderAssets;
        const float LoaderSourceTime=Super90ReloadSourceTime(WeaponStateElapsed);
        if(NetworkOwner)
        {
            if(Super90ReloadCount>0&&LoaderSourceTime+1.e-6f>=LastContact(Super90ReloadCount))
            {Super90ReloadCommitted=Super90ReloadCount;bReloadAmmoCommitted=true;PendingAmmoType.Reset();PendingAmmoWeapon.Reset();}
            UpdateSuper90SpeedloaderVisual();return true;
        }
        // Fire/aim requests must not turn a full loader stroke into a one-shell
        // reload. Commit the entire prepared fill atomically when seated, using
        // the inventory transaction for reserves, training and pending bolt state.
        if(!bReloadAmmoCommitted && Super90ReloadCount>0 && LoaderSourceTime+1.e-6f>=LastContact(Super90ReloadCount))
        {
            int32 Loaded=0;
            if(!PendingAmmoType.IsEmpty())
            {
                // Refund the previous tube only when the new loader seats.
                if(Profile->CommitAmmoSwitch(PendingAmmoWeapon,PendingAmmoType,MagazineCapacity,1,Super90ReloadCount))
                {
                    if(const auto* Gun=Profile->FindItem(ActiveInventoryWeapon))Loaded=Gun->Magazine;
                    PendingAmmoType.Reset();PendingAmmoWeapon.Reset();
                }
            }
            else Loaded=Profile->ConsumeAmmo(Super90ReloadCount,true,false,bPendingEmptyReload?1:0);
            if(Loaded<=0){InterruptReload();return false;}
            Super90ReloadCommitted=Loaded;bReloadAmmoCommitted=true;
        }
        if(bPendingEmptyReload && LoaderSourceTime+1.e-6f>=Release(Super90ReloadCount) && NeedsReloadCycle())
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
            if(bPendingEmptyReload)
            {
                MechanicalCueTimes.Add(NativeBoltReleaseCue);
                MechanicalCueSounds.Add(ChargeReleaseSound);
            }
        }
    }
    while(Super90ReloadCommitted<Super90ReloadCount && FeedTime+1.e-6f>=Insert+Super90ReloadCommitted*LoopStep)
    {
        const bool Final=Super90ReloadCommitted+1==Super90ReloadCount;
        // The first seated shell changes the whole tube type atomically; later
        // shell contacts use the ordinary per-shell path and can be interrupted.
        const bool Switching=!PendingAmmoType.IsEmpty();
        if(NetworkOwner)
        {
            // Animation contacts only. The server receipt owns pouch, magazine,
            // selected ammunition and bolt-ready state.
            ++Super90ReloadCommitted;bReloadAmmoCommitted=true;
            PendingAmmoType.Reset();PendingAmmoWeapon.Reset();continue;
        }
        const bool Loaded=Switching
            ?Profile->CommitAmmoSwitch(PendingAmmoWeapon,PendingAmmoType,MagazineCapacity,1,1,Final)
            :Profile->ConsumeAmmo(1,Final,true,bPendingEmptyReload?1:0)==1;
        if(!Loaded){InterruptReload();return false;}
        if(Switching){PendingAmmoType.Reset();PendingAmmoWeapon.Reset();}
        ++Super90ReloadCommitted;bReloadAmmoCommitted=true;
    }
    const float Ready=bReloadCycleOnly?CycleBoltReady:BoltRelease;
    if(!NetworkOwner&&bPendingEmptyReload && Super90ReloadSourceTime(WeaponStateElapsed)+1.e-6f>=Ready && NeedsReloadCycle())
        if(!Profile->CompleteWeaponReloadCycle(ActiveInventoryWeapon)){InterruptReload();return false;}
    UpdateSuper90SpeedloaderVisual();
    return true;
}

void AFPSGAMECharacter::FinishSuper90Reload()
{
    RecoilPatternIndex=0;bPendingEmptyReload=false;
    FinishWeaponAction();
}
