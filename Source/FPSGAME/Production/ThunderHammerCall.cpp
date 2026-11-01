#include "ThunderHammerCall.h"
#include "ThunderHammerTuning.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Skills/BlizzardEnvironment.h"
#include "Engine/World.h"

float ThunderHammer::LightningMagic(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile)
{
    if(!Profile)return 0.f;
    const auto Modifiers=ColdSteelMelee::Evaluate(Item,Profile).Modifiers;
    return float(FMath::Max(0.,Profile->Derived(TEXT("matk")))*MagicAttackScale*
        FMath::Max(0.,(1.+Profile->SetEffect(TEXT("magicDamage")))*Modifiers.MagicDamage)*Modifiers.AllAttackDamage);
}

bool ThunderHammerCall::Installed(const FColdSteelItem& Item)
{
    if(Item.Definition!=ThunderHammer::Definition)return false;
    const auto Data=ColdSteelItemData::Read(Item.Data);const TSharedPtr<FJsonObject>* Parts=nullptr;FString Id;
    return Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts)&&(*Parts)->TryGetStringField(TEXT("head_mount"),Id)&&Id==Seat;
}

bool ThunderHammerCall::SelectGround(const APawn* Pawn,FHitResult& Hit)
{
    if(!Pawn||!Pawn->GetWorld())return false;
    const auto* Character=Cast<AFPSGAMECharacter>(Pawn);
    const FTransform Aim=Character?Character->GetMeleeAimTransform():FTransform(Pawn->GetViewRotation(),Pawn->GetPawnViewLocation());
    FVector Point,Normal,Axis=FVector::RightVector;FString Failure;
    if(!BlizzardEnvironment::Select(const_cast<APawn*>(Pawn),RangeCM,Aim.GetLocation(),Aim.GetUnitAxis(EAxis::X),Point,Normal,Axis,Failure))return false;
    Hit=FHitResult{};Hit.bBlockingHit=true;Hit.Location=Hit.ImpactPoint=Point;Hit.Normal=Hit.ImpactNormal=Normal;
    return true;
}
