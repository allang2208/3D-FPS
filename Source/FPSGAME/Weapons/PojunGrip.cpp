#include "PojunGrip.h"
#include "GunsmithSystem.h"
#include "ModularSwordVisual.h"
#include "MeleeRuneVisual.h"
#include "FrostSwordRunes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"

PojunGrip::EAttack PojunGrip::Attack(const FColdSteelItem& Item,bool Heavy,bool Sprint,int32 Stage)
{
    if(!Installed(Item))return EAttack::Ordinary;
    if(Sprint)return ColdSteelMeleeRune::Selected(Item)==ColdSteelFrostRunes::Zhufeng?EAttack::Zhufeng:EAttack::Ordinary;
    if(Heavy)return ColdSteelMeleeRune::Selected(Item)==ColdSteelFrostRunes::Chixiao?EAttack::Chixiao:EAttack::Ordinary;
    return Stage==2&&ColdSteelModularSword::UsesRisingDragonFinisher(Item)?EAttack::Tengyun:EAttack::Ordinary;
}

bool PojunGrip::CanSprintAttack(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile)
{
    return Attack(Item,false,true,2)!=EAttack::Zhufeng||(Profile&&Profile->MasteryProgress(TEXT("dashAttack")).Level>0);
}

const FColdSteelItem* PojunGrip::ChainSlashWeapon(const UColdSteelStatusModel* Profile)
{
    if(!Profile)return nullptr;
    if(const auto* Tool=Profile->ActiveProductionTool())return Installed(*Tool)?Tool:nullptr;
    const auto* Sword=Profile->Equipped();
    return Sword&&ColdSteelInventory::IsTwoHandedSword(*Sword)?Sword:nullptr;
}

const FMeleeModifiers* PojunGrip::Modifiers(const FColdSteelItem* Item,const UColdSteelStatusModel* Profile,
    const FGunsmithParts* Preview)
{
    if(!Item||Item->Definition!=Weapon||!Profile)return nullptr;
    if(Preview?Preview->FindRef(TEXT("grip"))!=Part:!Installed(*Item))return nullptr;
    const auto* GI=Profile->GetGameInstance();
    const auto* Catalog=GI?GI->GetSubsystem<UGunsmithSystem>():nullptr;
    const auto* Grip=Catalog?Catalog->Option(Weapon,TEXT("grip"),Part):nullptr;
    return Grip?&Grip->Melee:nullptr;
}
