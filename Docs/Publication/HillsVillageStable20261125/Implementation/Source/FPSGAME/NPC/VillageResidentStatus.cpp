#include "VillageResidentStatus.h"
#include "ChapelNun.h"
#include "VillageArtisanMerchant.h"
#include "VillageBaker.h"
#include "VillageHerbalist.h"
#include "VillageMillKeeper.h"
#include "VillageTavernKeeper.h"
#include "../WorldGeneration/VillageGunshopServices.h"
#include "../Movement/StableRidingHorse.h"
#include "../Movement/StableHorseMarket.h"
#include "../Characters/VillageArtisanVitalsComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterHitFeedback.h"

const TCHAR* VillageResidentStatus::Name(const AActor* Actor)
{
    if(!IsValid(Actor))return nullptr;
    if(const auto* Horse=Cast<AStableRidingHorse>(Actor))return Horse->HorseName();
    if(StableHorseMarket::IsSeller(Actor))return TEXT("马厩管理员");
    if(const auto* Artisan=Cast<AVillageArtisanMerchant>(Actor))return Artisan->MerchantName();
    if(Actor->IsA<AVillageBaker>())return TEXT("面包师");
    if(Actor->IsA<AVillageMillKeeper>())return TEXT("磨坊管理员");
    if(Actor->IsA<AVillageHerbalist>())return TEXT("草药师林芷");
    if(Actor->IsA<AVillageTavernKeeper>())return TEXT("酒馆老板娘");
    if(Actor->IsA<AChapelNun>())return TEXT("修女");
    if(Actor->IsA<AVillageGunshopCounter>())return TEXT("枪匠");
    return nullptr;
}
void VillageResidentStatus::Read(AActor& Actor,FMonsterHitFeedback& Out)
{
    const TCHAR* Label=Name(&Actor);
    if(!Label)return;
    Out.Target=&Actor;Out.Name=FText::FromString(Label);Out.Opacity=1.f;
    const TCHAR* Activity=TEXT("可交谈");
    if(const auto* Horse=Cast<AStableRidingHorse>(&Actor))
    {
        Out.Health=Horse->GetHealth();Out.MaxHealth=Horse->GetMaximumHealth();
        Activity=Horse->IsRetreating()?TEXT("受惊逃离"):Horse->GetRider()?TEXT("骑乘中"):
            Horse->GetLeader()?TEXT("随行"):TEXT("待命");
    }
    else if(const auto* Vitals=Actor.FindComponentByClass<UVillageArtisanVitalsComponent>())
    {
        Out.Health=Vitals->GetHealth();Out.MaxHealth=Vitals->MaxHealth();
        const auto* Artisan=Cast<AVillageArtisanMerchant>(&Actor);
        Activity=Vitals->IsDowned()?TEXT("等待急救"):Artisan&&Artisan->IsDefending()?TEXT("戒备"):TEXT("工作中");
    }
    else if(const auto* Health=Actor.FindComponentByClass<UFPSCombatHealthComponent>())
    {
        Out.Health=Health->Health;Out.MaxHealth=Health->MaxHealth;
    }
    else if(Actor.IsA<AVillageGunshopCounter>())Activity=TEXT("营业中");
    Out.FriendlyActivity=FText::FromString(Activity);
}
