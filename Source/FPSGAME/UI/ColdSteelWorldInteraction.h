#pragma once
#include "CoreMinimal.h"
class APlayerController;
class APawn;
class AActor;
namespace ColdSteelWorldInteraction
{
    AActor* TraceTarget(const APlayerController* Controller,float Reach=250.f);
    bool IsFocused(const APawn* Pawn,const AActor* Target,float Reach=250.f);
}
