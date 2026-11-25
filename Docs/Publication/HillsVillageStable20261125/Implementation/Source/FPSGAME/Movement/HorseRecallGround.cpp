#include "HorseRiderComponent.h"
#include "StableRidingHorse.h"
#include "../FPSGAMECharacter.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NavigationData.h"
#include "NavigationSystem.h"

bool UHorseRiderComponent::FindRecallSpot(FVector Eye,FRotator Look,float HalfVerticalFov,const AStableRidingHorse* Existing,FTransform& Out) const
{
    auto* Pawn=Player.Get();
    if(!Pawn)return false;
    const FVector Feet=Pawn->GetActorLocation()-FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    const FVector Forward=FRotator(0,Look.Yaw,0).Vector();
    const float VerticalAngle=FMath::DegreesToRadians(FMath::Clamp(HalfVerticalFov+4.f,60.f,90.f));
    const FVector CameraUp=Look.RotateVector(FVector::UpVector);
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const FNavAgentProperties HorseAgent(62.f,204.f);
    const auto* Data=Nav?Nav->GetNavDataForProps(HorseAgent,Feet):nullptr;
    FNavLocation Destination;
    const bool HasRouteData=Data&&Nav->ProjectPointToNavigation(Feet,Destination,FVector(110,110,140),Data);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HorseSummon),false,Pawn);
    Query.AddIgnoredActor(Existing);
    auto FloorAt=[&](FVector Sample,FVector& Ground)
    {
        FHitResult Hit;
        if(!GetWorld()->LineTraceSingleByChannel(Hit,Sample+FVector(0,0,100),Sample-FVector(0,0,180),ECC_Pawn,Query)||
            !Hit.bBlockingHit||Hit.ImpactNormal.Z<.73f||(Hit.GetActor()&&Hit.GetActor()->IsA<APawn>()))return false;
        Ground=Hit.ImpactPoint;return true;
    };
    const auto Hull=FCollisionShape::MakeCapsule(43,94);
    for(const float Distance:{580.f,800.f,1050.f,1400.f})
    for(const float Angle:{0.f,32.f,-32.f,62.f,-62.f})
    {
        FVector Ground;
        if(!FloorAt(Feet-Forward.RotateAngleAxis(Angle,FVector::UpVector)*Distance,Ground))continue;
        FNavLocation Start;
        if(HasRouteData)
        {
            if(!Nav->ProjectPointToNavigation(Ground,Start,FVector(85,85,55),Data)||!FloorAt(Start.Location,Ground))continue;
        }
        const FVector Centre=Ground+FVector(0,0,97);
        // At a steep pitch the ground behind the player can be above or below the view.
        // Use the entire horse's bounding sphere against the rear and vertical planes.
        const FVector FromEye=Centre-Eye;
        const double Depth=FVector::DotProduct(FromEye,Look.Vector());
        const double Height=FMath::Abs(FVector::DotProduct(FromEye,CameraUp));
        constexpr float BodyRadius=190.f;
        if(Depth>-BodyRadius && Height*FMath::Cos(VerticalAngle)-Depth*FMath::Sin(VerticalAngle)<BodyRadius)continue;
        const FVector Toward=(Feet-Ground).GetSafeNormal2D();
        bool Fits=true;
        for(float Along:{-58.f,0.f,58.f})
        {
            const FVector Base=Ground+Toward*Along;
            FVector Support;
            if(!FloorAt(Base,Support)||FMath::Abs(Support.Z-Ground.Z)>32.f ||
                GetWorld()->OverlapBlockingTestByChannel(Support+FVector(0,0,97),FQuat::Identity,ECC_Pawn,Hull,Query))
            {Fits=false;break;}
        }
        if(!Fits)continue;
        // Prefer a walkable lane towards the player during the two-second entrance.
        // This also works while the village nav tile is still being built.
        FVector Last=Ground;
        const int32 Steps=FMath::Max(1,FMath::CeilToInt((HasRouteData?340.f:FVector::Dist2D(Feet,Ground))/55.f));
        for(int32 I=1;I<=Steps;++I)
        {
            const float Along=(HasRouteData?340.f:FVector::Dist2D(Feet,Ground))*I/Steps;
            FVector At=Ground+Toward*Along;At.Z=Last.Z;
            FVector Floor;
            if(!FloorAt(At,Floor)||FMath::Abs(Floor.Z-Last.Z)>34.f||
                GetWorld()->SweepTestByChannel(Last+FVector(0,0,98),Floor+FVector(0,0,98),FQuat::Identity,ECC_Pawn,
                    FCollisionShape::MakeCapsule(44,82),Query)){Fits=false;break;}
            Last=Floor;
        }
        if(!Fits)continue;
        if(HasRouteData)
        {
            FPathFindingQuery Route(Pawn,*Data,Start.Location,Destination.Location,Data->GetDefaultQueryFilter());
            Route.SetAllowPartialPaths(false);
            if(!Nav->TestPathSync(Route))continue;
        }
        Out=FTransform(Toward.Rotation(),Centre);
        return true;
    }
    return false;
}
