#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ColdSteelInventoryTypes.h"
#include "Dom/JsonObject.h"
#include "ColdSteelEnhancementSystem.generated.h"

class UColdSteelStatusModel;

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
DECLARE_MULTICAST_DELEGATE_TwoParams(FColdSteelEnhancementNetworkResult,bool,const FString&);

/** Processing uses the existing inventory transaction and instance JSON. */
UCLASS()
class FPSGAME_API UColdSteelEnhancementSystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase&) override;
    bool Supports(const FColdSteelItem&) const;
    static void PreserveAuthoritative(TArray<FColdSteelItem>& Incoming,const TArray<FColdSteelItem>& Authority);
    bool CanEnchant(const FColdSteelItem&,const FColdSteelEnchantOption&) const;
    int32 MaxLevel(const FColdSteelItem&) const;
    FColdSteelEnhanceQuote Quote(const FString& ItemId,const FString& ScrollId=TEXT("")) const;
    const FColdSteelItem* BenchItem() const;
    bool Transfer(const FString& ItemId,FString& Message);
    bool TransferAuthority(const FString& ItemId,const FString& ExpectedBenchId,FString& Message);
    bool Apply(const FColdSteelEnhanceQuote& Quote,FString& Message);
    /** Called only inside the validated workstation authority transaction. */
    bool ApplyAuthority(const FColdSteelEnhanceQuote& Quote,FString& Message);
    FColdSteelEnhancementNetworkResult OnNetworkResult;
    bool Pending() const;
    void NetworkFinished(bool Success,const FString& Message);
    // Negative override uses the instance's installed melee parts; previews pass their draft multiplier.
    double ProcessedDamage(const FColdSteelItem&,double WeaponBase,double CharacterAttack,double MeleeDamageMultiplier=-1,const UColdSteelStatusModel* Profile=nullptr) const;
    TSharedPtr<const FJsonObject> AttackFormula(const FColdSteelItem&) const;
    double AttackFormulaAttribute(const FColdSteelItem&,FName Key,const UColdSteelStatusModel* Profile=nullptr) const;
    double Defense(const FColdSteelItem&) const;
    /** 装备魔法防御（`defense.magicBase` / `magicPerEnhance`）；未声明返回 0。 */
    double MagicDefense(const FColdSteelItem&) const;
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
    int64 BaseSouls=100,Stones=1;
    double Growth=1.5,Increase=.05;
    bool Ready=false;
    bool bNetworkPending=false,bLastNetworkSuccess=false;
    FString LastNetworkMessage;
};
