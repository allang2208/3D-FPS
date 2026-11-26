#include "SwiftFalconHeavy.h"
#include "../../Combat/WeaponDamageTypes.h"
#include "../GunsmithSystem.h"
#include "../MeleeWeaponStats.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"

void SwiftFalconHeavy::ScalePhysicalDamage(FWeaponDamageParts& Panel)
{
    constexpr double PhysicalScale = 0.90;
    Panel.BasePhysical *= PhysicalScale;
    Panel.AddedPhysical *= PhysicalScale;
}

bool SwiftFalconHeavy::Eligible(const FColdSteelItem* Main,const UColdSteelStatusModel* Profile,bool Both)
{
    if(!Main||Main->Definition!=TEXT("ue_tactical_hatchet")||!Profile||!Profile->GetGameInstance())return false;
    const auto* G=Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    if(!G||G->Installed(*Main).FindRef(TEXT("blade_1"))!=TEXT("hatchet_falcon_edge"))return false;
    const auto* Active=Profile->Equipped();
    if(Active&&Active->InstanceId!=Main->InstanceId)return false;
    if(!Active)return !Both;
    const auto* First=Profile->Equipped(6);
    const auto* Other=Profile->Equipped(First&&First->InstanceId==Main->InstanceId?8:11);
    if(!Other)return !Both;
    return Both&&Other->Definition==TEXT("ue_tactical_hatchet")&&G->Installed(*Other).FindRef(TEXT("blade_1"))==TEXT("hatchet_falcon_edge");
}

float SwiftFalconHeavy::ReleaseRate(const FColdSteelItem& Main,const FColdSteelItem* Off,const UColdSteelStatusModel* Profile)
{
    const double MainRate=ColdSteelMelee::Evaluate(Main,Profile).AttackSpeedMultiplier(Main);
    const double Rate=Off?.5*(MainRate+ColdSteelMelee::Evaluate(*Off,Profile).AttackSpeedMultiplier(*Off)):MainRate;
    return FMath::Max(.05f,float(Rate));
}
