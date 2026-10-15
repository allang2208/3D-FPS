#include "WarhammerCombat.h"
#include "ProductionBluntCombo.h"
#include "WarhammerHeavyMotion.h"
#include "../Weapons/GunsmithSystem.h"
#include "Engine/GameInstance.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/MonsterCoreStats.h"
#include "../Combat/CombatStatusFormula.h"

float WarhammerCombat::ShockwaveRadius(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile)
{
    const float Base=float(ColdSteelInventory::Number(Item,TEXT("heavy_wave_radius_cm"),WarhammerHeavy::Radius));
    if(Item.Definition!=TEXT("ue_steel_warhammer")||!Profile)return Base;
    const auto* GI=Profile->GetGameInstance();
    const auto* Gunsmith=GI?GI->GetSubsystem<UGunsmithSystem>():nullptr;
    const auto* Weapon=Gunsmith?Gunsmith->ModifiableWeapon(Item.Definition):nullptr;
    if(!Weapon||!Weapon->Source)return Base;
    const FString Head=Gunsmith->Installed(Item).FindRef(TEXT("hammer_heads"));
    if(Head.IsEmpty())return Base;
    // Read the already-loaded exclusive catalogue once when committing tool stats.
    // This modifier is specific to ground waves, independent of ordinary melee reach.
    for(const auto& Entry:Weapon->Source->GetArrayField(TEXT("columns")))
    {
        const auto Column=Entry->AsObject();
        if(Column->GetStringField(TEXT("key"))!=TEXT("hammer_heads"))continue;
        for(const auto& Value:Column->GetArrayField(TEXT("options")))
        {
            const auto Option=Value->AsObject();
            if(Option->GetStringField(TEXT("id"))!=Head)continue;
            double Multiplier=1.;const TSharedPtr<FJsonObject>* Stats=nullptr;
            if(Option->TryGetObjectField(TEXT("stats"),Stats))
                (*Stats)->TryGetNumberField(TEXT("shockwave_radius_mult"),Multiplier);
            return Base*float(Multiplier);
        }
    }
    return Base;
}

FWeaponDamageParts WarhammerCombat::Damage(const FWeaponDamageParts& Base,const UColdSteelStatusModel* Profile,
    bool bSprint,bool bHeavy,float HeavyMultiplier,int32 Stage)
{
    if(bSprint&&Profile)
    {
        // Same skill multiplier and integer total as the sword dash. Preserve
        // the hammer's physical/magic/additional split; never multiply by heavy again.
        const double Total=Base.Total();
        const double Amount=FMath::FloorToFloat(Total*Profile->DashAttackStats().DamageMultiplier);
        return Base.Scaled(Total>0.?Amount/Total:0.);
    }
    return Base.Scaled(bHeavy?HeavyMultiplier:ProductionBluntCombo::DamageMultiplier(Stage));
}

void WarhammerCombat::ApplyHeavyStun(AActor* Target,float Seconds)
{
    if(!IsValid(Target)||!Target->HasAuthority()||Seconds<=0.f)return;
    auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
    if(!Combat||Combat->IsDead())return;
    FMonsterCoreStats Stats;
    const bool bOrdinary=MonsterCoreStats::Get(Target,Stats)
        &&(Stats.Rank==EMonsterRank::Normal||Stats.Rank==EMonsterRank::Minor);
    // Called after damage, so this very impact can open the broken window.
    if(!bOrdinary&&!Combat->IsToughnessBroken())return;
    if(auto* Status=UCombatStatusFormula::GetOrAdd(Target))Status->AddStun(Seconds);
}
