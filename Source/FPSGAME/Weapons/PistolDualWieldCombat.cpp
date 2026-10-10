#include "G18WeaponAssets.h"
#include "RSH12WeaponAssets.h"
#include "PitViper2011WeaponAssets.h"
#include "PistolDualWieldComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "ColdSteelEnchantmentCombat.h"
#include "FPSWeaponFXComponent.h"
#include "FPSBallisticsComponent.h"
#include "DanWesson715WeaponAssets.h"
#include "WeaponReloadStages.h"
#include "WeaponDamageFalloff.h"
#include "Camera/CameraComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "FPSGunplayAnimInstance.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Perception/AISense_Hearing.h"

// One source of truth for a dual hand's hip cone. Constants live in
// DualPistolSpread (PistolDualWieldComponent.h); the shared reticle reads the
// averaged cone through AFPSGAMECharacter::GetHipSpread().
float UPistolDualWieldComponent::HandConeSpread(int32 Index) const
{
    using namespace DualPistolSpread;
    if(!Player||!Hands.IsValidIndex(Index))return BaseHipSpread*BaseScale;
    const auto& H=Hands[Index];
    return (BaseHipSpread+H.Bloom+Player->MoveSpread+Player->AirSpread)*BaseScale*float(H.Stats.Spread);
}

float UPistolDualWieldComponent::SharedConeSpread() const
{
    if(bOffhandOnly)return HandConeSpread(1);
    if(Hands.Num()<2)return HandConeSpread(0);
    return .5f*(HandConeSpread(0)+HandConeSpread(1));
}

void UPistolDualWieldComponent::TryFire(int32 Index)
{
    auto& H=Hands[Index];const double Now=GetWorld()->GetTimeSeconds();
    if((!H.Pending && H.Item.Definition!=G18WeaponAssets::Definition) || !H.Held || !InputAvailable() || (IsEquipping() && H.Item.Definition!=G18WeaponAssets::Definition && H.Item.Definition!=PitViper2011WeaponAssets::Definition) || Player->IsAmmoWheelOpen() || H.Reloading || Player->IsSprinting()
        || Now<Player->SprintFireUnlockTime || Now<H.NextShot || (Index==1 && Player->IsCastBlockingLeftHandAction()))return;
    H.Pending=false;
    if(WeaponReloadStages::NeedsCycle(H.Item)){BeginReload(Index);return;}
    if(H.Rounds<=0)
    {
        if(Reserve(Index)>0 || InfiniteReserve(Index))BeginReload(Index);
        else { if(auto* Sound=H.Sounds.FindRef(TEXT("DryClick")).Get())UGameplayStatics::PlaySound2D(this,Sound,.65f); H.Held=false; }
        return;
    }
    const FVector Eye=Player->FirstPersonCamera->GetComponentLocation();
    // Both hands shoot the averaged akimbo cone, the same value the reticle shows.
    const float Spread=SharedConeSpread();
    const FVector Direction=FMath::VRandCone(SightDirection(),Spread);
    const FVector Muzzle=H.FX->ShotOrigin()+H.FX->ShotForward()*2.f;
    const float Range=FMath::Max(10000.f,float(H.Stats.Range)*300.f);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DualPistolShot),true,Player);Query.bReturnPhysicalMaterial=true;Query.bReturnFaceIndex=true;
    FHitResult Sight,Blocked;
    const bool AimHit=GetWorld()->LineTraceSingleByChannel(Sight,Eye,Eye+Direction*Range,ECC_Visibility,Query);
    const FVector Target=AimHit?Sight.ImpactPoint:Eye+Direction*Range;
    const bool MuzzleBlocked=GetWorld()->LineTraceSingleByChannel(Blocked,Eye,Muzzle,ECC_Visibility,Query);
    --H.Rounds;H.Item.Magazine=H.Rounds;
    const double ShotInterval=FMath::Max(.001,H.Stats.Interval);
    H.NextShot=H.Item.Definition==G18WeaponAssets::Definition
        ? (Now-H.NextShot>.15?Now:H.NextShot)+ShotInterval : Now+ShotInterval;
    H.Pattern=Now-H.LastShot>.4?0:FMath::Min(H.Pattern+1,FWeaponHandling::PatternCount-1);H.LastShot=Now;
    const float FireRate=H.Item.Definition==RSH12WeaponAssets::Definition && H.Clips.FindRef(TEXT("fire"))
        ?H.Clips.FindRef(TEXT("fire"))->GetPlayLength()/float(ShotInterval):1.f;
    StartAction(Index,!H.Revolver && H.Rounds==0?TEXT("fire_last"):TEXT("fire"),FireRate);
    if(H.Item.Definition==RSH12WeaponAssets::Definition && H.Action)
        H.NextShot=Now+FMath::Max(ShotInterval,double(H.Action->GetPlayLength()/FireRate));
    if(!bOffhandOnly){Player->MagazineAmmo=Hands[0].Rounds;Player->RevolverCaseCount=Hands[0].Cases;}
    // A blocked-muzzle hit may award XP and commit the profile synchronously.
    // Publish the consumed round before entering that callback, from the hand
    // counters, without saving or resetting either hand's action clock.
    Profile->SyncRuntime();
    ++Player->ShotsFired;Player->LastShotWorldTime=Now;
    if(MuzzleBlocked)
    {
        if(Blocked.GetActor())
        {
            const float Damage=float(H.Stats.Damage)*WeaponDamageFalloff::Multiplier(FVector::Distance(Muzzle,Blocked.ImpactPoint),float(H.Stats.Range)*100.f);
            FWeaponDamageResult DamageResult;
            auto Shot=ColdSteelSkills::Snapshot(Player,&H.Item,true);
            Shot.BulletSource=H.Ballistics;
            Shot.BulletFX=H.FX;
            const float Applied=ColdSteelSkills::ApplyHit(Player,Blocked,Damage,Direction,Shot,&DamageResult);
            Player->NotifyConfirmedWeaponHit(Blocked.GetActor(),Applied,&DamageResult,true);
            ColdSteelCombat::OnHit(Blocked,Player,ColdSteelCombat::Snapshot(Player,&H.Item).Poison);
        }
        H.FX->OnImpact(Blocked);
    }
    else H.Ballistics->Launch(Muzzle,(Target-Muzzle).GetSafeNormal(),float(H.Stats.Speed)*100.f,Range,float(H.Stats.Damage),H.FX,Player->CriticalHitSound,float(H.Stats.Range)*100.f,&H.Item);
    H.FX->OnShot(false);
    USoundBase* Sound=H.Suppressed?H.Sounds.FindRef(TEXT("Suppressed")):nullptr;
    if(!Sound)Sound=H.Sounds.FindRef(TEXT("Fire"));
    if(H.Item.Definition==G18WeaponAssets::Definition)
    {
        if(!H.Suppressed)
        {
            int32 Choice=FMath::RandRange(1,4);
            auto* Variant=H.Sounds.FindRef(FString::Printf(TEXT("Fire_%02d"),Choice)).Get();
            if(Variant && Variant==H.Sounds.FindRef(TEXT("PreviousFireVariant")).Get())
            {
                Choice=(Choice-1+FMath::RandRange(1,3))%4+1;
                Variant=H.Sounds.FindRef(FString::Printf(TEXT("Fire_%02d"),Choice)).Get();
            }
            if(Variant)Sound=Variant;
            H.Sounds.Add(TEXT("PreviousFireVariant"),Sound);
        }
        if(Sound)Player->PlayFireVoice(Sound,H.Suppressed?.7f:1.5f);
    }
    else if(Sound)UGameplayStatics::PlaySound2D(this,Sound,H.Item.Definition==RSH12WeaponAssets::Definition?.9f:H.Suppressed?.7f:1.5f,1.f);
    UAISense_Hearing::ReportNoiseEvent(this,Player->GetActorLocation(),1.f,Player,H.Suppressed?500.f:1800.f,TEXT("Gunshot"));
    const auto FeedbackHandling=ColdSteelCombat::ComposureHandling(Player,H.Stats.Handling);
    const auto Pattern=FWeaponHandling::Pattern(H.Pattern);
    if(auto* Controller=Player->GetController())
    {
        auto Aim=Controller->GetControlRotation();
        const float Scale=FWeaponHandling::ReferenceBallisticScale*FeedbackHandling.RecoilScale;
        Aim.Pitch=FMath::Clamp(FRotator::NormalizeAxis(Aim.Pitch)+FMath::RadiansToDegrees(Pattern.X)*Scale,-85.f,85.f);
        Aim.Yaw+=FMath::RadiansToDegrees(Pattern.Y)*Scale*(Index?-1.f:1.f);Controller->SetControlRotation(Aim);
    }
    // Presentation layers the single-weapon path receives from
    // ApplyShotFeedback(): this hand's viewmodel kick plus the shared camera
    // kick, jitter, trauma and FOV punch. The recoil load uses this hand's own
    // bloom, the same input its spread used for this shot.
    const float DualRecoilLoad=1.f+FMath::Clamp((H.Bloom+Player->MoveSpread+Player->AirSpread)/DualPistolSpread::RecoilLoadScale,0.f,2.f)*.7f;
    Player->ApplyDualWieldShotFeedback(Index,H.Revolver,FeedbackHandling,H.Pattern,float(H.Stats.Interval),DualRecoilLoad);
    H.Bloom=FMath::Min(DualPistolSpread::BloomMax,H.Bloom+DualPistolSpread::BloomPerShot);
    if(H.Rounds==0 && (InfiniteReserve(Index)||Reserve(Index)>0))H.ReloadQueued=true;
}

void UPistolDualWieldComponent::Reload()
{
    if(!bActive || !InputAvailable())return;
    for(int32 Index=FirstHand();Index<2;++Index)BeginReload(Index);
}
bool UPistolDualWieldComponent::SwitchAmmo(const FString& WeaponId,const FString& AmmoType)
{
    if(!bActive||!InputAvailable()||!Profile->CanSwitchAmmo(WeaponId,AmmoType))return false;
    for(int32 Index=FirstHand();Index<Hands.Num();++Index)if(Hands[Index].Item.InstanceId==WeaponId)
    {
        auto& H=Hands[Index];if(H.Reloading || (H.Item.Definition==RSH12WeaponAssets::Definition && H.Action && H.Action==H.Clips.FindRef(TEXT("fire"))) || (Index==1&&Player->IsCastBlockingLeftHandAction()))return false;
        CancelInputs();StopAction(Index);H.PendingAmmoType=AmmoType;BeginReload(Index);
        if(!H.Reloading)H.PendingAmmoType.Reset();return H.Reloading;
    }
    return false;
}
void UPistolDualWieldComponent::BeginReload(int32 Index)
{
    auto& H=Hands[Index];
    const bool Switching=!H.PendingAmmoType.IsEmpty();
    const bool ResumeCycle=!Switching && WeaponReloadStages::NeedsCycle(H.Item);
    if(H.Reloading)return;
    if(!ResumeCycle && !Switching && (H.Rounds>=H.Stats.Capacity || (!InfiniteReserve(Index) && Reserve(Index)<=0)))
    {H.ReloadQueued=false;return;}
    if(Index==1 && Player->IsCastBlockingLeftHandAction()){H.ReloadQueued=true;return;}
    if(H.Action){H.ReloadQueued=true;return;}
    H.ReloadQueued=false;H.ReloadStart=Switching||ResumeCycle?0:H.Rounds;
    H.ReloadSpeedloader=H.Speedloader;
    const int32 Available=Switching?int32(FMath::Min<int64>(H.Stats.Capacity,Profile->PouchCount(H.PendingAmmoType))):InfiniteReserve(Index)?H.Stats.Capacity:Reserve(Index);
    H.ReloadCount=FMath::Min(H.Stats.Capacity-H.ReloadStart,Available);
    if(ResumeCycle)H.ReloadCount=1;
    H.Seated=0;H.CasesCleared=Switching||ResumeCycle||!H.Revolver || (H.Rounds>0 && !H.Speedloader);
    H.ReloadCasesReleased=ResumeCycle || !H.Revolver;
    if(H.Item.Definition==RSH12WeaponAssets::Definition && !Switching && !ResumeCycle)
        H.CasesCleared=false;
    const bool Empty=Switching||ResumeCycle||H.Rounds==0;
    FString Clip;
    if(!H.Revolver){Clip=Empty?TEXT("reload_empty"):TEXT("reload");H.SourceLength=Empty?2.25f:1.75f;}
    else if(H.Speedloader){Clip=TEXT("speed_0");H.SourceLength=3.85f;H.ReloadCount=FMath::Min(H.Stats.Capacity,Available);}
    else{Clip=FString::Printf(TEXT("single_%d_%d"),H.ReloadStart,H.ReloadCount);H.SourceLength=DanWesson715WeaponAssets::SingleDuration(H.ReloadCount,Empty);}
    const auto* W=Player->GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Weapon(H.Item.Definition);
    const bool UseEmpty=Empty || (H.Revolver && H.Speedloader);
    const float Base=H.ReloadSpeedloader && H.Item.Definition==RSH12WeaponAssets::Definition?DanWesson715WeaponAssets::EmptyReload:
        W?float(UseEmpty?W->Base.EmptyReload:W->Base.Reload):H.SourceLength;
    const float Modified=float(UseEmpty?H.Stats.EmptyReload:H.Stats.Reload);
    // +33% akimbo reload: the same source clip played slower, so mechanical cues
    // and the ammo commit still land on the animation's own beats.
    const float Duration=FMath::Max(.05f,Modified)*DualPistolReload::TimeScale;
    StartAction(Index,Clip,Base/Duration);
    H.Reloading=H.Action!=nullptr;
    H.Pending=false;
    if(ResumeCycle && H.Action)
    {
        H.Seated=FMath::Max(1,H.ReloadCount);
        const auto Stages=WeaponReloadStages::ForWeapon(H.Item.Definition,UseEmpty,false,H.Revolver&&!H.ReloadSpeedloader,H.ReloadCount);
        H.ActionTime=Stages.CycleBegin/H.SourceLength*H.Action->GetPlayLength();
        H.ActionStarted-=H.ActionTime/FMath::Max(.001f,H.ActionRate);
    }
}

bool UPistolDualWieldComponent::CommitReloadInsertion(int32 Index,int32 Count,bool Completed)
{
    auto& H=Hands[Index];
    const bool NeedsCycle=H.Revolver || H.ReloadStart==0;
    const bool Inserted=!H.PendingAmmoType.IsEmpty()
        ? Profile->CommitAmmoSwitch(H.Item.InstanceId,H.PendingAmmoType,H.Stats.Capacity,NeedsCycle,Count,Completed)
        : Profile->ReloadDualPistol(H.Item.InstanceId,Count,H.Stats.Capacity,Completed,NeedsCycle)>0;
    if(Inserted){H.PendingAmmoType.Reset();H.CasesCleared=true;}
    return Inserted;
}

bool UPistolDualWieldComponent::CompleteReloadMechanism(int32 Index,float Source)
{
    auto& H=Hands[Index];
    const auto Stages=WeaponReloadStages::ForWeapon(H.Item.Definition,H.ReloadStart==0 || H.ReloadSpeedloader,
        false,H.Revolver&&!H.ReloadSpeedloader,H.ReloadCount);
    if(H.Seated>0 && Source+1.e-6f>=Stages.Ready && WeaponReloadStages::NeedsCycle(H.Item))
        if(!Profile->CompleteWeaponReloadCycle(H.Item.InstanceId)){StopAction(Index);return false;}
    return true;
}

void UPistolDualWieldComponent::Cue(int32 Index,const FString& Name,float At,float Previous,float Now)
{
    auto& H=Hands[Index];
    if(Now<At || Previous>At || H.PlayedCues.Contains(Name))return;
    H.PlayedCues.Add(Name);
    FString SoundKey=Name;int32 Separator=INDEX_NONE;if(SoundKey.FindChar(TCHAR(':'),Separator))SoundKey.LeftInline(Separator);
    if(auto* Sound=H.Sounds.FindRef(SoundKey).Get())
    {
        if(auto* Voice=UGameplayStatics::SpawnSound2D(this,Sound,.8f,1.f,0.f,nullptr,false,true))H.Voices.Add(Voice);
    }
}

void UPistolDualWieldComponent::AdvanceReload(int32 Index,float Previous)
{
    auto& H=Hands[Index];
    const float Source=H.ActionTime/FMath::Max(.001f,H.Action->GetPlayLength())*H.SourceLength;
    if(!H.Revolver)
    {
        Cue(Index,TEXT("MagOut"),.3167f,Previous,Source);
        Cue(Index,TEXT("MagInsert"),1.05f,Previous,Source);
        Cue(Index,TEXT("MagSeat"),1.0667f,Previous,Source);
        if(H.ReloadStart==0)Cue(Index,TEXT("BoltRelease"),1.6f,Previous,Source);
        if(!H.Seated && Source>=1.05f)
        {
            if(!CommitReloadInsertion(Index,H.ReloadCount,true)){StopAction(Index);return;}
            H.Seated=1;
        }
        CompleteReloadMechanism(Index,Source);
        return;
    }
    using namespace DanWesson715WeaponAssets;
    const bool RSH=H.Item.Definition==RSH12WeaponAssets::Definition;
    const float EjectAt=H.ReloadSpeedloader?Eject/NormalReload*3.85f:
        RSH?(H.ReloadStart==0?Eject:Open+.06f):EmptyCaseClear;
    if(RSH && !H.ReloadCasesReleased && Source>=EjectAt)
    {
        if(!ReleaseReloadCases(Index,EjectAt)){StopAction(Index);return;}
    }
    else if(!H.CasesCleared && Source>=EjectAt)
    {
        if(!Profile->EjectDualPistolCases(H.Item.InstanceId,H.ReloadSpeedloader)){StopAction(Index);return;}
        H.CasesCleared=true;
    }
    if(H.ReloadSpeedloader)
    {
        for(const auto& C:SpeedloaderSoundCues)
            Cue(Index,C.Name,FMath::Max(0.f,C.Contact/NormalReload*3.85f-C.LeadSeconds*H.ActionRate),Previous,Source);
        if(!H.Seated && Source>=Seat/NormalReload*3.85f)
        {
            if(!CommitReloadInsertion(Index,H.ReloadCount,true)){StopAction(Index);return;}
            H.Seated=1;
        }
    }
    else
    {
        Cue(Index,TEXT("SingleOpen"),Open,Previous,Source);
        if(H.ReloadStart==0)Cue(Index,TEXT("SingleEject"),Eject,Previous,Source);
        const float Begin=SingleLoopBegin(H.ReloadStart==0);
        for(int32 Round=0;Round<H.ReloadCount;++Round)
        {
            const float Contact=SingleSeatTime(Round,H.ReloadStart==0);
            Cue(Index,FString::Printf(TEXT("MagSeat:%d"),Round),Contact,Previous,Source);
            if(H.Seated==Round && Source>=Contact)
            {
                const bool Inserted=CommitReloadInsertion(Index,1,H.Seated+1==H.ReloadCount);
                if(!Inserted)
                {
                    // Previously seated rounds remain saved, including when the
                    // other hand exhausted the shared pouch. Resume with closure.
                    StopAction(Index);return;
                }
                ++H.Seated;
            }
        }
        Cue(Index,TEXT("SingleClose"),Begin+SingleStep*H.ReloadCount+.37f,Previous,Source);
    }
    CompleteReloadMechanism(Index,Source);
}

bool UPistolDualWieldComponent::ReleaseReloadCases(int32 Index,float ReleaseSource)
{
    auto& H=Hands[Index];
    const bool DiscardLive=H.ReloadSpeedloader || !H.PendingAmmoType.IsEmpty();
    const int32 First=DiscardLive?0:H.Rounds;
    const int32 Count=FMath::Clamp(H.Cases,0,RSH12WeaponAssets::Capacity);
    const int32 Live=H.Rounds;
    const float Now=H.ActionTime;
    const float ReleaseTime=ReleaseSource/H.SourceLength*H.Action->GetPlayLength();
    const float Age=FMath::Max(0.f,(Now-ReleaseTime)/FMath::Max(.001f,H.ActionRate));
    // Resolve the actual release pose before the inventory transaction masks
    // its case bones. Sampling the previous rendered frame causes a visible gap.
    H.ActionTime=ReleaseTime;
    Pose(Index,0.f);
    H.Mesh->TickAnimation(0.f,false);
    H.Mesh->RefreshBoneTransforms();
    TArray<FTransform,TInlineAllocator<5>> Frames;
    for(int32 Chamber=First;Chamber<Count;++Chamber)
    {
        FTransform Frame=H.Mesh->GetSocketTransform(*FString::Printf(TEXT("WPN_Case_%d"),Chamber),RTS_World);
        // The shared native rig carries a 100x root; exported static geometry
        // is already centimetres. Preserve the posed frame without scaling twice.
        Frame.SetScale3D(Frame.GetScale3D()*.01f);
        Frames.Add(Frame);
    }
    const FVector Bore=H.Mesh->GetSocketQuaternion(TEXT("WPN_Cylinder")).RotateVector(
        FVector(-.0871535167f,-.0000020575f,.9961948395f));
    H.ActionTime=Now;
    if(!H.CasesCleared && !Profile->EjectDualPistolCases(H.Item.InstanceId,H.ReloadSpeedloader))
    {Pose(Index,0.f);return false;}
    H.CasesCleared=true;H.ReloadCasesReleased=true;
    for(int32 Chamber=First;Chamber<Count;++Chamber)
    {
        const auto& Meshes=Chamber<Live?H.ReloadLiveMeshes:H.ReloadCaseMeshes;
        if(Meshes.IsValidIndex(Chamber) && Meshes[Chamber] && H.FX)
            H.FX->OnReloadCartridge(Meshes[Chamber],Frames[Chamber-First],
                Player->GetVelocity()-Bore*32.f+FVector(0,0,-18.f),Age);
    }
    Pose(Index,0.f);
    H.Mesh->TickAnimation(0.f,false);
    H.Mesh->RefreshBoneTransforms();
    return true;
}
