#pragma once

#include "CoreMinimal.h"

class UWorld;

namespace VillagePresentationView
{
    // Distance at a 90 degree horizontal field of view, including the physical scope.
    double Distance(UWorld& World, const FVector& Center, double Radius = 0., bool* HasView = nullptr);
    struct FCanopyView
    {
        TArray<FVector4d, TInlineAllocator<2>> EyesAndScales;
        bool bScoped = false;
        bool Update(UWorld& World, bool& bDiscontinuity);
    };
}
