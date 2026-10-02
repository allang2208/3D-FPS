#pragma once
#include "ColdSteelSkillTypes.h"
struct FColdSteelProfile;
struct FColdSteelItem;
namespace ColdSteelSkills
{
    FPSGAME_API FColdSteelSkillDefinition LoadDefinition(FName Id=TEXT("rifleMastery"));
    FPSGAME_API bool Migrate(FColdSteelProfile& Profile);
    FPSGAME_API bool Validate(const FColdSteelProfile& Profile, FString& Reason);
    FPSGAME_API bool IsRifle(const FColdSteelItem* Item);
    FPSGAME_API bool IsPistol(const FColdSteelItem* Item);
    FPSGAME_API bool IsCriticalHit(const FHitResult& Hit);
    FPSGAME_API FColdSteelSkillEffect Effect(const FColdSteelSkillDefinition& Definition, int32 Level);
    FPSGAME_API int32 ExperienceRequired(const FColdSteelSkillDefinition& Definition, int32 Level);
    FPSGAME_API void AddExperience(FColdSteelProfile& Profile, const FColdSteelSkillDefinition& Definition, int32 Amount);
    FPSGAME_API FString EffectSummary(const FColdSteelSkillEffect& Effect);
    // Ammo effects apply only to fired rounds, never to a rifle-stock/pistol melee strike.
    FPSGAME_API FColdSteelSkillShot Snapshot(AActor* Shooter,const FColdSteelItem* Item=nullptr,bool bFiredRound=false);
    FPSGAME_API float ApplyHit(AActor* Shooter, const FHitResult& Hit, float Damage, const FVector& Direction, const FColdSteelSkillShot& Shot,FWeaponDamageResult* Result=nullptr);
    // Called once after a confirmed enemy contact, including weapon-specific magic attacks.
    FPSGAME_API void GrantBerserkOnWeaponHit(AActor* Shooter,const FColdSteelSkillShot& Shot);
    // M3 联机：客户端（非权威射手）命中不本地结算，由插件注册的转发函数送权威服务器。返回 true=已转发。
    using FColdSteelNetHitForward = bool (*)(AActor* Shooter, const FHitResult& Hit, float Damage, const FVector& Direction, const FColdSteelSkillShot& Shot);
    FPSGAME_API FColdSteelNetHitForward& NetHitForward();
    // M3 联机：击杀奖励按射手归属发放（主机走单例，远端玩家走其影子档案）。
    FPSGAME_API void AwardKillByOwner(UGameInstance* GameInstance, AController* Instigator, AActor* Victim, int64 ExperienceReward);
    // Confirmed death effects also apply to targets that grant no kill rewards.
    FPSGAME_API void NotifyKillByOwner(UGameInstance* GameInstance, AController* Instigator, AActor* Victim);
}
