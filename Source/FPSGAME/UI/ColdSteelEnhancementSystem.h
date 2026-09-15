#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ColdSteelInventoryTypes.h"
#include "Dom/JsonObject.h"
#include "ColdSteelEnhancementSystem.generated.h"

struct FColdSteelEnhanceCost {FString Definition,Name;int64 Need=0,Have=0;bool BackpackOnly=false;};
struct FColdSteelEnchantOption {FString Id,Item,Name,Slot,Restriction,Description;int64 Dust=0;TSharedPtr<FJsonObject> Effects;};
struct FColdSteelEnhanceQuote
{
    FString ItemId,ScrollId,Reason;
    int64 Revision=0;
    bool Valid=false;
    FColdSteelItem Before,After;
    TArray<FColdSteelEnhanceCost> Costs;
};
/** Single-player processing transactions, persisted in the existing item instance JSON. */
UCLASS()
class FPSGAME_API UColdSteelEnhancementSystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase&) override;
    bool Supports(const FColdSteelItem&) const;
    bool CanEnchant(const FColdSteelItem&,const FColdSteelEnchantOption&) const;
    int32 MaxLevel(const FColdSteelItem&) const;
    FColdSteelEnhanceQuote Quote(const FString& ItemId,const FString& ScrollId=TEXT("")) const;
    bool Apply(const FColdSteelEnhanceQuote& Quote,FString& Message);
    double ProcessedDamage(const FColdSteelItem&,double WeaponBase,double CharacterAttack) const;
    TSharedPtr<const FJsonObject> AttackFormula(const FColdSteelItem&) const;
    double AttackFormulaAttribute(const FColdSteelItem&,FName Key) const;
    double Defense(const FColdSteelItem&) const;
    double Effect(const FColdSteelItem&,const TCHAR* Key,double Default=0) const;
    double CraftEffect(const FColdSteelItem&,const TCHAR* Key,double Default=0) const;
    FString Affix(const FColdSteelItem&,const TCHAR* Slot) const;
    const TArray<FColdSteelEnchantOption>& Scrolls()const{return Options;}
    const FColdSteelEnchantOption* Scroll(const FString&)const;
    int64 BackpackScrollCount(const FString& Definition)const;
    double IncreasePerLevel()const{return Increase;}
private:
    TSharedPtr<FJsonObject> WeaponFormulas;
    TArray<FColdSteelEnchantOption> Options;
    int32 WeaponMax=15,ArmorMax=10;
    int64 BaseGold=100,Stones=1;
    double Growth=1.5,Increase=.05;
    bool Ready=false;
};
