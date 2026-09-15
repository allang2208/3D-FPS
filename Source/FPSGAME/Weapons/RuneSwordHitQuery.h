#pragma once
#include "CoreMinimal.h"

class UWorld;

struct FRuneSwordBladeSample
{
    FVector Base,Tip,Origin,Forward;
};

struct FRuneSwordTraceSettings
{
    float Radius=4.f;
    float ForwardCorridorRadius=0.f; // Zero keeps the ordinary front hemisphere.
    bool bCleavePawns=true;
};

namespace RuneSwordCombat
{
    inline constexpr float BladeRadius=4.f;
    // Centimetres and control-aim space; cosmetic camera motion is excluded.
    TArray<FHitResult> Query(UWorld* World,AActor* Owner,const FRuneSwordBladeSample& From,
        const FRuneSwordBladeSample& To,float Reach,const TSet<TWeakObjectPtr<AActor>>& AlreadyHit,
        const FRuneSwordTraceSettings& Settings=FRuneSwordTraceSettings());
}
