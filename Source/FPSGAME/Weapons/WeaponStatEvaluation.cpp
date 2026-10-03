#include "WeaponStatEvaluation.h"
#include "WeaponDamagePanel.h"
#include "Bow/BowDamageTuning.h"
#include "GunsmithSystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../FPSGAMECharacter.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/UnrealType.h"

double ColdSteelWeaponStats::Damage(const FColdSteelItem& Item,const UColdSteelStatusModel* Model,double Base)
{return DamageParts(Item,Model,Base).Total();}

FWeaponDamageParts ColdSteelWeaponStats::DamageParts(const FColdSteelItem& Item,const UColdSteelStatusModel* Model,double Base)
{
    if(Model&&ColdSteelInventory::IsBow(Item))
        if(const auto* G=Model->GetGameInstance()->GetSubsystem<UGunsmithSystem>())Base*=G->Calculate(Item.Definition,G->Installed(Item)).Bow.Damage;
    const float Attack=Model?Model->Derived(TEXT("atk")):0;
    const auto* Enhancement=Model?Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;
    return ColdSteelWeaponDamage::Evaluate(Item,Model,Enhancement?Enhancement->ProcessedDamage(Item,Base,Attack):Base+Attack*ColdSteelBow::DamageCoefficientScale(Item));
}
double ColdSteelWeaponStats::BowDrawSpeedBonus(const FColdSteelItem* Item,const UColdSteelStatusModel* Model)
{
    if(!Item||!Model||!ColdSteelInventory::IsBow(*Item))return 0.;
    double Bonus=Model->EquipmentBonus(TEXT("bowDrawSpeed"));
    if(const auto* G=Model->GetGameInstance()->GetSubsystem<UGunsmithSystem>())
        Bonus+=G->Calculate(Item->Definition,G->Installed(*Item)).Bow.DrawSpeedBonus;
    if(const auto* Enhancement=Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        Bonus+=Enhancement->Effect(*Item,TEXT("bowDrawSpeedBonus"));
    return Bonus;
}
double ColdSteelWeaponStats::Interval(const FColdSteelItem* Item,const UColdSteelStatusModel* Model,double Base)
{
    if(!Model)return Base;
    // Firearms are catalog-tuned: the character's attack rate no longer shortens
    // the fire interval (2026-09-17). Melee keeps its own dex-based attack rate.
    // Only item and skill sources still modify the interval here.
    float Result=Base;
    if(Item&&ColdSteelInventory::IsBow(*Item))
    {
        // Modification, equipment and this bow's enchantment share one speed sum.
        // Nocking and arrow velocity keep their independent clocks.
        Result/=FMath::Max(0.05,1.+BowDrawSpeedBonus(Item,Model));
    }
    if(Item)if(const auto* Enhancement=Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        Result*=Enhancement->Effect(*Item,TEXT("attackIntervalMul"),1);
    if(Item&&Model->WeaponMastery(Item)==TEXT("bowMastery"))Result*=1-Model->MasteryEffect(TEXT("bowMastery")).CooldownReduction;
    return Result;
}
double ColdSteelWeaponStats::Reload(const FColdSteelItem* Item,const UColdSteelStatusModel* Model,double Base)
{
    if(!Model)return Base;
    // One multiplicative stack: 敏捷 × 快手 × 附魔 × 改造. Speed factors divide the
    // time, so every source stays independent instead of adding up into one bonus.
    const double Dex=Model->Attribute(TEXT("dex"))+Model->EquipmentBonus(TEXT("dex"))*Model->EffectiveAttributeMultiplier();
    double Speed=1.+FMath::Max(0.,Dex)*DexReloadSpeedPerPoint;
    Speed*=FMath::Max(0.05,Model->ReloadSpeedMultiplier());
    Speed*=FMath::Max(0.05,1.+Model->EquipmentBonus(TEXT("reloadSpeed")));
    if(Item)if(const auto* Enhancement=Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
    {
        Speed*=FMath::Max(0.05,Enhancement->Effect(*Item,TEXT("reloadSpeedPercent"),1));
        Speed*=FMath::Max(0.05,Enhancement->CraftEffect(*Item,TEXT("reloadSpeedPercent"),1));
    }
    return Base/FMath::Max(0.05,Speed);
}
FString ColdSteelWeaponStats::AmmoName(const FString& Definition)
{
    static const TMap<FString,FString> Names={{TEXT("ammo_556"),TEXT("5.56 mm")},{TEXT("ammo_762"),TEXT("7.62x39mm")},{TEXT("ammo_pkm_762x54r"),TEXT("7.62x54R mm")},
        {TEXT("ammo_58"),TEXT("5.8 mm")},{TEXT("ammo_9mm"),TEXT("9 mm")},{TEXT("ammo_45acp"),TEXT(".45 ACP")},
        {TEXT("ammo_357"),TEXT(".357 MAG")},{TEXT("ammo_127"),TEXT("12.7 mm")}};
    const auto* Name=Names.Find(Definition);
    return Name?*Name:Definition.IsEmpty()?FString():TEXT("未知口径");
}
