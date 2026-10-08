#include "ColdSteelStatusModel.h"
#include "../Weapons/JingangRuneComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "ColdSteelEnhancementSystem.h"
#include "Engine/GameInstance.h"
#include "../Combat/CoreCombatFormula.h"
#include "Dom/JsonObject.h"
#include "../Combat/CombatItemFormula.h"
#include "Serialization/JsonSerializer.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
float UColdSteelStatusModel::BerserkAttackSpeedMultiplier() const
{
    const auto* Status=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
    return Status?Status->BerserkAttackSpeed():1.f;
}
double UColdSteelStatusModel::EquipmentBonus(FName Key) const
{return EquipmentBonusFor(Current,Key);}
double UColdSteelStatusModel::EquipmentBonusFor(const FColdSteelProfile& State,FName Key)
{
    double Sum=0;const FString Name=Key==TEXT("intt")?TEXT("int"):Key.ToString();
    for(const auto& Item:State.Items)if(Item.Place==1)
    {
        if(ColdSteelInventory::Text(Item,TEXT("weaponType"))==TEXT("shield")&&Item.Cell!=(State.ActiveWeaponSlot==6?8:11))continue;
        const auto O=CombatItemFormula::ReadOnly(Item);if(!O)continue;
        double L=0;O->TryGetNumberField(TEXT("enhanceLevel"),L);
        for(const auto& Pair:TArray<TPair<FString,double>>{{TEXT("bonusStats"),1},{TEXT("bonusPerEnhance"),L},{TEXT("_enchantEffects"),1}})
        {const TSharedPtr<FJsonObject>* B=nullptr;double V=0;if(O->TryGetObjectField(Pair.Key,B)&&(*B)->TryGetNumberField(Name,V))Sum+=V*Pair.Value;}
    }
    return Sum;
}
double UColdSteelStatusModel::ResourceMaximum(const FColdSteelProfile& State,bool Mana)
{
    auto Raw=[&](FName Key){return (State.Attributes.FindRef(Key)+EquipmentBonusFor(State,Key))*State.Infection.AttributeMultiplier()*State.Survival.AttributeMultiplier();};
    return 100+(State.Level-1)*10+(Mana?Raw(TEXT("wis"))*10+Raw(TEXT("intt"))*5:Raw(TEXT("con"))*10)+EquipmentBonusFor(State,Mana?TEXT("maxMp"):TEXT("maxHp"));
}
double UColdSteelStatusModel::Attribute(FName Key) const
{
    if(Key==TEXT("int"))Key=TEXT("intt");
    const double Base=Attributes.FindRef(Key)+EquipmentBonus(Key)
        +(Key==TEXT("str")?MasteryEffect(TEXT("machineGunMastery")).Strength+MasteryEffect(TEXT("heavyStrike")).Strength+MasteryEffect(TEXT("swordUppercut")).Strength+MasteryEffect(TEXT("whirlwind")).Strength:0)
        +(Key==TEXT("con")?MasteryEffect(TEXT("shotgunMastery")).Constitution:0)
        +(Key==TEXT("wis")?RifleEffect().Wisdom:0)
        +(Key==TEXT("dex")?DexterousHandsEffect().Dexterity+PistolEffect().Dexterity+MasteryEffect(TEXT("bowMastery")).Dexterity:0)
        +(Key==TEXT("luck")?CriticalStrikeEffect().Luck:0);
    return Base*EffectiveAttributeMultiplier();
}
double UColdSteelStatusModel::EffectiveAttributeMultiplier() const
{return InfectionAttributeMultiplier()*Current.Survival.AttributeMultiplier();}

void UColdSteelStatusModel::SetSurvivalState(const FFPSSurvivalState& State,AActor* Source)
{
    if(!Source||Source!=CurrentPawn.Get())return;
    const bool WasDepleted=Current.Survival.IsSanityDepleted();
    Current.Survival=State;bTrainingDirty=true;
    if(WasDepleted==Current.Survival.IsSanityDepleted())return;
    // Derived penalties never overwrite the allocated or equipped attributes.
    if(auto* Health=Source->FindComponentByClass<UFPSCombatHealthComponent>())
    {
        Health->MaxHealth=Derived(TEXT("maxHp"));
        Health->Health=FMath::Min(Health->Health,Health->MaxHealth);Current.Health=Health->Health;
    }
    Current.Mana=FMath::Min(Current.Mana,Derived(TEXT("maxMp")));
    const float Before=Current.Stamina;
    Current.Stamina=FMath::Min(Current.Stamina,MaxStamina());
    if(Before!=Current.Stamina)OnStaminaChanged.Broadcast();
    OnChanged.Broadcast();
}
void UColdSteelStatusModel::SetInfectionState(const FInfectionState& State,bool bStageChanged)
{
    Current.Infection=State;
    bTrainingDirty=true; // Use the existing coalesced autosave; no per-tick disk writes.
    if(!bStageChanged)return;
    if(CurrentPawn.IsValid())if(auto* Health=CurrentPawn->FindComponentByClass<UFPSCombatHealthComponent>())
    {
        Health->MaxHealth=Derived(TEXT("maxHp"));
        Health->Health=FMath::Min(Health->Health,Health->MaxHealth);
        Current.Health=Health->Health;
    }
    Current.Mana=FMath::Min(Current.Mana,Derived(TEXT("maxMp")));
    OnChanged.Broadcast();
}
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
    // These branches depend only on raw resources, not the full combat-stat tree.
    if (Key == TEXT("maxStamina")) return MaxStamina();
    if (Key == TEXT("maxHp")) return ResourceMaximum(Current,false);
    if (Key == TEXT("maxMp")) return ResourceMaximum(Current,true);
    if (Key == TEXT("hpRegen")) return (1+TributeEffect(TEXT("hpRegenFlat"))+DungeonEffect(TEXT("hpRegenFlat")))*TributeEffect(TEXT("hpRegenPercent"));
    auto Total=[&](FName Key){return Attribute(Key);};
    const CoreCombatFormula::Attributes A{Total(TEXT("str")),Total(TEXT("dex")),Total(TEXT("intt")),
        Total(TEXT("con")),Total(TEXT("wis")),Total(TEXT("luck"))};
    const auto S=CoreCombatFormula::Player(A,Level);
    const double AttributeScale=EffectiveAttributeMultiplier();
    auto Raw=A;Raw.Str-=(MasteryEffect(TEXT("machineGunMastery")).Strength+MasteryEffect(TEXT("heavyStrike")).Strength+MasteryEffect(TEXT("swordUppercut")).Strength+MasteryEffect(TEXT("whirlwind")).Strength)*AttributeScale;Raw.Con-=MasteryEffect(TEXT("shotgunMastery")).Constitution*AttributeScale;Raw.Dex-=(DexterousHandsEffect().Dexterity+PistolEffect().Dexterity+MasteryEffect(TEXT("bowMastery")).Dexterity)*AttributeScale;Raw.Wis-=RifleEffect().Wisdom*AttributeScale;Raw.Luck-=CriticalStrikeEffect().Luck*AttributeScale;
    const auto Resources=CoreCombatFormula::Player(Raw,Level);
    const auto* Jingang=(Key==TEXT("def")||Key==TEXT("mdef")||Key==TEXT("aspd"))?UJingangRuneComponent::From(this):nullptr;
    const float JingangDefense=Jingang?Jingang->DefenseMultiplier():1.f;
    if (Key == TEXT("atk")) return AdjustCombatStat(Key,S.Atk+CoreCombatFormula::Round(EquipmentBonus(Key)));
    if (Key == TEXT("def")) {float Equipment=0;if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())for(const auto& Item:Current.Items)if(Item.Place==1&&(ColdSteelInventory::Text(Item,TEXT("weaponType"))!=TEXT("shield")||Item.Cell==(Current.ActiveWeaponSlot==6?8:11)))Equipment+=E->Defense(Item);double Value=S.Def+Equipment;if(const auto* I=Equipped())if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())Value=std::floor(Value*(1+E->CraftEffect(*I,TEXT("defensePercent"))));return AdjustCombatStat(Key,Value)*JingangDefense;}
    if (Key == TEXT("matk")) return AdjustCombatStat(Key,S.Matk+CoreCombatFormula::Round(EquipmentBonus(Key))+EquipmentMagicAttack());
    if (Key == TEXT("mdef")) return AdjustCombatStat(Key,S.Mdef)*JingangDefense;
    if (Key == TEXT("critRes")) return S.CritRes;
    if (Key == TEXT("crit")) return AdjustCombatStat(Key,S.Crit+CoreCombatFormula::Round(EquipmentBonus(Key)))+ColdSteelMelee::EquippedModifiers(this).CriticalChanceAdd;
    if (Key == TEXT("speed")) return std::floor(S.Speed*CombatMoveMultiplier());
    if (Key == TEXT("mpRegen")) return Resources.MpRegen*TributeEffect(TEXT("mpRegenPercent"))*(1+DungeonEffect(TEXT("mpRegenPercent"))/100.);
    if (Key == TEXT("aspd")) return S.AttackSpeed*(1.+EquipmentBonus(TEXT("meleeAttackSpeed")))*BerserkAttackSpeedMultiplier()*(Jingang?Jingang->AttackSpeedMultiplier():1.f);
    if (Key == TEXT("staminaRegen")) return Resources.StaminaRegen*SetEffect(Key)*TributeEffect(TEXT("staminaRegenPercent"))*(1+DungeonEffect(TEXT("staminaRegenPercent"))/100.);
    return 0;
}
