#pragma once
#include "CoreMinimal.h"

struct FCampfireFoodVisual
{
    FName Recipe;
    FString Raw,Cooked,RawMesh,CookedMesh,MotionProfile;
    bool bCustomSpit=false;
    FVector SpitAnchor=FVector::ZeroVector;
};
/** One presentation contract shared by the rack, pickup and first/third-person eating. */
namespace CampfireFood
{
    const TArray<FCampfireFoodVisual>& Catalog();
    const FCampfireFoodVisual* Cooked(const FString& Definition);
    bool Contains(const FString& Definition);
}
