#include "../UI/ColdSteelStatusModel.h"
#include "ColdSteelSkillRules.h"
const FColdSteelSkillDefinition& UColdSteelStatusModel::MasteryDefinition(FName Id) const
{
    if(Id==TEXT("rifleMastery"))return RifleDefinition();if(Id==TEXT("pistolMastery"))return PistolDefinition();
    static const TMap<FName,FColdSteelSkillDefinition> AdditionalDefinitions=[] {
        TMap<FName,FColdSteelSkillDefinition> Out;for(FName Key:{FName(TEXT("swordMastery")),FName(TEXT("machineGunMastery")),FName(TEXT("shotgunMastery")),FName(TEXT("bowMastery")),FName(TEXT("heavyStrike")),FName(TEXT("whirlwind"))})Out.Add(Key,ColdSteelSkills::LoadDefinition(Key));return Out;}();
    if(const auto* D=AdditionalDefinitions.Find(Id))return *D;return RifleDefinition();
}
FColdSteelSkillProgress UColdSteelStatusModel::MasteryProgress(FName Id)const
{if(const auto* P=Current.Skills.Find(Id))return *P;FColdSteelSkillProgress Empty;Empty.Level=0;return Empty;}
FColdSteelSkillEffect UColdSteelStatusModel::MasteryEffect(FName Id,int32 L)const
{return ColdSteelSkills::Effect(MasteryDefinition(Id),L<0?MasteryProgress(Id).Level:L);}
FName UColdSteelStatusModel::WeaponMastery(const FColdSteelItem* Item)const
{
    if(!Item)return NAME_None;const FString Type=ColdSteelInventory::Text(*Item,TEXT("weaponType"));
    if(Type==TEXT("rifle"))return TEXT("rifleMastery");if(Type==TEXT("pistol"))return TEXT("pistolMastery");
    if(Type==TEXT("sword")||Item->Definition==TEXT("ue_rune_sword"))return TEXT("swordMastery");
    if(Type==TEXT("machineGun")||Type==TEXT("machinegun")||Type==TEXT("lmg"))return TEXT("machineGunMastery");
    if(Type==TEXT("shotgun"))return TEXT("shotgunMastery");if(Type==TEXT("bow"))return TEXT("bowMastery");return NAME_None;
}
float UColdSteelStatusModel::AdditionalWeaponDamage(const FColdSteelItem& Item,float Damage)const
{
    // Production tools share the formula/defense pipeline, not weapon mastery bonuses.
    if(ColdSteelInventory::Text(Item,TEXT("category"))==TEXT("tool"))return Damage;
    // Source computeWeaponAttack adds sword mastery before category-specific mastery.
    Damage+=MasteryEffect(TEXT("swordMastery")).FlatDamage;
    const FName Id=WeaponMastery(&Item);
    if(Id==TEXT("rifleMastery"))return RifleWeaponDamage(Item,Damage);
    if(Id==TEXT("pistolMastery"))return PistolWeaponDamage(Item,Damage);
    if(Id==TEXT("machineGunMastery")||Id==TEXT("shotgunMastery")||Id==TEXT("bowMastery"))
    {const auto E=MasteryEffect(Id);return FMath::RoundToFloat(Damage*(1+E.DamagePercent)+E.FlatDamage);}
    return Damage;
}
