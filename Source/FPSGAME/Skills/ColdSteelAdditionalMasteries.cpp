#include "../UI/ColdSteelStatusModel.h"
#include "ColdSteelSkillTree.h"
#include "ColdSteelSkillRules.h"
#include "../Weapons/Bow/BowDamageTuning.h"
#include "../Weapons/WoodenTorchItem.h"
const FColdSteelSkillDefinition& UColdSteelStatusModel::MasteryDefinition(FName Id) const
{
    if(Id==TEXT("rifleMastery"))return RifleDefinition();if(Id==TEXT("pistolMastery"))return PistolDefinition();
    static const TMap<FName,FColdSteelSkillDefinition> AdditionalDefinitions=[] {
        TMap<FName,FColdSteelSkillDefinition> Out;for(FName Key:{FName(TEXT("twoHandedMastery")),FName(TEXT("oneHandedMastery")),FName(TEXT("swordMastery")),FName(TEXT("bluntMastery")),FName(TEXT("machineGunMastery")),FName(TEXT("shotgunMastery")),FName(TEXT("bowMastery")),FName(TEXT("heartPiercingArrow")),FName(TEXT("magicArrowRain")),FName(TEXT("elementalArrow")),FName(TEXT("illuminationArrow")),FName(TEXT("heavyStrike")),FName(TEXT("whirlwind")),FName(TEXT("dashAttack")),FName(TEXT("swordUppercut")),FName(TEXT("leapStrike")),FName(TEXT("chainSlash")),FName(TEXT("shadowStepSlash"))})Out.Add(Key,ColdSteelSkills::LoadDefinition(Key));return Out;}();
    if(const auto* D=AdditionalDefinitions.Find(Id))return *D;return RifleDefinition();
}
FColdSteelSkillProgress UColdSteelStatusModel::MasteryProgress(FName Id)const
{
    // Skill tree (2026-11-15): an unlearned tree skill reads as Level 0, so every existing
    // MasteryProgress(...).Level<1 gate (client and server authority) also means "未习得".
    if(const auto* P=Current.Skills.Find(Id);P&&ColdSteelSkillTree::IsLearned(Current,Id))return *P;
    FColdSteelSkillProgress Empty;Empty.Level=0;return Empty;
}
FColdSteelSkillEffect UColdSteelStatusModel::MasteryEffect(FName Id,int32 L)const
{return ColdSteelSkills::Effect(MasteryDefinition(Id),L<0?MasteryProgress(Id).Level:L);}
FName UColdSteelStatusModel::WeaponMastery(const FColdSteelItem* Item)const
{
    if(!Item)return NAME_None;const FString Type=ColdSteelInventory::Text(*Item,TEXT("weaponType"));
    if(Type==TEXT("rifle")||Type==TEXT("sniper"))return TEXT("rifleMastery");if(Type==TEXT("pistol"))return TEXT("pistolMastery");
    if(ColdSteelInventory::IsTwoHandedSword(*Item))return TEXT("swordMastery");
    if(ColdSteelInventory::IsOneHandedMelee(*Item)&&!ColdSteelInventory::IsWoodenTorch(*Item))return TEXT("oneHandedMastery");
    if(Type==TEXT("blunt")&&ColdSteelInventory::Text(*Item,TEXT("category"))==TEXT("weapon_melee"))return TEXT("bluntMastery");
    if(Type==TEXT("machineGun")||Type==TEXT("machinegun")||Type==TEXT("lmg"))return TEXT("machineGunMastery");
    if(Type==TEXT("shotgun"))return TEXT("shotgunMastery");if(Type==TEXT("bow"))return TEXT("bowMastery");return NAME_None;
}
float UColdSteelStatusModel::AdditionalWeaponDamage(const FColdSteelItem& Item,float Damage)const
{
    // Production tools share the formula/defense pipeline, not weapon mastery bonuses.
    if(ColdSteelInventory::Text(Item,TEXT("category"))==TEXT("tool"))return Damage;
    const double FlatScale=ColdSteelBow::DamageCoefficientScale(Item);
    const FName Id=WeaponMastery(&Item);
    if(ColdSteelSkills::IsMeleeMastery(Id))
    {
        const auto E=MasteryEffect(Id);
        // Two-handed swords and blunt weapons stack their sub-mastery with twoHandedMastery.
        const auto Root=ColdSteelSkills::IsTwoHandedSubMastery(Id)?MasteryEffect(TEXT("twoHandedMastery")):FColdSteelSkillEffect{};
        return Damage*(1.f+E.DamagePercent+Root.DamagePercent)+E.FlatDamage+Root.FlatDamage;
    }
    if(Id==TEXT("rifleMastery"))return RifleWeaponDamage(Item,Damage);
    if(Id==TEXT("pistolMastery"))return PistolWeaponDamage(Item,Damage);
    if(Id==TEXT("machineGunMastery")||Id==TEXT("shotgunMastery")||Id==TEXT("bowMastery"))
    {const auto E=MasteryEffect(Id);return FMath::RoundToFloat(Damage*(1+E.DamagePercent)+E.FlatDamage*FlatScale);}
    return Damage;
}

float UColdSteelStatusModel::MeleeMasteryIntervalMultiplier(const FColdSteelItem& Item) const
{
    const FName Id=WeaponMastery(&Item);
    if(!ColdSteelSkills::IsMeleeMastery(Id))return 1.f;
    float Reduction=MasteryEffect(Id).CooldownReduction;
    if(ColdSteelSkills::IsTwoHandedSubMastery(Id))Reduction+=MasteryEffect(TEXT("twoHandedMastery")).CooldownReduction;
    return FMath::Max(.05f,1.f-Reduction);
}
