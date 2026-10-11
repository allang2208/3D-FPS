#include "FPSGAMECharacter.h"
#include "Weapons/Super90WeaponAssets.h"
#include "Weapons/Super90SpeedloaderAssets.h"
#include "Weapons/Super90LoaderPushTiming.h"
#include "UI/ColdSteelStatusModel.h"
#include "Animation/AnimSequence.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "TimerManager.h"

namespace
{
// Pace the ordinary empty tail independently from the unchanged shell feeds.
// The source clock still owns both hands, grip deltas, the bolt and sound cues.
constexpr float NativeEmptyTailPace = 2.16f;
constexpr float NativeCyclePaceStart = .36f;
float NativeEmptyTailSourceTime(float PaceTime)
{
    struct FKnot { float Pace; float Source; float Slope; };
    // Positive monotone Hermite tangents avoid a stop at every phase boundary.
    static constexpr FKnot Knots[] = {
        {0.f, 0.f, 1.f},                                  // Last shell seated
        {.36f, .3f, .672718808f},                          // Right hand regripped
        {1.02f, .659615385f, .671927995f},                 // Left grasp established
        {1.24f, .836981900f, .710573668f},                 // Pull cue
        {1.40f, .939706450f, .698404430f},                 // Release cue
        {1.45f, .976923077f, .483721508f},                 // Bolt closed
        {1.51f, .998076923f, .417424620f},                 // Hand clearing handle
        {NativeEmptyTailPace, 1.4f, .861662083f}           // Back on foregrip
    };
    const float Time = FMath::Clamp(PaceTime, 0.f, NativeEmptyTailPace);
    for (int32 I = 1; I < UE_ARRAY_COUNT(Knots); ++I)
    {
        const FKnot& A = Knots[I - 1];
        const FKnot& B = Knots[I];
        if (Time > B.Pace) continue;
        const float Span = B.Pace - A.Pace;
        const float T = (Time - A.Pace) / Span;
        const float T2 = T * T, T3 = T2 * T;
        return (2.f * T3 - 3.f * T2 + 1.f) * A.Source
            + (T3 - 2.f * T2 + T) * Span * A.Slope
            + (-2.f * T3 + 3.f * T2) * B.Source
            + (T3 - T2) * Span * B.Slope;
    }
    return Knots[UE_ARRAY_COUNT(Knots) - 1].Source;
}
}

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
        ?Super90SpeedloaderAssets::EmptyReference/FMath::Max(.01f,EmptyReloadDuration)
        :Super90SpeedloaderAssets::NormalReference/FMath::Max(.01f,ReloadDuration);
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
    if(!bSuper90SpeedReload && bPendingEmptyReload)
        WeaponStateDuration=(CycleOnly?NativeEmptyTailPace-NativeCyclePaceStart:Super90ReloadTail+NativeEmptyTailPace)/Super90ReloadRate;
    PlayWeaponAnimation(Clip,false,Super90ReloadRate);
    ActionDuration=WeaponStateDuration;
    UpdateSuper90SpeedloaderVisual();
    if(bSuper90SpeedReload)
    {
        SetSuper90LoaderCues();return;
    }
    const float BoltCueOffset=CycleOnly?NativeCycleBegin:0.f;
    ReloadStages={Insert,TailBegin,BoltRelease-BoltCueOffset};
    MechanicalCueTimes.Reset();MechanicalCueSounds.Reset();NextMechanicalCue=0;
    for(int32 I=0;I<Super90ReloadCount;++I)
    {
        MechanicalCueTimes.Add(Insert+I*LoopStep);
        MechanicalCueSounds.Add(MagInsertSound);
    }
    if(bPendingEmptyReload)
    {
        MechanicalCueTimes.Append({BoltPull-BoltCueOffset,NativeBoltReleaseCue-BoltCueOffset});
        MechanicalCueSounds.Append({ChargePullSound,ChargeReleaseSound});
    }
}

float AFPSGAMECharacter::Super90ReloadSourceTime(float RuntimeTime) const
{
    using namespace Super90WeaponAssets;
    const float Time=FMath::Max(0.f,RuntimeTime)*Super90ReloadRate;
    if(bSuper90SpeedReload)
        return FMath::Min(Super90ReloadCount>0?Super90LoaderPushTiming::SourceTime(Time):Time,Super90SingleLength);
    if(bReloadCycleOnly)
        return FMath::Clamp(NativeEmptyTailSourceTime(Time+NativeCyclePaceStart)-(NativeCycleBegin-TailBegin),0.f,Super90SingleLength);
    if(bPendingEmptyReload && Time>=Super90ReloadTail)
        return FMath::Min(Super90SingleLength,TailBegin+NativeEmptyTailSourceTime(Time-Super90ReloadTail));
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
        const float LoaderSourceTime=Super90ReloadSourceTime(WeaponStateElapsed);
        // Fire/aim requests must not turn a full loader stroke into a one-shell
        // reload. Commit the entire prepared fill atomically when seated, using
        // the inventory transaction for reserves, training and pending bolt state.
        if(!bReloadAmmoCommitted && Super90ReloadCount>0 && LoaderSourceTime+1.e-6f>=LastContact(Super90ReloadCount))
        {
            const int32 Loaded=Profile->ConsumeAmmo(Super90ReloadCount,true,false,bPendingEmptyReload?1:0);
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
            if(bPendingEmptyReload)
                WeaponStateDuration=ActionDuration=(Super90ReloadTail+NativeEmptyTailPace)/Super90ReloadRate;
            MechanicalCueTimes.SetNum(StopAfter);MechanicalCueSounds.SetNum(StopAfter);
            if(bPendingEmptyReload)
            {
                MechanicalCueTimes.Append({BoltPull,NativeBoltReleaseCue});
                MechanicalCueSounds.Append({ChargePullSound,ChargeReleaseSound});
            }
        }
    }
    while(Super90ReloadCommitted<Super90ReloadCount && FeedTime+1.e-6f>=Insert+Super90ReloadCommitted*LoopStep)
    {
        const bool Final=Super90ReloadCommitted+1==Super90ReloadCount;
        if(Profile->ConsumeAmmo(1,Final,true,bPendingEmptyReload?1:0)!=1){InterruptReload();return false;}
        ++Super90ReloadCommitted;bReloadAmmoCommitted=true;
    }
    const float Ready= BoltRelease-(bReloadCycleOnly?NativeCycleBegin:0.f);
    if(bPendingEmptyReload && Super90ReloadSourceTime(WeaponStateElapsed)+1.e-6f>=Ready && NeedsReloadCycle())
        if(!Profile->CompleteWeaponReloadCycle(ActiveInventoryWeapon)){InterruptReload();return false;}
    UpdateSuper90SpeedloaderVisual();
    return true;
}

void AFPSGAMECharacter::FinishSuper90Reload()
{
    RecoilPatternIndex=0;bPendingEmptyReload=false;
    FinishWeaponAction();
}
