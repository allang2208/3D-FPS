#include "FPSBallisticsComponent.h"
#include "FPSWeaponFXComponent.h"
#include "FPSShatterFXSubsystem.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"

bool UFPSBallisticsComponent::IsShatterEnemy(AActor* Target,AActor* Shooter)
{
    if(!IsValid(Target)||Target==Shooter||Target->IsActorBeingDestroyed()||!Target->CanBeDamaged()
        ||Target->IsA<AFPSGAMECharacter>()||Target->ActorHasTag(TEXT("Player"))
        ||Target->ActorHasTag(TEXT("Friendly"))||Target->ActorHasTag(TEXT("Companion")))return false;
    const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
    return Combat&&!Combat->IsDead();
}

void UFPSBallisticsComponent::QueueShatter(const FHitResult& Hit,const FColdSteelSkillShot& Shot,const FWeaponDamageResult& Receipt)
{
    UWorld* World=GetWorld();AActor* Shooter=GetOwner();
    if(!World||!Shooter||!Shooter->HasAuthority()||Shot.bRicochet||Shot.ShatterRadiusCM<=0.f
        ||Shot.ShatterDamageScale<=0.f||Receipt.BeforeDefense.Total()<=0.)return;

    const FVector Origin=Hit.ImpactPoint;
    const float Radius=Shot.ShatterRadiusCM;
    AActor* Original=Hit.GetActor();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ShatterBulletTargets),false,Shooter);
    if(Original)Query.AddIgnoredActor(Original);
    TArray<FOverlapResult> Overlaps;
    World->OverlapMultiByObjectType(Overlaps,Origin,FQuat::Identity,
        FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeSphere(Radius),Query);

    TArray<AActor*> Candidates;
    TSet<AActor*> Seen;
    // Bodies do not occlude the all-enemy fan-out. World geometry still does.
    FCollisionQueryParams Sight(SCENE_QUERY_STAT(ShatterBulletSight),true,Shooter);
    if(Original)Sight.AddIgnoredActor(Original);
    for(const auto& Overlap:Overlaps)
    {
        AActor* Target=Overlap.GetActor();
        if(Target&&Cast<APawn>(Target))Sight.AddIgnoredActor(Target);
        if(Target==Original||Seen.Contains(Target)||!IsShatterEnemy(Target,Shooter))continue;
        Seen.Add(Target);
        if(FVector::DistSquared(Origin,Target->GetActorLocation())<=FMath::Square(Radius))Candidates.Add(Target);
    }
    Candidates.RemoveAll([&](AActor* Target)
    {
        FHitResult Cover;
        return World->LineTraceSingleByChannel(Cover,Origin,Target->GetActorLocation(),ECC_Visibility,Sight);
    });
    if(Candidates.IsEmpty())return;
    if(!Receipt.bKilled)
    {
        AActor* Selected=Candidates[FMath::RandHelper(Candidates.Num())];
        Candidates.Reset();Candidates.Add(Selected);
    }

    // Preserve the original critical/weakpoint result and typed damage BEFORE
    // its victim's armor/remaining HP. New targets resolve their own defense once.
    FColdSteelSkillShot ChildShot=Shot;
    ChildShot.DamagePanel=Receipt.BeforeDefense.Scaled(Shot.ShatterDamageScale);
    ChildShot.ShatterRadiusCM=0.f;
    ChildShot.bRicochet=true;
    ChildShot.bInheritedCritical=Receipt.bCritical;
    ChildShot.BulletSource=this;
    if(!ChildShot.BulletFX.IsValid())ChildShot.BulletFX=Shooter->FindComponentByClass<UFPSWeaponFXComponent>();
    const float Speed=Shot.BulletSpeedCM>0.f?Shot.BulletSpeedCM:50000.f;
    PendingShatterRounds.Reserve(PendingShatterRounds.Num()+Candidates.Num());
    const int32 FirstChild=PendingShatterRounds.Num();
    for(AActor* Target:Candidates)
    {
        const FVector Direction=(Target->GetActorLocation()-Origin).GetSafeNormal();
        if(Direction.IsNearlyZero())continue;
        FFPSFlyingRound Child;
        Child.Id=NextRoundId++;
        Child.Position=Origin;Child.Direction=Direction;
        Child.Speed=Speed;Child.Remaining=Radius;
        Child.Damage=ChildShot.DamagePanel.Total();
        // EffectiveRangeCM=0 means no second falloff over this short bounce.
        Child.Timestamp=World->GetTimeSeconds();Child.Training=ChildShot;
        Child.RicochetTarget=Target;
        Child.bShowTracer=true;
        if(Original)Child.HitActors.Add(Original);
        // Piercing and poison-affix procs default to zero; captured ammo effects
        // and ordinary weapon damage/training still follow the shared hit path.
        PendingShatterRounds.Add(MoveTemp(Child));
    }
    if(PendingShatterRounds.Num()>FirstChild)
        if(auto* FX=World->GetSubsystem<UFPSShatterFXSubsystem>())
            FX->Burst(Origin,Hit.ImpactNormal,Receipt.bKilled?EShatterBurst::Kill:EShatterBurst::Hit);
    SetComponentTickEnabled(true);
}
