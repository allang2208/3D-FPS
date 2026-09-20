#pragma once
#include "CoreMinimal.h"
#include "FireballTypes.h"
#include "IceSpikeTypes.h"
#include "../Combat/WeaponDamageTypes.h"
#include "ColdSteelSkillTypes.generated.h"

USTRUCT(BlueprintType)
struct FColdSteelSkillProgress
{
    GENERATED_BODY()
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 Level = 1;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 Experience = 0;
};

/** 快速进战：独立配重锤/枪托打击的固定档参数（skills.json: quickCombat）。 */
struct FQuickCombatTuning
{
    float DamageBase=25.f, DamagePerLevel=5.f;
    float StrengthFactorBase=5.f, StrengthFactorPerLevel=.1f;
    float KnockbackCM=100.f, RangeCM=200.f;
    float StunBase=2.5f, StunPerLevel=.1f;
    float Cooldown=12.f;
};

/** 施放时按等级与当前力量取值的一次结算快照。 */
struct FQuickCombatCast
{
    float Damage=0.f;
    float DamageMultiplier=1.f;
    float KnockbackCM=100.f;
    float StunSeconds=0.f;
    float RangeCM=200.f;
    float CooldownSeconds=12.f;
};

struct FColdSteelSkillDefinition
{
    FName Id = TEXT("rifleMastery");
    FString Name = TEXT("步枪精通");
    FString Description = TEXT("精通步枪的精准射击，每颗子弹都命中要害。");
    FString Icon = TEXT("Skills/rifle_mastery_cold_steel.png");
    FString UpgradeSound = TEXT("Skills/player_upgrade.wav");
    int32 MaxLevel = 20, ExperiencePerLevel = 100, KillExperience = 10, CriticalExperience = 5;
    float DamagePercentPerLevel = .01f, FlatDamagePerLevel = 1.f, WeakpointPerLevel = .01f;
    int32 WisdomPerLevel = 1;
    int32 StrengthPerLevel=0,ConstitutionPerLevel=0,HitExperience=0,MultiHitExperience=0;
    float CooldownReductionPerLevel=0;
    float DodgeDistanceCMPerLevel = 10.f, DodgeCostReductionPerLevel = .015f;
    int32 UseExperience = 1, MeleeDodgeExperience = 5, RangedDodgeExperience = 10;
    int32 DexterityPerLevel = 1, ReloadExperience = 5;
    int32 MeleeHitExperience=0,MeleeKillExperience=0;
    float ReloadSpeedPerLevel = .01f;
    float MoveSpeedPerLevel = .01f;
    float CriticalDamageBase = .50f, CriticalDamagePerLevel = .05f;
    int32 LuckPerLevel = 1, CriticalHitExperience = 1, CriticalKillExperience = 10;
    float HeavyMultiplierBase=2.5f,HeavyMultiplierPerLevel=.1f,HeavyChargeBase=2.f,HeavyChargeReductionPerLevel=.05f;
    int32 HeavyHit2Experience=5,HeavyKill2Experience=12,HeavyHit5Experience=25,HeavyKill5Experience=60;
    FFireballTuning Fireball;
    FIceSpikeTuning IceSpike;
    FQuickCombatTuning QuickCombat;
};

struct FColdSteelSkillEffect
{
    float DamagePercent = 0, FlatDamage = 0, WeakpointPercent = 0;
    int32 Wisdom = 0;
    int32 Strength=0,Constitution=0;
    float HeavyMultiplier=0,HeavyChargeSeconds=0;
    float CooldownReduction=0;
    float DodgeDistanceCM = 0, DodgeCostReduction = 0;
    int32 Dexterity = 0;
    float ReloadSpeed = 0;
    float MoveSpeed = 0;
    float CriticalDamageBonus = 0;
    int32 Luck = 0;
};

// Captured at fire time; weapon swaps and later skill upgrades cannot alter a flying round.
struct FColdSteelSkillShot
{
    FName MasteryId;
    /** 命中时用于查询目录开关（枪械默认不造成硬直）。 */
    FString ItemDefinition;
    int32 ExtraMasteryExperience=0;
    float ArmorPenetration=0;
    float MagicPenetration=0;
    FWeaponDamageParts DamagePanel;
    float CriticalChance = 0;
    bool bRifle = false;
    bool bPistol = false;
    bool bMelee = false;
    float WeakpointPercent = 0;
    float CriticalDamageBonus = 0;
};

struct FColdSteelProgressNotice
{
    FString Title, Detail, Icon;
    float Duration = 2.8f;
};
