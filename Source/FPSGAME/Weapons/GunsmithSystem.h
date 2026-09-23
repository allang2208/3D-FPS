#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Dom/JsonObject.h"
#include "WeaponHandling.h"
#include "GunsmithSystem.generated.h"

struct FColdSteelItem;
using FGunsmithParts = TMap<FString,FString>;
struct FMeleeModifiers
{
    double Damage=1, AttackSpeed=1, Range=1, Stamina=1, BlockStamina=1, HitReaction=1, BlockReduction=1;
    // Poise damage is separate from the duration of a successful poise break.
    double ToughnessDamage=1, PhysicalArmorPenetration=0;
    double ComboSecond=1, ComboThird=1;
    double MagicCooldown=1, MagicDamage=1, MagicCost=1, RuneIntelligence=0, RuneWisdom=0;
    double InnateErosionMultiplier=1;
    // Flat additions affect the action multiplier, not the panel damage.
    // Knockback distance is independent of hit-reaction duration.
    double HeavyDamage=1, HeavyDamageAdd=0, Knockback=1;
    double QuickCombatDamageAdd=0, QuickCombatKnockback=1;
    // 每次近战出手按武器冷却口径缩减全部魔法技能CD（金色符文强化：0.5s→1.0s）。
    double CooldownReduceSecondsPerHit=0;
    // RuneVulnerability*=剑刃攻击通道（普攻/连段/重击/旋风/冲刺及未来的剑刃攻击）；
    // QuickCombatRuneVulnerability*=配重锤快速近战专属通道，两种改造件触发条件不同。
    double QuickCombatRuneVulnerability=0, QuickCombatRuneVulnerabilitySeconds=0;
    double HeavyMultiplier(double Base) const {return Base*HeavyDamage+HeavyDamageAdd;}
    double RuneVulnerability=0, RuneVulnerabilitySeconds=0;
    double ParryWindow=1, RiposteSpeed=1, RiposteStamina=1, RiposteSeconds=0;
    double ClovenSeconds=0, ClovenPhysical=1, ClovenToughness=1;
    double ComboMultiplier(int32 Stage) const {return Stage==2?ComboSecond:Stage==3?ComboThird:1.;}
};
struct FGunsmithStats
{
    FMeleeModifiers Melee;
    FWeaponHandling Handling;
    double ADS=0.3, ADSPercent=0, ADSSeconds=0, Recoil=100, Shake=100, RecoilMultiplier=1, ShakeMultiplier=1, StabilityMultiplier=1;
    double Interval=0.13, Reload=1.5, EmptyReload=1.5, Speed=90, Range=40, Spread=1, Damage=25;
    int32 Capacity=30, ActiveParts=0;
    int32 BurstCount=1;
    double BurstDelay=0; // Last shot to next permitted trigger, seconds.
    double BurstCycle(double ShotInterval) const {return (BurstCount-1)*ShotInterval+FMath::Max(ShotInterval,BurstDelay);}
};
struct FGunsmithOption
{
    FMeleeModifiers Melee;
    TArray<FString> CompatibleWeapons;
    FString Id, Name, Description;
    TArray<TPair<FString,int32>> Effects;
    // EmptyReload defaults to Reload, so an option only needs the extra catalog
    // key (empty_reload_mult) when normal and empty reload must differ.
    double ADS=0, ADSSeconds=0, Recoil=1, Shake=1, Stability=1, Speed=1, Interval=1, Spread=1, Range=1, Reload=1, EmptyReload=1;
    int32 Magazine=0;
};
/**
 * 武器特殊性质：工具提示「特殊性质」段的一行。
 * Icon 决定这一行的颜色（见 ColdSteelItemTooltipLayout 的 TraitColor），
 * 所以新增武器只要在目录里写 traits，不必改 UI 代码。
 * 取值：special（特殊攻击）/ magic（魔法）/ mechanic（机制）/ drawback（代价）/ neutral。
 * 数据直接从目录的 FGunsmithWeapon::Source 读，不额外缓存。
 */
struct FGunsmithTrait
{
    FString Icon, Text;
};
struct FGunsmithWeapon
{
    FString Id, Model, Name, Ammo;
    /** 目录显式声明该枪命中会造成硬直；缺省 false = 枪械默认不硬直。 */
    bool bHitStagger = false;
    TArray<FString> Allowed;
    TMap<FString,TArray<FGunsmithOption>> Options;
    FGunsmithStats Base;
    TSharedPtr<FJsonObject> Source;
};
DECLARE_MULTICAST_DELEGATE(FGunsmithChanged);
/** Draft is transient. Persistent parts belong exclusively to an inventory instance. */
UCLASS()
class FPSGAME_API UGunsmithSystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase&) override;
    virtual void Deinitialize() override;
    const FGunsmithWeapon* Weapon(const FString& Definition) const;
    // Weapon remains the firearm contract used by ammunition and combat callers.
    const FGunsmithWeapon* ModifiableWeapon(const FString& Definition) const;
    bool IsMelee(const FString& Definition) const {return MeleeWeapons.Contains(Definition);}
    const FGunsmithOption* Option(const FString& Definition,const FString& Slot,const FString& Id) const;
    FGunsmithParts Installed(const FColdSteelItem&) const;
    FGunsmithParts Normalize(const FString& Definition,const FGunsmithParts&) const;
    FGunsmithStats Calculate(const FString& Definition,const FGunsmithParts&) const;
    bool Begin(const FString& Instance);
    bool Select(const FString& Slot,const FString& OptionId);
    bool Apply();
    bool CanApply(FString& Reason) const;
    void Undo();
    void Close();
    int32 Pending() const;
    bool IsOpen() const {return bOpen;}
    const FString& Instance() const {return InstanceId;}
    const FString& Definition() const {return DefinitionId;}
    const FGunsmithParts& Draft() const {return Preview;}
    const FString& Message()const{return Status;}
    const TArray<FString>& Slots() const{return SlotKeys;}
    const TArray<FString>& Categories()const{return CategoryNames;}
    const TArray<FString>& Defaults()const{return DefaultNames;}
    const TArray<FString>& Slots(const FString& Definition) const {return IsMelee(Definition)?MeleeSlotKeys:SlotKeys;}
    const TArray<FString>& Categories(const FString& Definition) const {return IsMelee(Definition)?MeleeCategoryNames:CategoryNames;}
    const TArray<FString>& Defaults(const FString& Definition) const {return IsMelee(Definition)?MeleeDefaultNames:DefaultNames;}
    FGunsmithChanged OnChanged;
    TSharedPtr<FJsonObject> Catalog;
private:
    TMap<FString,FGunsmithWeapon> Weapons;
    TMap<FString,FGunsmithWeapon> MeleeWeapons;
    TArray<FString> MeleeSlotKeys,MeleeCategoryNames,MeleeDefaultNames;
    void LoadMeleeCatalog();
    TArray<FString> SlotKeys,CategoryNames,DefaultNames;
    FGunsmithParts Preview, Original;
    FString InstanceId, DefinitionId, Status;
    bool bOpen=false;
};
