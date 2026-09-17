#include "PistolDualWieldComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "ColdSteelEnchantmentCombat.h"
#include "FPSWeaponFXComponent.h"
#include "FPSBallisticsComponent.h"
#include "DanWesson715WeaponAssets.h"
#include "WeaponDamageFalloff.h"
#include "Camera/CameraComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/AudioComponent.h"
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
    if(Hands.Num()<2)return HandConeSpread(0);
    return .5f*(HandConeSpread(0)+HandConeSpread(1));
}

void UPistolDualWieldComponent::TryFire(int32 Index)
{
    auto& H=Hands[Index];const double Now=GetWorld()->GetTimeSeconds();
    if(!H.Pending || !H.Held || !InputAvailable() || H.Reloading || Player->IsSprinting()
        || Now<Player->SprintFireUnlockTime || Now<H.NextShot || (Index==1 && Player->IsCastBlockingLeftHandAction()))return;
    H.Pending=false;
    if(H.Rounds<=0)
    {
        if(Reserve(Index)>0 || Player->HasInfiniteReserveAmmo())BeginReload(Index);
        else if(auto* Sound=H.Sounds.FindRef(TEXT("DryClick")).Get())UGameplayStatics::PlaySound2D(this,Sound,.65f);
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
    H.NextShot=Now+FMath::Max(.001,H.Stats.Interval);
    H.Pattern=Now-H.LastShot>.4?0:FMath::Min(H.Pattern+1,FWeaponHandling::PatternCount-1);H.LastShot=Now;
    StartAction(Index,!H.Revolver && H.Rounds==0?TEXT("fire_last"):TEXT("fire"));
    ++Player->ShotsFired;Player->LastShotWorldTime=Now;
    if(MuzzleBlocked)
    {
        if(Blocked.GetActor())
        {
            const float Damage=float(H.Stats.Damage)*WeaponDamageFalloff::Multiplier(FVector::Distance(Muzzle,Blocked.ImpactPoint),float(H.Stats.Range)*100.f);
            Player->NotifyConfirmedWeaponHit(Blocked.GetActor(),ColdSteelSkills::ApplyHit(Player,Blocked,Damage,Direction,ColdSteelSkills::Snapshot(Player,&H.Item)));
            ColdSteelCombat::OnHit(Blocked.GetActor(),Player,ColdSteelCombat::Snapshot(Player,&H.Item).Poison);
        }
        H.FX->OnImpact(Blocked);
    }
    else H.Ballistics->Launch(Muzzle,(Target-Muzzle).GetSafeNormal(),float(H.Stats.Speed)*100.f,Range,float(H.Stats.Damage),H.FX,Player->CriticalHitSound,float(H.Stats.Range)*100.f,&H.Item);
    H.FX->OnShot(false);
    USoundBase* Sound=H.Suppressed?H.Sounds.FindRef(TEXT("Suppressed")):nullptr;
    if(!Sound)Sound=H.Sounds.FindRef(TEXT("Fire"));
    if(Sound)UGameplayStatics::PlaySound2D(this,Sound,H.Suppressed?.7f:1.5f,1.f);
    UAISense_Hearing::ReportNoiseEvent(this,Player->GetActorLocation(),1.f,Player,H.Suppressed?500.f:1800.f,TEXT("Gunshot"));
    const auto Pattern=FWeaponHandling::Pattern(H.Pattern);
    if(auto* Controller=Player->GetController())
    {
        auto Aim=Controller->GetControlRotation();
        const float Scale=FWeaponHandling::ReferenceBallisticScale*H.Stats.Handling.RecoilScale;
        Aim.Pitch=FMath::Clamp(FRotator::NormalizeAxis(Aim.Pitch)+FMath::RadiansToDegrees(Pattern.X)*Scale,-85.f,85.f);
        Aim.Yaw+=FMath::RadiansToDegrees(Pattern.Y)*Scale*(Index?-1.f:1.f);Controller->SetControlRotation(Aim);
    }
    // Presentation layers the single-weapon path receives from
    // ApplyShotFeedback(): this hand's viewmodel kick plus the shared camera
    // kick, jitter, trauma and FOV punch. The recoil load uses this hand's own
    // bloom, the same input its spread used for this shot.
    const float DualRecoilLoad=1.f+FMath::Clamp((H.Bloom+Player->MoveSpread+Player->AirSpread)/DualPistolSpread::RecoilLoadScale,0.f,2.f)*.7f;
    Player->ApplyDualWieldShotFeedback(Index,H.Revolver,H.Stats.Handling,H.Pattern,float(H.Stats.Interval),DualRecoilLoad);
    H.Bloom=FMath::Min(DualPistolSpread::BloomMax,H.Bloom+DualPistolSpread::BloomPerShot);
    if(H.Rounds==0 && Player->HasInfiniteReserveAmmo())H.ReloadQueued=true;
}

void UPistolDualWieldComponent::Reload()
{
    if(!bActive || !InputAvailable())return;
    for(int32 Index=0;Index<2;++Index)BeginReload(Index);
}
void UPistolDualWieldComponent::BeginReload(int32 Index)
{
    auto& H=Hands[Index];
    if(H.Reloading || H.Rounds>=H.Stats.Capacity || (!Player->HasInfiniteReserveAmmo() && Reserve(Index)<=0))return;
    if(Index==1 && Player->IsCastBlockingLeftHandAction()){H.ReloadQueued=true;return;}
    if(H.Action && H.Action!=H.Clips.FindRef(TEXT("equip"))){H.ReloadQueued=true;return;}
    H.ReloadQueued=false;H.ReloadStart=H.Rounds;
    H.ReloadSpeedloader=H.Speedloader;
    H.ReloadCount=FMath::Min(H.Stats.Capacity-H.Rounds,Player->HasInfiniteReserveAmmo()?H.Stats.Capacity:Reserve(Index));
    H.Seated=0;H.CasesCleared=!H.Revolver || (H.Rounds>0 && !H.Speedloader);
    const bool Empty=H.Rounds==0;
    FString Clip;
    if(!H.Revolver){Clip=Empty?TEXT("reload_empty"):TEXT("reload");H.SourceLength=Empty?2.25f:1.75f;}
    else if(H.Speedloader){Clip=TEXT("speed_0");H.SourceLength=3.85f;H.ReloadCount=FMath::Min(6,Player->HasInfiniteReserveAmmo()?6:Reserve(Index));}
    else{Clip=FString::Printf(TEXT("single_%d_%d"),H.ReloadStart,H.ReloadCount);H.SourceLength=DanWesson715WeaponAssets::SingleDuration(H.ReloadCount,Empty);}
    const auto* W=Player->GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Weapon(H.Item.Definition);
    const bool UseEmpty=Empty || (H.Revolver && H.Speedloader);
    const float Base=W?float(UseEmpty?W->Base.EmptyReload:W->Base.Reload):H.SourceLength;
    const float Modified=float(UseEmpty?H.Stats.EmptyReload:H.Stats.Reload);
    // +33% akimbo reload: the same source clip played slower, so mechanical cues
    // and the ammo commit still land on the animation's own beats.
    const float Duration=FMath::Max(.05f,Modified)*DualPistolReload::TimeScale;
    StartAction(Index,Clip,Base/Duration);
    H.Reloading=H.Action!=nullptr;
    H.Pending=false;
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
        if(!H.Seated && Source>=1.0667f)
        {
            H.Seated=1;
            Profile->ReloadDualPistol(H.Item.InstanceId,H.ReloadCount,H.Stats.Capacity,true);
        }
        return;
    }
    using namespace DanWesson715WeaponAssets;
    const float EjectAt=H.ReloadSpeedloader?Eject/NormalReload*3.85f:EmptyCaseClear;
    if(!H.CasesCleared && Source>=EjectAt)
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
            H.Seated=1;Profile->ReloadDualPistol(H.Item.InstanceId,H.ReloadCount,6,true);
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
                ++H.Seated;
                const int32 Taken=Profile->ReloadDualPistol(H.Item.InstanceId,1,6,H.Seated==H.ReloadCount);
                if(Taken==0 && !Player->HasInfiniteReserveAmmo())
                {
                    // Keep the closing tail when the other gun exhausted shared reserves.
                    H.ActionTime=FMath::Max(H.ActionTime,H.Action->GetPlayLength()-SingleCloseTail);
                    H.ActionStarted=GetWorld()->GetTimeSeconds()-H.ActionTime/H.ActionRate;H.Seated=H.ReloadCount;break;
                }
            }
        }
        Cue(Index,TEXT("SingleClose"),Begin+SingleStep*H.ReloadCount+.37f,Previous,Source);
    }
}
