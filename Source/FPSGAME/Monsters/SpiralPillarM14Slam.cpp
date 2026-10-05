#include "SpiralPillarM14.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/FPSIceWall.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

void ASpiralPillarM14::SlamContact()
{
    if(!HasAuthority()||bConsumed||State!=EM14State::TrunkSlam)return;
    bConsumed=true;
    // The contact volume follows the sampled upper trunk, including its tip.
    const FVector From=GetMesh()->GetSocketLocation(TEXT("spine_02"));
    const FVector Upper=GetMesh()->GetSocketLocation(TEXT("spine_05"));
    const FVector Previous=GetMesh()->GetSocketLocation(TEXT("spine_04"));
    const FVector To=Upper+(Upper-Previous).GetSafeNormal()*45.f;
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_Pawn);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M14TrunkSlam),false,this);
    TArray<FHitResult> Hits;
    GetWorld()->SweepMultiByObjectType(Hits,From,To,FQuat::Identity,Objects,
        FCollisionShape::MakeSphere(SlamBodyRadius),Query);
    TSet<TWeakObjectPtr<AActor>> Consumed;
    for(const FHitResult& Hit:Hits)
    {
        if(Dead()||State!=EM14State::TrunkSlam)break;
        AActor* Victim=Hit.GetActor();APawn* Pawn=Cast<APawn>(Victim);
        const bool PlayerBody=Pawn&&Pawn->IsPlayerControlled()&&Hit.GetComponent()==Pawn->GetRootComponent();
        if(!IsValid(Victim)||(!PlayerBody&&!Victim->IsA<AFPSIceWall>())||Consumed.Contains(Victim))continue;
        // Walls must block the downward strike; no radial damage through scenery.
        FHitResult Block;
        const FVector Sight=GetNavAgentLocation()+FVector::UpVector*100.f;
        if(GetWorld()->LineTraceSingleByChannel(Block,Sight,Victim->GetActorLocation(),ECC_Visibility,Query)&&Block.GetActor()!=Victim)continue;
        Consumed.Add(Victim);
        UGameplayStatics::ApplyPointDamage(Victim,PhysicalAttack*SlamDamageMultiplier,
            (GetActorForwardVector()-FVector::UpVector).GetSafeNormal(),Hit,GetController(),this,UEnemyMeleeDamage::StaticClass());
    }
}
