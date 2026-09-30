#include "IceWallCombat.h"
#include "FPSIceWall.h"
#include "EnemyAttackDamage.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

AFPSIceWall* IceWallCombat::BlockingWall(const AActor* Attacker,const AActor* Target,float Reach,float MinimumFacing)
{
    if(!IsValid(Attacker)||!IsValid(Target)||!Attacker->GetWorld()||Reach<=0)return nullptr;
    // Trace at leg/torso height so low cover is also an attackable obstruction.
    const auto* Pawn=Cast<APawn>(Attacker);
    const float HalfHeight=Pawn?Pawn->GetSimpleCollisionHalfHeight():0.f;
    const FVector Start=Attacker->GetActorLocation()+FVector(0,0,40.f-HalfHeight);
    FVector End=Target->GetActorLocation();End.Z=Start.Z;
    FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(IceWallMeleeCover),false,Attacker);
    Query.AddIgnoredActor(Target);
    if(!Attacker->GetWorld()->LineTraceSingleByChannel(Hit,Start,End,ECC_Visibility,Query)||Hit.Distance>Reach)return nullptr;
    auto* Wall=Cast<AFPSIceWall>(Hit.GetActor());
    if(!Wall||!Wall->IsSolid())return nullptr;
    const FVector Direction=(Hit.ImpactPoint-Start).GetSafeNormal2D();
    if(!Direction.IsNearlyZero()&&FVector::DotProduct(Attacker->GetActorForwardVector(),Direction)<MinimumFacing)return nullptr;
    return Wall;
}

bool IceWallCombat::ApplyMelee(AActor* Attacker,const AActor* Target,float Reach,float Damage,float MinimumFacing)
{
    auto* Wall=BlockingWall(Attacker,Target,Reach,MinimumFacing);
    if(!Wall)return false;
    const auto* Pawn=Cast<APawn>(Attacker);
    UGameplayStatics::ApplyDamage(Wall,Damage,Pawn?Pawn->GetController():nullptr,Attacker,UEnemyMeleeDamage::StaticClass());
    return true; // This contact was intercepted, including the blow that destroys the wall.
}
