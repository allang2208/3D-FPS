#pragma once
#include "CoreMinimal.h"

// Camera-space wrist path shared by the pistol's crossed kukri and hatchet carries.
namespace PistolOffhandRaise
{
    inline const FVector LowerEnd(-8.f,-6.f,-34.f);

    inline FVector WristOffset(float LowerWeight)
    {
        const FVector Control(-6.f,-7.f,-10.f);
        const float S=FMath::Clamp(LowerWeight,0.f,1.f);
        return 2.f*(1.f-S)*S*Control+S*S*LowerEnd;
    }
}
