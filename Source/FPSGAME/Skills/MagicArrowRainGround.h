#pragma once
#include "CoreMinimal.h"
#include "MagicArrowRainTypes.h"
class APawn;
namespace MagicArrowRainGround
{
    FVector Flight(const FVector& Start,const FVector& Burst,float Fraction);
    bool Select(APawn* Pawn,const FMagicArrowRainCast& Cast,const FVector& Eye,const FVector& Aim,
        FVector& Ground,FVector& Normal,FVector& Burst,FString& Failure,const FVector* LaunchOrigin=nullptr);
    bool Validate(APawn* Pawn,const FMagicArrowRainCast& Cast,const FVector& Start,
        FVector& Ground,FVector& Normal,FVector& Burst,FString& Failure);
}
