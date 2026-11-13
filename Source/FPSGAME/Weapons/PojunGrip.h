#pragma once
#include "../UI/ColdSteelInventoryTypes.h"
#include "../UI/ColdSteelItemReadCache.h"

struct FMeleeModifiers;
class UColdSteelStatusModel;

namespace PojunGrip
{
    inline constexpr const TCHAR* Weapon=TEXT("ue_zhanmadao");
    inline constexpr const TCHAR* Part=TEXT("pojun_longhaft");
    inline constexpr const TCHAR* SwordAttackLayer=TEXT("/Game/Audio/SwordAttack20260914/S_Sword_Attack.S_Sword_Attack");
    inline constexpr const TCHAR* SwordHit=TEXT("/Game/Weapons/AzureRunesword20260913/Sword_Hit.Sword_Hit");
    inline bool Installed(const FColdSteelItem& Item)
    {
        if(Item.Definition!=Weapon)return false;
        const auto Data=ColdSteelItemData::Read(Item.Data);
        const TSharedPtr<FJsonObject>* Parts=nullptr;
        FString Grip;
        return Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts)&&
            (*Parts)->TryGetStringField(TEXT("grip"),Grip)&&Grip==Part;
    }
    inline bool UsesHammerMotion(const FColdSteelItem& Item)
    {
        return Installed(Item)||ColdSteelInventory::IsTwoHandedBlunt(Item);
    }
    enum class EAttack : uint8 { Ordinary, Tengyun, Chixiao, Zhufeng };
    bool CanSprintAttack(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile);
    EAttack Attack(const FColdSteelItem& Item,bool Heavy,bool Sprint,int32 Stage);
    const FMeleeModifiers* Modifiers(const FColdSteelItem* Item,const UColdSteelStatusModel* Profile,
        const TMap<FString,FString>* Preview=nullptr);
    const FColdSteelItem* ChainSlashWeapon(const UColdSteelStatusModel* Profile);
}
