#pragma once
#include "CoreMinimal.h"
struct FMonsterHitFeedback;
namespace VillageResidentStatus
{
    const TCHAR* Name(const AActor* Actor);
    void Read(AActor& Actor,FMonsterHitFeedback& Out);
}
