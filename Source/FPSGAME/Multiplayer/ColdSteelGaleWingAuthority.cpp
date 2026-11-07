#include "ColdSteelPlayerState.h"
#include "UppercutStaminaReceipt.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Movement/FPSExhaustionComponent.h"
#include "Engine/GameInstance.h"

void AColdSteelPlayerState::ServerPayGaleSwing_Implementation(APawn* ActionPawn,const FString& Weapon,
    uint32 Serial,bool Dash)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    if(!Serial || !Pawn || Pawn!=ActionPawn || !ShadowModel || ShadowModel->ActiveProductionTool())return;
    if(GaleSwingPawn.Get()!=Pawn){GaleSwingPawn=Pawn;LastGaleSwingSerial=0;}
    if(int32(Serial-LastGaleSwingSerial)<=0)return;

    const auto* Item=ShadowModel->Equipped();
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!Sword || !Sword->HasGaleGuard(Item) || Item->InstanceId!=Weapon || !Health || Health->IsDead())return;
    if(Dash && ShadowModel->MasteryProgress(TEXT("dashAttack")).Level<1)return;

    const double Cost=Dash?ShadowModel->DashAttackStats().StaminaCost:ColdSteelMelee::AttackStamina(Item,ShadowModel);
    const float Before=ShadowModel->Stamina();
    if(!ShadowModel->SpendStamina(Cost))return;
    LastGaleSwingSerial=Serial;
    const float Paid=Before-ShadowModel->Stamina();
    const auto Key=GaleWing::Key(Dash?GaleWing::EAttack::Dash:GaleWing::EAttack::Swing,Serial);
    Sword->RecordGalePayment(Key,Weapon,Paid);
    ShadowModel->Current.UppercutStaminaSpent+=Paid;
    bServerDirty=true;
    ClientGaleSwingCost(ShadowModel->Current.UppercutStaminaSpent);
}

void AColdSteelPlayerState::ClientGaleSwingCost_Implementation(double TotalSpent)
{
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model || TotalSpent<=Model->Current.UppercutStaminaSpent)return;
    auto* Exhaustion=GetPawn()?GetPawn()->FindComponentByClass<UFPSExhaustionComponent>():nullptr;
    if(Exhaustion)Exhaustion->ObserveStamina(Model->Stamina());
    UppercutStaminaReceipt::Merge(Model->Current,TotalSpent);
    Model->DelayStaminaRecovery();
    if(Exhaustion)Exhaustion->ObserveStamina(Model->Stamina());
}

void AColdSteelPlayerState::ClientGaleCredit_Implementation(double TotalSpent,double TotalCredit)
{
    ClientGaleSwingCost_Implementation(TotalSpent);
    if(auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Model->ApplyOathRefundReceipt(TotalCredit);
}
