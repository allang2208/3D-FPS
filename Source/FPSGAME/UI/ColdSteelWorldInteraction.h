#pragma once
#include "CoreMinimal.h"
class APlayerController;
class APawn;
class AActor;
namespace ColdSteelWorldInteraction
{
    /** Keep reach at player eyes when the development camera pulls back. */
    void GetReachViewPoint(const APlayerController* Controller,FVector& Eye,FRotator& View);
    AActor* TraceTarget(const APlayerController* Controller,float Reach=250.f);
    bool IsFocused(const APawn* Pawn,const AActor* Target,float Reach=250.f);
}
