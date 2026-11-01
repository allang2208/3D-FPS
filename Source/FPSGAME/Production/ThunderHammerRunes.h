#pragma once
#include "CoreMinimal.h"
struct FColdSteelItem;
struct FColdSteelSkillShot;
struct FLightningCast;
class AActor;

namespace ThunderHammerRunes
{
    inline constexpr const TCHAR* Thunder=TEXT("lei_ming_rune");
    inline constexpr const TCHAR* Echo=TEXT("hui_xiang_rune");
    void Configure(FLightningCast& Spell,const FColdSteelItem* Item);
    int32 Stacks(const FLightningCast& Spell,int32 NativeStacks);
    void ApplyStacks(AActor* Shooter,AActor* Target,const FColdSteelSkillShot& Shot,int32 Count);
    void OnHit(AActor* Shooter,AActor* Target,const FColdSteelSkillShot& Shot);
}
