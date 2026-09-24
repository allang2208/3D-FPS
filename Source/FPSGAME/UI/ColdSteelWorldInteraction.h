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
    /** Dungeon treasure uses one-shot opening state, separate from warehouse UI. */
    bool IsTreasureChest(const AActor* Target);
    bool IsTreasureChestActivated(const AActor* Target);
    FString TreasureChestPrompt(const AActor* Target);
    bool OpenTreasureChest(const APlayerController* Controller,AActor* Target);
}
