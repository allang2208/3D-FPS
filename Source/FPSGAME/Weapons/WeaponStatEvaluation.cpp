#include "WeaponStatEvaluation.h"
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
    const float Attack=Model?Model->Derived(TEXT("atk")):0;
    const auto* Enhancement=Model?Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;
    return ColdSteelWeaponDamage::Evaluate(Item,Model,Enhancement?Enhancement->ProcessedDamage(Item,Base,Attack):Base+Attack);
}
double ColdSteelWeaponStats::Interval(const FColdSteelItem* Item,const UColdSteelStatusModel* Model,double Base)
{
    if(!Model)return Base;
    // Firearms are catalog-tuned: the character's attack rate no longer shortens
    // the fire interval (2026-09-17). Melee keeps its own dex-based attack rate.
    // Only item and skill sources still modify the interval here.
    float Result=Base;
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
    const double Dex=double(Model->Attribute(TEXT("dex")))+Model->EquipmentBonus(TEXT("dex"));
    double Speed=1.+FMath::Max(0.,Dex)*DexReloadSpeedPerPoint;
    Speed*=FMath::Max(0.05,Model->ReloadSpeedMultiplier());
    if(Item)if(const auto* Enhancement=Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
    {
        Speed*=FMath::Max(0.05,Enhancement->Effect(*Item,TEXT("reloadSpeedPercent"),1));
        Speed*=FMath::Max(0.05,Enhancement->CraftEffect(*Item,TEXT("reloadSpeedPercent"),1));
    }
    return Base/FMath::Max(0.05,Speed);
}
FString ColdSteelWeaponStats::AmmoName(const FString& Definition)
{
    static const TMap<FString,FString> Names={{TEXT("ammo_556"),TEXT("5.56 mm")},{TEXT("ammo_762"),TEXT("7.62 mm")},
        {TEXT("ammo_58"),TEXT("5.8 mm")},{TEXT("ammo_9mm"),TEXT("9 mm")},{TEXT("ammo_45acp"),TEXT(".45 ACP")},
        {TEXT("ammo_357"),TEXT(".357 MAG")}};
    const auto* Name=Names.Find(Definition);
    return Name?*Name:Definition.IsEmpty()?FString():TEXT("未知口径");
}
double ColdSteelWeaponStats::NativeM4Base(const UColdSteelStatusModel* Model,const TCHAR* Property)
{
    const auto* Pawn=Model?Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(Model,0)):nullptr;
    const auto* Defaults=Pawn?Pawn->GetClass()->GetDefaultObject<AFPSGAMECharacter>():GetDefault<AFPSGAMECharacter>();
    const auto* Field=FindFProperty<FFloatProperty>(Defaults->GetClass(),Property);
    return Field?Field->GetPropertyValue_InContainer(Defaults):0;
}
