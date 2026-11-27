#pragma once
#include "CoreMinimal.h"
#include "../Combat/CombatChill.h"
#include "AbsoluteZeroTypes.generated.h"

/** Ultimate Ice Nova ("绝对零度") tuning loaded from Content/ColdSteelData/skills.json. */
struct FAbsoluteZeroTuning
{
    float DamageBase=90.f, DamagePerLevel=12.f, MagicBase=16.f, MagicPerLevel=1.15f;
    float ShatterDamageBase=40.f, ShatterDamagePerLevel=6.f, ShatterMagicBase=6.f, ShatterMagicPerLevel=.45f;
    float WallShardDamageBase=25.f, WallShardDamagePerLevel=4.f, WallShardMagicBase=2.2f, WallShardMagicPerLevel=.18f;
    float RadiusBaseCM=1000.f, RadiusPerLevelCM=30.f, InnerRadiusCM=600.f;
    float ManaBase=150.f, ManaPerLevel=3.f, Cooldown=42.f, CooldownReduction=7.f;
    float ChannelSeconds=1.5f, ArmorChannelSeconds=1.1f;
    float ChannelDamageReduction=.35f, ArmorChannelDamageReduction=.50f;
    float ExpandSeconds=.35f, KnockbackBaseCM=350.f, KnockbackMaxCM=500.f, ToughnessDamage=380.f;
    int32 InnerChillStacks=10, OuterChillStacks=6;
    float ChillSeconds=4.5f, ChillBonusPerStack=.035f, ChillBonusCap=.70f;
    int32 ShatterChillThreshold=10;
    int32 MaxDetonatedWalls=2, MaxShardsPerWall=24, MaxFullShardsPerTarget=6;
    float OverflowShardScale=.25f;
    float WallShardRangeCM=1800.f, WallShardSpeedCM=2600.f, WallShardConeDegrees=28.f;
    int32 HitExperience=2, KillExperience=10, MultiHitExperience=8, MultiKillExperience=10, WallComboExperience=6;
    bool bRequiresStaff=true;
};

/** Immutable snapshot captured when Absolute Zero begins channeling. */
USTRUCT()
struct FAbsoluteZeroCast
{
    GENERATED_BODY()
    UPROPERTY() float Damage=0.f;
    UPROPERTY() float ShatterDamage=0.f;
    UPROPERTY() float WallShardDamage=0.f;
    UPROPERTY() float Radius=1000.f;
    UPROPERTY() float InnerRadius=600.f;
    UPROPERTY() float ManaCost=150.f;
    UPROPERTY() float Cooldown=42.f;
    UPROPERTY() float ChannelSeconds=1.5f;
    UPROPERTY() float ArmorChannelSeconds=1.1f;
    UPROPERTY() float ChannelDamageReduction=.35f;
    UPROPERTY() float ArmorChannelDamageReduction=.50f;
    UPROPERTY() float ExpandSeconds=.35f;
    UPROPERTY() float KnockbackBase=350.f;
    UPROPERTY() float KnockbackMax=500.f;
    UPROPERTY() float ToughnessDamage=380.f;
    UPROPERTY() int32 InnerChillStacks=10;
    UPROPERTY() int32 OuterChillStacks=6;
    UPROPERTY() float ChillSeconds=4.5f;
    UPROPERTY() float ChillBonusPerStack=.035f;
    UPROPERTY() float ChillBonusCap=.70f;
    UPROPERTY() int32 ShatterChillThreshold=10;
    UPROPERTY() int32 MaxDetonatedWalls=2;
    UPROPERTY() int32 MaxShardsPerWall=24;
    UPROPERTY() int32 MaxFullShardsPerTarget=6;
    UPROPERTY() float OverflowShardScale=.25f;
    UPROPERTY() float WallShardRange=1800.f;
    UPROPERTY() float WallShardSpeed=2600.f;
    UPROPERTY() float WallShardConeDegrees=28.f;
    UPROPERTY() float CastSpeed=1.f;
    UPROPERTY() float CriticalChance=0.f;
    UPROPERTY() float CriticalDamageBonus=0.f;
    UPROPERTY() float MagicPenetration=0.f;
    UPROPERTY() float MagicDamageBonus=0.f;
    UPROPERTY() float PendantChillSlow=0.f;
    UPROPERTY() float PendantChillSeconds=3.f;
    UPROPERTY() int32 CastHasteStacks=0;
    UPROPERTY() float CastHasteDuration=5.f;
    UPROPERTY() bool bGrantChain=false;
    UPROPERTY() bool bRequiresStaff=true;
    UPROPERTY() bool bIceArmorSynergy=false;
};

/** Compact per-wall snapshot replicated inside the burst actor for deterministic client shrapnel replay. */
USTRUCT()
struct FAbsoluteZeroDetonatedWall
{
    GENERATED_BODY()
    UPROPERTY() FVector_NetQuantize Location=FVector::ZeroVector;
    UPROPERTY() FRotator Rotation=FRotator::ZeroRotator;
    UPROPERTY() float MinAlong=-100.f;
    UPROPERTY() float MaxAlong=100.f;
    UPROPERTY() float GroundZ=0.f;
    UPROPERTY() float Height=220.f;
    UPROPERTY() float HealthRatio=1.f;
    UPROPERTY() float TriggerDistance=60.f;
    UPROPERTY() int32 ShardCount=12;
    UPROPERTY() int32 Seed=0;
};

struct FAbsoluteZeroRewards
{
    int32 Hits=0, Kills=0, CriticalHits=0, CriticalKills=0, WallComboHits=0;
    bool bMultiHit=false;
};
