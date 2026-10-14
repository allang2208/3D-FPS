#include "RuneSwordComponent.h"
#include "RuneSwordGuardTuning.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Movement/PlayerGuardBreakComponent.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"

bool URuneSwordComponent::CanMaintainNetworkGuard() const
{
    const auto* Pawn=Character.Get();const auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Model?Model->Equipped():nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Break=Pawn?Pawn->FindComponentByClass<UPlayerGuardBreakComponent>():nullptr;
    return Pawn&&Item&&Item->InstanceId==InstanceId&&ColdSteelInventory::IsTwoHandedSword(*Item)
        &&!Model->ActiveProductionTool()&&Health&&!Health->IsDead()&&!(Break&&Break->IsActive())
        &&!UBoundCongregateCaptureComponent::IsCaptured(Pawn)&&!Pawn->IsTraversing()
        &&!Pawn->IsDodging()&&!Pawn->IsSliding()&&!Pawn->IsCastBlockingLeftHandAction()&&CanUse();
}

void URuneSwordComponent::SendGuardIntent(bool Raised)
{
    const auto* Pawn=Character.Get();
    if(Pawn&&Pawn->IsLocallyControlled()&&!Pawn->HasAuthority())ServerSetSwordGuard(InstanceId,Raised);
}

void URuneSwordComponent::ServerSetSwordGuard_Implementation(const FString& Weapon,bool Raised)
{
    auto* Pawn=Character.Get();if(!Pawn||!Pawn->HasAuthority()||Pawn->IsLocallyControlled())return;
    if(Weapon!=InstanceId){if(Raised)ClientSwordGuardResult(Weapon,3,0.f,GetWorld()->GetTimeSeconds());return;}
    auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    if(!Raised)
    {
        bGuardHeld=bGuarding=false;if(Model)Model->DelayStaminaRecovery();return;
    }
    if(!CanMaintainNetworkGuard()||!Model||Model->Stamina()<=0.f)
    {bGuardHeld=bGuarding=false;ClientSwordGuardResult(Weapon,3,0.f,GetWorld()->GetTimeSeconds());return;}
    if(!bGuarding)GuardStartedAt=GetWorld()->GetTimeSeconds();
    bGuardHeld=bGuarding=true;Model->DelayStaminaRecovery();
}

void URuneSwordComponent::TickNetworkGuard()
{
    if(GetOwner()->HasAuthority()&&bGuarding&&!CanMaintainNetworkGuard())
    {bGuardHeld=bGuarding=false;ClientSwordGuardResult(InstanceId,3,0.f,GetWorld()->GetTimeSeconds());}
}

void URuneSwordComponent::PresentGuardBreak()
{
    if(!Character.IsValid()||!Character->IsLocallyControlled()||!IsEquipped())return;
    bGuarding=bGuardHeld=bGuardReacting=bReturningGuard=false;
    bGuardBreakPose=true;GuardFeedbackAt=GetWorld()->GetTimeSeconds();GuardFeedbackStrength=1.8f;
    SetClip(Animations.FindRef(TEXT("GuardBreak"))?TEXT("GuardBreak"):TEXT("Idle"),false);
}

void URuneSwordComponent::ClientSwordGuardResult_Implementation(const FString& Weapon,uint8 Outcome,float StaminaSpent,double ServerAt)
{
    auto* Pawn=Character.Get();if(!Pawn||!Pawn->IsLocallyControlled()||Pawn->HasAuthority())return;
    // The accepted block still spent stamina if equipment changed before this receipt.
    if(auto* Model=ColdSteelAuthority::ForPawn(Pawn);Model&&StaminaSpent>0.f)Model->SpendStamina(FMath::Min(Model->Stamina(),StaminaSpent));
    if(Weapon!=InstanceId)return;
    if(Outcome==3){ReleaseGuard();return;}
    if(Outcome==2){PresentGuardBreak();return;}
    GuardFeedback(Outcome==1);
    if(Outcome!=1)return;
    const auto* GS=GetWorld()->GetGameState();
    const double Age=FMath::Max(0.,(GS?GS->GetServerWorldTimeSeconds():ServerAt)-ServerAt);
    if(MeleeModifiers.ClovenSeconds>Age)
    {
        ClovenGrantedAt=GetWorld()->GetTimeSeconds()-Age;
        ClovenReadyUntil=ClovenGrantedAt+MeleeModifiers.ClovenSeconds;
    }
    if(MeleeModifiers.RiposteSeconds>Age)
        UCombatStatusFormula::GetOrAdd(Pawn)->GrantRiposteGuard(MeleeModifiers.RiposteSeconds-Age,MeleeModifiers.RiposteSpeed,MeleeModifiers.RiposteStamina);
}

bool URuneSwordComponent::ClaimNetworkClovenAttack(uint32 Serial)
{
    auto* Pawn=Character.Get();auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Model?Model->Equipped():nullptr;
    if(!Pawn||!Pawn->HasAuthority()||!Serial||!Item||Item->InstanceId!=InstanceId
        ||Item->Definition!=TEXT("ue_highland_claymore")||Model->ActiveProductionTool())return false;
    const double Now=GetWorld()->GetTimeSeconds();
    if(Serial==ConsumedClovenSerial)return ClovenAttackWeapon==InstanceId&&Now<ClovenAttackUntil;
    if(static_cast<int32>(Serial-ConsumedClovenSerial)<=0||Now>=ClovenReadyUntil)return false;
    const auto Mods=ColdSteelMelee::EquippedModifiers(Model);
    if(Mods.ClovenSeconds<=0)return false;
    ConsumedClovenSerial=Serial;ClovenAttackWeapon=InstanceId;ClovenReadyUntil=0.;
    ClovenAttackUntil=Now+2.;ClovenAttackPhysical=Mods.ClovenPhysical;ClovenAttackToughness=Mods.ClovenToughness;
    return true;
}

void URuneSwordComponent::ServerBeginClovenAttack_Implementation(const FString& Weapon,uint32 Serial)
{
    if(Weapon==InstanceId)ClaimNetworkClovenAttack(Serial);
}

bool URuneSwordComponent::ApplyNetworkClovenAttack(FColdSteelSkillShot& Shot)
{
    if(Shot.GuardSourceInstance!=InstanceId||!ClaimNetworkClovenAttack(Shot.GuardAttackSerial))return false;
    Shot.DamagePanel.BasePhysical*=ClovenAttackPhysical;Shot.DamagePanel.AddedPhysical*=ClovenAttackPhysical;
    Shot.ToughnessDamageMultiplier*=ClovenAttackToughness;return true;
}
