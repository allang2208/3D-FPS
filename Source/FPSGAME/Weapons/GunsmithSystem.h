#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Dom/JsonObject.h"
#include "WeaponHandling.h"
#include "GunsmithSystem.generated.h"

struct FColdSteelItem;
using FGunsmithParts = TMap<FString,FString>;
struct FGunsmithStats
{
    FWeaponHandling Handling;
    double ADS=0.3, ADSPercent=0, Recoil=100, Shake=100, RecoilMultiplier=1, ShakeMultiplier=1;
    double Interval=0.13, Reload=1.5, EmptyReload=1.5, Speed=90, Range=40, Spread=1, Damage=25;
    int32 Capacity=30, ActiveParts=0;
};
struct FGunsmithOption
{
    FString Id, Name, Description;
    TArray<TPair<FString,int32>> Effects;
    double ADS=0, Recoil=1, Shake=1, Speed=1, Interval=1, Spread=1, Range=1, Reload=1;
    int32 Magazine=0;
};
struct FGunsmithWeapon
{
    FString Id, Model, Name, Ammo;
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
    FGunsmithChanged OnChanged;
    TSharedPtr<FJsonObject> Catalog;
private:
    TMap<FString,FGunsmithWeapon> Weapons;
    TArray<FString> SlotKeys,CategoryNames,DefaultNames;
    FGunsmithParts Preview, Original;
    FString InstanceId, DefinitionId, Status;
    bool bOpen=false;
};
