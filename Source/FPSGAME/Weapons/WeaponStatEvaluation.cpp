#include "WeaponStatEvaluation.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../FPSGAMECharacter.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/UnrealType.h"

double ColdSteelWeaponStats::Damage(const FColdSteelItem& Item,const UColdSteelStatusModel* Model,double Base)
{
    if(!Model)return Base;
    const float Attack=Model->Derived(TEXT("atk"));
    const auto* Enhancement=Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
    return Enhancement?Enhancement->ProcessedDamage(Item,Base,Attack):Base+Attack;
}
double ColdSteelWeaponStats::Interval(const FColdSteelItem* Item,const UColdSteelStatusModel* Model,double Base)
{
    if(!Model)return Base;
    float Result=Base/FMath::Max(1.f,Model->Derived(TEXT("aspd")));
    if(Item)if(const auto* Enhancement=Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        Result*=Enhancement->Effect(*Item,TEXT("attackIntervalMul"),1);
    if(Item&&Model->WeaponMastery(Item)==TEXT("bowMastery"))Result*=1-Model->MasteryEffect(TEXT("bowMastery")).CooldownReduction;
    return Result;
}
double ColdSteelWeaponStats::Reload(const UColdSteelStatusModel* Model,double Base)
{return Model?Base/Model->ReloadSpeedMultiplier():Base;}
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
