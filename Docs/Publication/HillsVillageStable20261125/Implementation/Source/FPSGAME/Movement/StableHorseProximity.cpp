#include "HorseRiderComponent.h"
#include "StableRidingHorse.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

AStableRidingHorse* UHorseRiderComponent::NearbyForDisplay()
{
    auto* Pawn=Player.Get();
    if(!Pawn || !Pawn->IsLocallyControlled() || Active())return nullptr;
    const double Now=GetWorld()->GetTimeSeconds();
    if(Now<NextNearbyScan)
    {
        auto* Nearest=NearbyHorse.Get();
        return Nearest&&!Nearest->GetRider()&&!Nearest->IsRetreating()&&Nearest->Visit()==EStableHorseVisit::Present?Nearest:nullptr;
    }
    NextNearbyScan=Now+.15;
    NearbyHorse.Reset();
    auto* PC=Cast<APlayerController>(Pawn->GetController());
    if(!PC)return nullptr;
    FVector Eye;FRotator View;
    ColdSteelWorldInteraction::GetReachViewPoint(PC,Eye,View);
    const FVector At=Pawn->GetActorLocation();
    constexpr float Radius=220.f;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(StableHorseNear),false,Pawn);
    TArray<FOverlapResult> Hits;
    GetWorld()->OverlapMultiByObjectType(Hits,At,FQuat::Identity,FCollisionObjectQueryParams(ECC_Pawn),
        FCollisionShape::MakeSphere(Radius),Query);
    double Best=FMath::Square(Radius);
    for(const auto& Hit:Hits)
    {
        auto* Horse=Cast<AStableRidingHorse>(Hit.GetActor());
        if(!Horse||Horse->GetRider()||Horse->IsRetreating()||Horse->Visit()!=EStableHorseVisit::Present)continue;
        const FVector Point=Horse->GetActorLocation()+FVector(0,0,32);
        const double Distance=FVector::DistSquared(At,Horse->GetActorLocation());
        if(Distance>=Best || FVector::DotProduct(View.Vector(),(Point-Eye).GetSafeNormal())<-.1)continue;
        FHitResult Wall;
        if(GetWorld()->LineTraceSingleByChannel(Wall,Eye,Point,ECC_Visibility,Query)&&Wall.GetActor()!=Horse)continue;
        Best=Distance;NearbyHorse=Horse;
    }
    return NearbyHorse.Get();
}
