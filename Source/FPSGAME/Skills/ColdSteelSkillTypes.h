#pragma once
#include "CoreMinimal.h"
#include "ColdSteelSkillTypes.generated.h"

USTRUCT(BlueprintType)
struct FColdSteelSkillProgress
{
    GENERATED_BODY()
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 Level = 1;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 Experience = 0;
};

struct FColdSteelSkillDefinition
{
    FName Id = TEXT("rifleMastery");
    FString Name = TEXT("步枪精通");
    FString Description = TEXT("精通步枪的精准射击，每颗子弹都命中要害。");
    FString Icon = TEXT("Skills/rifle_mastery.png");
    FString UpgradeSound = TEXT("Skills/player_upgrade.wav");
    int32 MaxLevel = 20, ExperiencePerLevel = 100, KillExperience = 10, CriticalExperience = 5;
    float DamagePercentPerLevel = .01f, FlatDamagePerLevel = 1.f, WeakpointPerLevel = .01f;
    int32 WisdomPerLevel = 1;
};

struct FColdSteelSkillEffect
{
    float DamagePercent = 0, FlatDamage = 0, WeakpointPercent = 0;
    int32 Wisdom = 0;
};

// Captured at fire time; weapon swaps and later skill upgrades cannot alter a flying round.
struct FColdSteelSkillShot
{
    bool bRifle = false;
    float WeakpointPercent = 0;
};

struct FColdSteelProgressNotice
{
    FString Title, Detail, Icon;
    float Duration = 2.8f;
};
