#pragma once
#include "ColdSteelSkillTypes.h"
struct FColdSteelProfile;
struct FColdSteelItem;
namespace ColdSteelSkills
{
    FPSGAME_API FColdSteelSkillDefinition LoadDefinition();
    FPSGAME_API bool Migrate(FColdSteelProfile& Profile);
    FPSGAME_API bool Validate(const FColdSteelProfile& Profile, FString& Reason);
    FPSGAME_API bool IsRifle(const FColdSteelItem* Item);
    FPSGAME_API FColdSteelSkillEffect Effect(const FColdSteelSkillDefinition& Definition, int32 Level);
    FPSGAME_API int32 ExperienceRequired(const FColdSteelSkillDefinition& Definition, int32 Level);
    FPSGAME_API void AddExperience(FColdSteelProfile& Profile, const FColdSteelSkillDefinition& Definition, int32 Amount);
    FPSGAME_API FString EffectSummary(const FColdSteelSkillEffect& Effect);
    FPSGAME_API FColdSteelSkillShot Snapshot(AActor* Shooter);
    FPSGAME_API float ApplyHit(AActor* Shooter, const FHitResult& Hit, float Damage, const FVector& Direction, const FColdSteelSkillShot& Shot);
}
