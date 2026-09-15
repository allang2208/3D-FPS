#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "Engine/GameInstance.h"
#include "../Combat/CoreCombatFormula.h"
#include "Dom/JsonObject.h"
#include "../Combat/CombatItemFormula.h"
#include "Serialization/JsonSerializer.h"
double UColdSteelStatusModel::EquipmentBonus(FName Key) const
{return EquipmentBonusFor(Current,Key);}
double UColdSteelStatusModel::EquipmentBonusFor(const FColdSteelProfile& State,FName Key)
{
    double Sum=0;const FString Name=Key==TEXT("intt")?TEXT("int"):Key.ToString();
    for(const auto& Item:State.Items)if(Item.Place==1)
    {
        if(ColdSteelInventory::Text(Item,TEXT("weaponType"))==TEXT("shield")&&Item.Cell!=(State.ActiveWeaponSlot==6?8:11))continue;
        const auto O=CombatItemFormula::Read(Item);if(!O)continue;
        double L=0;O->TryGetNumberField(TEXT("enhanceLevel"),L);
        for(const auto& Pair:TArray<TPair<FString,double>>{{TEXT("bonusStats"),1},{TEXT("bonusPerEnhance"),L}})
        {const TSharedPtr<FJsonObject>* B=nullptr;double V=0;if(O->TryGetObjectField(Pair.Key,B)&&(*B)->TryGetNumberField(Name,V))Sum+=V*Pair.Value;}
    }
    return Sum;
}
double UColdSteelStatusModel::ResourceMaximum(const FColdSteelProfile& State,bool Mana)
{
    auto Raw=[&](FName Key){return State.Attributes.FindRef(Key)+EquipmentBonusFor(State,Key);};
    return 100+(State.Level-1)*10+(Mana?Raw(TEXT("wis"))*10+Raw(TEXT("intt"))*5:Raw(TEXT("con"))*10)+EquipmentBonusFor(State,Mana?TEXT("maxMp"):TEXT("maxHp"));
}
int32 UColdSteelStatusModel::Attribute(FName Key) const { const int32* Value = Attributes.Find(Key); return (Value ? *Value : 0)+int32(EquipmentBonus(Key))+(Key==TEXT("str")?MasteryEffect(TEXT("machineGunMastery")).Strength+MasteryEffect(TEXT("heavyStrike")).Strength:0)+(Key==TEXT("con")?MasteryEffect(TEXT("shotgunMastery")).Constitution:0)+(Key==TEXT("wis")?RifleEffect().Wisdom:0)+(Key==TEXT("dex")?DexterousHandsEffect().Dexterity+PistolEffect().Dexterity+MasteryEffect(TEXT("bowMastery")).Dexterity:0)+(Key==TEXT("luck")?CriticalStrikeEffect().Luck:0); }
bool UColdSteelStatusModel::AllocateAttribute(FName Key)
{
    SyncRuntime(); auto Next=Snapshot(); int32* Value=Next.Attributes.Find(Key);
    if (!Value || Next.Points <= 0 || *Value >= 1000000) return false;
    ++*Value; --Next.Points; return CommitState(Next);
}
void UColdSteelStatusModel::GrantAttributePoints(int32 Amount)
{
    if (Amount <= 0) return;
    SyncRuntime(); auto Next=Snapshot(); Next.Points=static_cast<int32>(FMath::Min<int64>(int64(Next.Points)+Amount,1000000)); CommitState(Next);
}
float UColdSteelStatusModel::Derived(FName Key) const
{
    auto Total=[&](FName Key){return double(Attribute(Key))+EquipmentBonus(Key)-int32(EquipmentBonus(Key));};
    const CoreCombatFormula::Attributes A{Total(TEXT("str")),Total(TEXT("dex")),Total(TEXT("intt")),
        Total(TEXT("con")),Total(TEXT("wis")),Total(TEXT("luck"))};
    const auto S=CoreCombatFormula::Player(A,Level);
    auto Raw=A;Raw.Str-=MasteryEffect(TEXT("machineGunMastery")).Strength+MasteryEffect(TEXT("heavyStrike")).Strength;Raw.Con-=MasteryEffect(TEXT("shotgunMastery")).Constitution;Raw.Dex-=DexterousHandsEffect().Dexterity+PistolEffect().Dexterity+MasteryEffect(TEXT("bowMastery")).Dexterity;Raw.Wis-=RifleEffect().Wisdom;Raw.Luck-=CriticalStrikeEffect().Luck;
    const auto Resources=CoreCombatFormula::Player(Raw,Level);
    if (Key == TEXT("atk")) return AdjustCombatStat(Key,S.Atk+CoreCombatFormula::Round(EquipmentBonus(Key)));
    if (Key == TEXT("def")) {float Equipment=0;if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())for(const auto& Item:Current.Items)if(Item.Place==1&&(ColdSteelInventory::Text(Item,TEXT("weaponType"))!=TEXT("shield")||Item.Cell==(Current.ActiveWeaponSlot==6?8:11)))Equipment+=E->Defense(Item);double Value=S.Def+Equipment;if(const auto* I=Equipped())if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())Value=std::floor(Value*(1+E->CraftEffect(*I,TEXT("defensePercent"))));return AdjustCombatStat(Key,Value);}
    if (Key == TEXT("matk")) return AdjustCombatStat(Key,S.Matk+CoreCombatFormula::Round(EquipmentBonus(Key))+EquipmentMagicAttack());
    if (Key == TEXT("mdef")) return AdjustCombatStat(Key,S.Mdef);
    if (Key == TEXT("critRes")) return S.CritRes;
    if (Key == TEXT("crit")) return AdjustCombatStat(Key,S.Crit+CoreCombatFormula::Round(EquipmentBonus(Key)));
    if (Key == TEXT("speed")) return std::floor(S.Speed*CombatMoveMultiplier());
    if (Key == TEXT("mpRegen")) return Resources.MpRegen*TributeEffect(TEXT("mpRegenPercent"));
    if (Key == TEXT("aspd")) return S.AttackSpeed;
    if (Key == TEXT("staminaRegen")) return Resources.StaminaRegen*SetEffect(Key)*TributeEffect(TEXT("staminaRegenPercent"));
    if (Key == TEXT("maxStamina")) return MaxStamina();
    if (Key == TEXT("maxHp")) return ResourceMaximum(Current,false);
    if (Key == TEXT("maxMp")) return ResourceMaximum(Current,true);
    if(Key==TEXT("hpRegen"))return (1+TributeEffect(TEXT("hpRegenFlat")))*TributeEffect(TEXT("hpRegenPercent"));
    return 0;
}
