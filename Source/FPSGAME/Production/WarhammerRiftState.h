#pragma once
#include "CoreMinimal.h"

namespace WarhammerRift
{
    inline constexpr int32 PoolSize=4,Stations=96;
    inline constexpr const TCHAR* Material=TEXT("/Game/Weapons/AzureRunesword20260913/WristRiftV3/M_RuneRift.M_RuneRift");
    struct FTrail
    {
        TArray<FVector> Inner,Outer,CrossInner,CrossOuter;
        FVector Drift=FVector::ZeroVector;
        float FadeAge=-1.f,Strength=.1f;
        bool bDirty=false,bCrossed=false;
        void Reset()
        {
            Inner.Reset();Outer.Reset();CrossInner.Reset();CrossOuter.Reset();
            FadeAge=-1.f;bDirty=true;bCrossed=false;
        }
    };
}
