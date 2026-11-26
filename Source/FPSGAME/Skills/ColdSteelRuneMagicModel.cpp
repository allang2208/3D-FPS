#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"

void UColdSteelStatusModel::NotifyMagicReleased()
{
    auto* Pawn=RuntimePawn();
    const auto* Item=Equipped();
    if(!Pawn||!Pawn->HasAuthority()||ActiveProductionTool()||!Item||Item->Definition!=TEXT("ue_rune_sword"))return;
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Health&&Health->IsDead())return;
    const auto* Gunsmith=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    if(!Gunsmith||Gunsmith->Installed(*Item).FindRef(TEXT("blade_2"))!=TEXT("silver_glow_rune"))return;
    UCombatStatusFormula::GetOrAdd(Pawn)->GrantMagicInspiration();
    OnChanged.Broadcast();
}
float UColdSteelStatusModel::MagicInspirationAttackSpeedMultiplier() const
{
    const auto* Pawn=RuntimePawn();
    const auto* Status=Pawn?Pawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
    return Status?Status->MagicInspirationAttackSpeed():1.f;
}
