#pragma once

#include "EngineUtils.h"
#include "GameFramework/Actor.h"

namespace VillageShop
{
    // Both workshops belong to the same streamed village, including their ruined versions.
    template<class TOppositeShop>
    void FaceAcrossStreet(const AActor& Shop, const FVector& Outward, FTransform& ResidentPose)
    {
        FVector Facing = Outward;
        for (TActorIterator<TOppositeShop> It(Shop.GetWorld()); It; ++It)
        {
            if (It->GetLevel() != Shop.GetLevel()) continue;
            const FVector Towards = It->GetActorLocation() - ResidentPose.GetLocation();
            if (Towards.SizeSquared2D() > UE_KINDA_SMALL_NUMBER) Facing = Towards;
            break;
        }
        ResidentPose.SetRotation(FRotator(0., Facing.Rotation().Yaw, 0.).Quaternion());
    }
}
