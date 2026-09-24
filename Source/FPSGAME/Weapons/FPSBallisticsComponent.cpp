#include "FPSBallisticsComponent.h"
#include "WeaponDamageFalloff.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../FPSGAMECharacter.h"
#include "FPSWeaponFXComponent.h"
#include "ColdSteelEnchantmentCombat.h"
#include "../WorldGeneration/RiverPilotFXSubsystem.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "HAL/IConsoleManager.h"

// Live tuning for the "projectile feel" pass (Docs/Weapons/ballistic-feel-options-20260921.md):
// 90 m/s rounds flew at arrow speed (0.78 s to 70 m, ten rounds in the air before the first
// one landed) which read as a thrown object. Presentation and muzzle velocity only — damage,
// falloff, penetration and the trace are untouched.
static TAutoConsoleVariable<float> CVarBulletSpeedScale(TEXT("fps.Ballistics.SpeedScale"),1.f,
    TEXT("Multiplier on muzzle velocity for every launched round (1 = catalog bullet_speed)."));
static TAutoConsoleVariable<int32> CVarTracerEvery(TEXT("fps.Tracer.Every"),1,
    TEXT("Draw a tracer streak on every Nth round (1 = every round); round 1 always draws."));

UFPSBallisticsComponent::UFPSBallisticsComponent()
{PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;}
void UFPSBallisticsComponent::Launch(FVector Start,FVector Direction,float SpeedCM,float RangeCM,float Damage,UFPSWeaponFXComponent* FX,USoundBase* Headshot,float EffectiveRangeCM,const FColdSteelItem* ShotItem)
{
    if(!GetWorld()||!FMath::IsFinite(SpeedCM)||SpeedCM<=0||RangeCM<=0||Direction.IsNearlyZero())return;
    LastLaunchStart=Start;
    WeaponFX=FX;HeadshotSound=Headshot;
    const float SpeedScale=FMath::Clamp(CVarBulletSpeedScale.GetValueOnGameThread(),.05f,10.f);
    const int32 TracerInterval=FMath::Max(1,CVarTracerEvery.GetValueOnGameThread());
    const auto Effects=ColdSteelCombat::Snapshot(GetOwner(),ShotItem);
    FFPSFlyingRound Round;Round.Id=NextRoundId++;Round.Training=ColdSteelSkills::Snapshot(GetOwner(),ShotItem,true);Round.Position=Start;Round.Direction=Direction.GetSafeNormal();Round.Speed=SpeedCM*SpeedScale;Round.Remaining=RangeCM;Round.Damage=Damage;Round.Timestamp=GetWorld()->GetTimeSeconds();Round.Piercing=Effects.Piercing;Round.Poison=Effects.Poison;Rounds.Add(MoveTemp(Round));
    Rounds.Last().EffectiveRangeCM=EffectiveRangeCM;
    // Counter starts at zero, so the first round of a magazine always carries a tracer and
    // then every Nth one does — a burst reads as spaced streaks instead of a solid tube.
    Rounds.Last().bShowTracer=(TracerRoundCounter++%TracerInterval)==0;
    SetComponentTickEnabled(true);
}
void UFPSBallisticsComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Fn)
{
    Super::TickComponent(Delta,Type,Fn);
    const double Now=GetWorld()->GetTimeSeconds();
    const auto* Pawn=Cast<APawn>(GetOwner());
    auto* RiverFX=GetWorld()->GetSubsystem<URiverPilotFXSubsystem>();
    for(int32 I=Rounds.Num()-1;I>=0;--I)
    {
        auto& R=Rounds[I];const float Distance=FMath::Min(R.Remaining,R.Speed*static_cast<float>(FMath::Max(0.,Now-R.Timestamp)));
        R.Timestamp=Now;if(Distance<=0)continue;
        const FVector Start=R.Position;
        const FVector End=R.Position+R.Direction*Distance;FHitResult Hit;
        FCollisionQueryParams Params(SCENE_QUERY_STAT(FlyingRound),true,GetOwner());Params.bReturnPhysicalMaterial=true;Params.bReturnFaceIndex=true;
        for(const auto& A:R.HitActors)if(A.IsValid())Params.AddIgnoredActor(A.Get());
        bool Stopped=false;
        while(GetWorld()->LineTraceSingleByChannel(Hit,R.Position,End,ECC_Visibility,Params))
        {
            ++ImpactCount;
            LastImpactPoint=Hit.ImpactPoint;
            if(Hit.GetActor())
            {
                const float HitDistance=R.TraveledCM+FVector::Distance(Start,Hit.ImpactPoint);
                const float HitDamage=R.Damage*WeaponDamageFalloff::Multiplier(HitDistance,R.EffectiveRangeCM);
                const float Applied = ColdSteelSkills::ApplyHit(GetOwner(),Hit,HitDamage,R.Direction,R.Training);
                if(auto* Shooter=Cast<AFPSGAMECharacter>(GetOwner())) Shooter->NotifyConfirmedWeaponHit(Hit.GetActor(),Applied);
            }
            ColdSteelCombat::OnHit(Hit.GetActor(),GetOwner(),R.Poison);
            if(WeaponFX&&(!RiverFX||!RiverFX->IsSubmergedRiverbed(Hit)))WeaponFX->OnImpact(Hit);
            if(HeadshotSound&&ColdSteelSkills::IsCriticalHit(Hit))UGameplayStatics::PlaySound2D(this,HeadshotSound,.630957f);
            // Penetrate targets, never walls. Each target takes damage once per round.
            if(R.Piercing>0&&Cast<APawn>(Hit.GetActor())){--R.Piercing;R.HitActors.Add(Hit.GetActor());Params.AddIgnoredActor(Hit.GetActor());R.Position=Hit.ImpactPoint;continue;}
            Stopped=true;break;
        }
        const FVector Reached=Stopped?Hit.ImpactPoint:End;
        if(!R.bRiverEntryPlayed&&RiverFX&&RiverFX->TryBulletCrossing(Start,Reached,R.Speed))R.bRiverEntryPlayed=true;
        if(WeaponFX&&R.bShowTracer)WeaponFX->OnTracerSegment(R.Id,Start,Reached);
        if(Stopped){Rounds.RemoveAtSwap(I);continue;}
        R.Position=End;R.Remaining-=Distance;R.TraveledCM+=Distance;
        if(R.Remaining<=KINDA_SMALL_NUMBER)Rounds.RemoveAtSwap(I);
    }
    if(Rounds.IsEmpty())SetComponentTickEnabled(false);
}
