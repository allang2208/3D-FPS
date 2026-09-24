#include "WeaponDamagePanel.h"
#include "GunsmithSystem.h"
#include "../Combat/CombatItemFormula.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Dom/JsonObject.h"

namespace
{
double Attribute(const UColdSteelStatusModel* Profile,FName Key)
{
    if(!Profile)return 0;
    if(Key==TEXT("int"))Key=TEXT("intt");
    if(Key==TEXT("atk")||Key==TEXT("matk"))return Profile->Derived(Key);
    return Profile->Attribute(Key);
}
double Additional(const TSharedPtr<const FJsonObject>& Root,const TCHAR* Type,const UColdSteelStatusModel* Profile,double Base)
{
    const TSharedPtr<FJsonObject>* All=nullptr;const TSharedPtr<FJsonObject>* Part=nullptr;
    if(!Root||!Root->TryGetObjectField(TEXT("additionalDamage"),All)||!(*All)->TryGetObjectField(Type,Part))return 0;
    double Flat=0,Ratio=0;(*Part)->TryGetNumberField(TEXT("flat"),Flat);(*Part)->TryGetNumberField(TEXT("baseRatio"),Ratio);
    double Result=Flat+Base*Ratio;
    const TSharedPtr<FJsonObject>* Attributes=nullptr;
    if((*Part)->TryGetObjectField(TEXT("attributes"),Attributes))for(const auto& Term:(*Attributes)->Values)
    {double Coefficient=0;if(Term.Value->TryGetNumber(Coefficient))Result+=Attribute(Profile,FName(*Term.Key))*Coefficient;}
    return FMath::Max(0.,Result);
}
}

FWeaponDamageParts ColdSteelWeaponDamage::Evaluate(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,double Base,const FMeleeModifiers* Melee)
{
    FWeaponDamageParts R;R.BasePhysical=FMath::Max(0.,Base);
    const auto Data=CombatItemFormula::ReadOnly(Item);
    R.AddedPhysical=Additional(Data,TEXT("physical"),Profile,R.Base());
    R.AddedMagic=Additional(Data,TEXT("magic"),Profile,R.Base());
    // This weapon-native contribution is independent of the selected rune.
    // Spirit burst doubles only innate erosion, not affixes or other additions.
    const double Innate=Attribute(Profile,TEXT("intt"))*ColdSteelInventory::Number(Item,TEXT("innate_erosion_intelligence"))
        +Attribute(Profile,TEXT("wis"))*ColdSteelInventory::Number(Item,TEXT("innate_erosion_wisdom"));
    R.AddedMagic+=Innate*(Melee?Melee->InnateErosionMultiplier:1.);
    if(Melee)R.AddedMagic+=Attribute(Profile,TEXT("intt"))*Melee->RuneIntelligence+Attribute(Profile,TEXT("wis"))*Melee->RuneWisdom;
    // Attacker-side magic bonuses are already included in the panel, before any
    // attack multiplier or target defense. Do not apply them again on contact.
    R.AddedMagic*=FMath::Max(0.,(1+(Profile?Profile->SetEffect(TEXT("magicDamage")):0))*(Melee?Melee->MagicDamage:1));
    return R;
}
