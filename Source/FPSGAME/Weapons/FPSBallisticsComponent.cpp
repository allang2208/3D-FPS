#include "FPSBallisticsComponent.h"
#include "WeaponDamageFalloff.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../FPSGAMECharacter.h"
#include "FPSWeaponFXComponent.h"
#include "ColdSteelEnchantmentCombat.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

UFPSBallisticsComponent::UFPSBallisticsComponent()
{PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;}
void UFPSBallisticsComponent::Launch(FVector Start,FVector Direction,float SpeedCM,float RangeCM,float Damage,UFPSWeaponFXComponent* FX,USoundBase* Headshot,float EffectiveRangeCM,const FColdSteelItem* ShotItem)
{
    if(!GetWorld()||!FMath::IsFinite(SpeedCM)||SpeedCM<=0||RangeCM<=0||Direction.IsNearlyZero())return;
    LastLaunchStart=Start;
    WeaponFX=FX;HeadshotSound=Headshot;
    const auto Effects=ColdSteelCombat::Snapshot(GetOwner(),ShotItem);
    FFPSFlyingRound Round;Round.Training=ColdSteelSkills::Snapshot(GetOwner(),ShotItem);Round.Position=Start;Round.Direction=Direction.GetSafeNormal();Round.Speed=SpeedCM;Round.Remaining=RangeCM;Round.Damage=Damage;Round.Timestamp=GetWorld()->GetTimeSeconds();Round.Piercing=Effects.Piercing;Round.Poison=Effects.Poison;Rounds.Add(MoveTemp(Round));
    Rounds.Last().EffectiveRangeCM=EffectiveRangeCM;
    SetComponentTickEnabled(true);
}
void UFPSBallisticsComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Fn)
{
    Super::TickComponent(Delta,Type,Fn);
    const double Now=GetWorld()->GetTimeSeconds();
    const auto* Pawn=Cast<APawn>(GetOwner());
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
            if(WeaponFX)WeaponFX->OnImpact(Hit);
            if(HeadshotSound&&ColdSteelSkills::IsCriticalHit(Hit))UGameplayStatics::PlaySound2D(this,HeadshotSound,.630957f);
            // Penetrate targets, never walls. Each target takes damage once per round.
            if(R.Piercing>0&&Cast<APawn>(Hit.GetActor())){--R.Piercing;R.HitActors.Add(Hit.GetActor());Params.AddIgnoredActor(Hit.GetActor());R.Position=Hit.ImpactPoint;continue;}
            Stopped=true;break;
        }
        if(WeaponFX)WeaponFX->OnTracerSegment(Start,Stopped?Hit.ImpactPoint:End);
        if(Stopped){Rounds.RemoveAtSwap(I);continue;}
        R.Position=End;R.Remaining-=Distance;R.TraveledCM+=Distance;
        if(R.Remaining<=KINDA_SMALL_NUMBER)Rounds.RemoveAtSwap(I);
    }
    if(Rounds.IsEmpty())SetComponentTickEnabled(false);
}
