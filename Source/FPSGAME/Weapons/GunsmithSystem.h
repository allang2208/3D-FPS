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
    double Damage=1, AttackSpeed=1, Range=1, Stamina=1, HitReaction=1, BlockReduction=1;
    double ComboSecond=1, ComboThird=1;
    double MagicCooldown=1, MagicDamage=1, MagicCost=1, RuneIntelligence=0, RuneWisdom=0;
    // Flat additions affect the action multiplier, not the panel damage.
    // Knockback distance is independent of hit-reaction duration.
    double HeavyDamage=1, HeavyDamageAdd=0, Knockback=1;
    double QuickCombatDamageAdd=0, QuickCombatKnockback=1;
    double HeavyMultiplier(double Base) const {return Base*HeavyDamage+HeavyDamageAdd;}
    double RuneVulnerability=0, RuneVulnerabilitySeconds=0;
    double ParryWindow=1, RiposteSpeed=1, RiposteStamina=1, RiposteSeconds=0;
    double ComboMultiplier(int32 Stage) const {return Stage==2?ComboSecond:Stage==3?ComboThird:1.;}
};
struct FGunsmithStats
{
    FMeleeModifiers Melee;
    FWeaponHandling Handling;
    double ADS=0.3, ADSPercent=0, ADSSeconds=0, Recoil=100, Shake=100, RecoilMultiplier=1, ShakeMultiplier=1, StabilityMultiplier=1;
    double Interval=0.13, Reload=1.5, EmptyReload=1.5, Speed=90, Range=40, Spread=1, Damage=25;
    int32 Capacity=30, ActiveParts=0;
};
struct FGunsmithOption
{
    FMeleeModifiers Melee;
    TArray<FString> CompatibleWeapons;
    FString Id, Name, Description;
    TArray<TPair<FString,int32>> Effects;
    double ADS=0, ADSSeconds=0, Recoil=1, Shake=1, Stability=1, Speed=1, Interval=1, Spread=1, Range=1, Reload=1;
    int32 Magazine=0;
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
