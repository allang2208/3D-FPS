#pragma once
#include "CoreMinimal.h"
#include "FireballTypes.h"
#include "IceSpikeTypes.h"
#include "IceWallTypes.h"
#include "BlizzardTypes.h"
#include "LightningTypes.h"
#include "ElectricMagicTypes.h"
#include "HolyLightTypes.h"
#include "FireMagicTypes.h"
#include "WhirlwindTypes.h"
#include "DashAttackTypes.h"
#include "../Combat/WeaponDamageTypes.h"
#include "../Combat/MonsterToughnessTypes.h"
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
    float DamageBase=5.f, DamagePerLevel=1.f;
    float StrengthFactorBase=1.f, StrengthFactorPerLevel=.02f;
    float KnockbackCM=50.f, RangeCM=200.f;
    float StaminaCost=15.f, StaminaReductionPerLevel=.02f;
};

/** 施放时按等级与当前力量取值的一次结算快照。 */
struct FQuickCombatCast
{
    float Damage=0.f;
    float DamageMultiplier=1.f;
    float KnockbackCM=50.f;
    float RangeCM=200.f;
    float StaminaCost=15.f;
    float ToughnessMultiplier=1.f, BleedChance=0.f;
    bool bAreaHit=false;
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
    /**
     * 持械移速倍率（技能满级前的固定档）。机枪精通把它压到 1 以下作为持械减速；
     * 0 表示"本技能不改移速"，这样未配置的武器专精不会误带一个 0 倍移速。
     */
    float MovementMultiplier = 0.f;
    float CriticalDamageBase = .50f, CriticalDamagePerLevel = .05f;
    int32 LuckPerLevel = 1, CriticalHitExperience = 1, CriticalKillExperience = 10;
    float HeavyMultiplierBase=2.5f,HeavyMultiplierPerLevel=.1f,HeavyChargeBase=2.f,HeavyChargeReductionPerLevel=.05f;
    float UppercutStaminaCost=25.f,UppercutCooldownSeconds=8.f;
    float UppercutRangeMultiplier=1.25f,UppercutReachGrowthPerLevel=.01f;
    int32 HeavyHit2Experience=5,HeavyKill2Experience=12,HeavyHit5Experience=25,HeavyKill5Experience=60;
    FFireballTuning Fireball;
    FIceSpikeTuning IceSpike;
    FLightningTuning Lightning;
    FElectricMagicTuning ElectricMagic;
    FHolyLightTuning HolyLight;
    FQuickCombatTuning QuickCombat;
    FWhirlwindTuning Whirlwind;
    FDashAttackTuning DashAttack;
    FFireMagicTuning FireMagic;
    FIceWallTuning IceWall;
    FBlizzardTuning Blizzard;
};

struct FColdSteelSkillEffect
{
    float DamagePercent = 0, FlatDamage = 0, WeakpointPercent = 0;
    int32 Wisdom = 0;
    int32 Strength=0,Constitution=0;
    float HeavyMultiplier=0,HeavyChargeSeconds=0;
    float UppercutReachMultiplier=1.f;
    float CooldownReduction=0;
    float DodgeDistanceCM = 0, DodgeCostReduction = 0;
    int32 Dexterity = 0;
    float ReloadSpeed = 0;
    float MoveSpeed = 0;
    /** 持械移速固定档：1 = 不影响；机枪精通用它承载持械减速。 */
    float MovementMultiplier = 1.f;
    float CriticalDamageBonus = 0;
    int32 Luck = 0;
};

// Captured at fire time; weapon swaps and later skill upgrades cannot alter a flying round.
class UFPSBallisticsComponent;
class UFPSWeaponFXComponent;
struct FColdSteelSkillShot
{
    FName MasteryId;
    /** 命中时用于查询目录开关（枪械默认不造成硬直）。 */
    FString ItemDefinition;
    /** 命中形式：决定该次命中按哪条韧性抗性折算削韧。 */
    EMonsterAttackForm AttackForm = EMonsterAttackForm::Impact;
    /**
     * 手持枪械发动的近战打击（快速进战的握把底/枪托砸击）。这类动作按近战结算：
     * 不受「枪械默认不硬直」闸门约束，照常累积削韧；不影响 bMelee 的修炼口径。
     */
    bool bMeleeStrike = false;
    int32 ExtraMasteryExperience=0;
    float ArmorPenetration=0;
    float ToughnessDamageMultiplier=1;
    float MagicPenetration=0;
    FWeaponDamageParts DamagePanel;
    float CriticalChance = 0;
    bool bRifle = false;
    bool bPistol = false;
    bool bMelee = false;
    float WeakpointPercent = 0;
    float CriticalDamageBonus = 0;
    /** Guaranteed ammo effects captured on release, independent of later selection. */
    int32 AmmoPoisonStacks = 0, AmmoBleedStacks = 0;
    /** Fired firearm enchantment snapshot. Melee, arrows and spells leave radius zero. */
    float ShatterRadiusCM=0.f, ShatterDamageScale=1.f, BulletSpeedCM=0.f;
    /** Secondary bullets inherit resolved pre-defense damage, never roll crit or bounce again. */
    bool bRicochet=false, bInheritedCritical=false;
    /** 联机命中上报的攻击语义上下文（本地结构体，ForwardHit 透传进 Report）：
     *  弓=拉弦比 0-1；其余武器族留 0。客户端只报"怎么打的"，不报"打了多少"。 */
    float DamageContext = 0.f;
    /** 联机上报：低4位=连段；0x10=重击，0x14=上挑，0x20=旋风，0x40=裂斩波，0x80=快速近战。 */
    uint8 AttackMeta = 0;
    float QuickCombatTigerRoarToughnessBonus=0.f, QuickCombatTigerRoarSeconds=0.f;
    float QuickCombatPhysicalVulnerabilityBonus=0.f, QuickCombatPhysicalVulnerabilitySeconds=0.f;
    TWeakObjectPtr<UFPSBallisticsComponent> BulletSource;
    TWeakObjectPtr<UFPSWeaponFXComponent> BulletFX;
    /** Only the actual melee item's prefix can start an enchantment discharge. */
    float ElectrifiedRadiusCM=0.f;
    int32 ElectrifiedMinLevel=0;
    /** 狂暴仅捕获实际近战物品；当前持有实例仍须与本次攻击来源一致。 */
    FString BerserkSourceInstance;
    float BerserkSpeedPerStack=0.f,BerserkDecaySeconds=0.f;
    int32 BerserkMaxStacks=0;
    /** 大盲注：捕获实际手枪词缀；赌注只由这类命中增加、加成与消耗。 */
    float WagerCriticalBonusPerStack=0.f,WagerSeconds=0.f;
    int32 WagerMaxStacks=0;
    /** 冷静的：实际附魔枪械的攻击快照；直接暴击才增加沉着冷静。 */
    float ComposureStabilityPerStack=0.f,ComposureRecoilReductionPerStack=0.f,ComposureSeconds=0.f;
    int32 ComposureMaxStacks=0;
};

struct FColdSteelProgressNotice
{
    FString Title, Detail, Icon;
    float Duration = 2.8f;
};
