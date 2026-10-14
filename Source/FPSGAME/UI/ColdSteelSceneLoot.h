#pragma once
#include "CoreMinimal.h"

class AColdSteelSceneContainer;

/** Authored facility search pools. No player, actor-spawn order or global RNG in a roll. */
namespace ColdSteelSceneLoot
{
    bool IsBound(const AColdSteelSceneContainer* Container);
    bool Roll(const FString& ContainerId,int32 RunSeed,TArray<TPair<FString,int64>>& OutLoot);
    FName Claim(const FString& ContainerId);
}
