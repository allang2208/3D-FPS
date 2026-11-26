#include "RuneSwordComponent.h"
#include "../Weapons/PojunGrip.h"
#include "RuneSwordGuardTuning.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Production/ProductionToolComponent.h"
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
    const auto* Item=GuardItem(Model);
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Break=Pawn?Pawn->FindComponentByClass<UPlayerGuardBreakComponent>():nullptr;
    const auto* Tool=Pawn?Pawn->FindComponentByClass<UProductionToolComponent>():nullptr;
    const auto* PS=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    const bool MatchingKind=Item&&(ToolGuardInstance.IsEmpty()
        ?ColdSteelInventory::IsTwoHandedSword(*Item)&&!Model->ActiveProductionTool()
        :PojunGrip::UsesHammerMotion(*Item));
    return Pawn&&Item&&Item->InstanceId==GuardWeaponInstance()&&MatchingKind
        &&!bChainSlash&&!bChainSlashPending
        &&(ToolGuardInstance.IsEmpty()||!Tool||!Tool->HasAuthorityAttackInFlight())
        &&(!PS||!PS->IsQuickCombatExecuting(Pawn))
        &&Health&&!Health->IsDead()&&!(Break&&Break->IsActive())
        &&!UBoundCongregateCaptureComponent::IsCaptured(Pawn)&&!Pawn->IsTraversing()
        &&!Pawn->IsDodging()&&!Pawn->IsSliding()&&!Pawn->IsCastBlockingLeftHandAction()&&CanUse();
}

void URuneSwordComponent::SendGuardIntent(bool Raised)
{
    const auto* Pawn=Character.Get();
    if(!Pawn||!Pawn->IsLocallyControlled())return;
    if(Raised){++GuardIntentSerial;if(!GuardIntentSerial)++GuardIntentSerial;}
    if(!Pawn->HasAuthority())ServerSetSwordGuard(GuardWeaponInstance(),Raised,GuardIntentSerial);
}

void URuneSwordComponent::ServerSetSwordGuard_Implementation(const FString& Weapon,bool Raised,uint32 IntentSerial)
{
    auto* Pawn=Character.Get();if(!Pawn||!Pawn->HasAuthority()||Pawn->IsLocallyControlled())return;
    if(!IntentSerial||static_cast<int32>(IntentSerial-ServerGuardIntentSerial)<0)return;
    if(Raised&&IntentSerial==ServerGuardIntentSerial)return;
    // Validate identity before the already-raised fast path consumes a serial.
    // Otherwise an old weapon can invalidate the current weapon's lower request.
    if(Weapon!=GuardWeaponInstance()){if(Raised)ClientSwordGuardResult(Weapon,3,0.f,GetWorld()->GetTimeSeconds(),IntentSerial);return;}
    // Repeating raise with a fresh serial must not restart the parry window.
    if(Raised&&bGuarding){ServerGuardIntentSerial=IntentSerial;return;}
    if(!Raised&&IntentSerial!=ServerGuardIntentSerial)return;
    const double Now=GetWorld()->GetTimeSeconds();
    if(Raised)ServerGuardIntentSerial=IntentSerial;
    auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    if(!Raised)
    {
        NetworkGuardLoweredAt=Now;bNetworkGuardParried=false;
        bGuardHeld=bGuarding=false;if(Model)Model->DelayStaminaRecovery();return;
    }
    // Raise/lower toggling must not restart the parry window. The client's
    // RaiseSeconds+LowerSeconds animation lock is the minimum action cycle.
    if(Now-NetworkGuardLoweredAt<RuneSwordGuardTuning::RaiseSeconds+RuneSwordGuardTuning::LowerSeconds)
    {bGuardHeld=bGuarding=false;ClientSwordGuardResult(Weapon,3,0.f,Now,IntentSerial);return;}
    if(!CanMaintainNetworkGuard()||!Model||Model->Stamina()<=0.f)
    {bGuardHeld=bGuarding=false;ClientSwordGuardResult(Weapon,3,0.f,Now,IntentSerial);return;}
    if(!bGuarding)GuardStartedAt=Now;
    NetworkGuardRaisedAt=Now;bNetworkGuardParried=false;
    bGuardHeld=bGuarding=true;Model->DelayStaminaRecovery();
}

void URuneSwordComponent::TickNetworkGuard()
{
    if(GetOwner()->HasAuthority()&&bGuarding&&!CanMaintainNetworkGuard())
    {
        NetworkGuardLoweredAt=GetWorld()->GetTimeSeconds();bNetworkGuardParried=false;
        bGuardHeld=bGuarding=false;ClientSwordGuardResult(GuardWeaponInstance(),3,0.f,GetWorld()->GetTimeSeconds(),ServerGuardIntentSerial);
    }
}

void URuneSwordComponent::PresentGuardBreak()
{
    if(!Character.IsValid()||!Character->IsLocallyControlled()||!IsGuardWeaponEquipped())return;
    // Stunned while lying: the input lock still applies, the arms keep the knockdown clip.
    if(bKnockdownPose)return;
    bGuarding=bGuardHeld=bGuardReacting=bReturningGuard=false;
    bGuardBreakPose=true;GuardFeedbackAt=GetWorld()->GetTimeSeconds();GuardFeedbackStrength=1.8f;
    if(!ToolGuardInstance.IsEmpty()){ToolGuardClip=TEXT("GuardBreak");ToolGuardAge=0.f;return;}
    SetClip(Animations.FindRef(TEXT("GuardBreak"))?TEXT("GuardBreak"):TEXT("Idle"),false);
}

void URuneSwordComponent::ClientSwordGuardResult_Implementation(const FString& Weapon,uint8 Outcome,float StaminaSpent,double ServerAt,uint32 IntentSerial)
{
    auto* Pawn=Character.Get();if(!Pawn||!Pawn->IsLocallyControlled()||Pawn->HasAuthority())return;
    ReceiveGuardResult(Weapon,Outcome,StaminaSpent,ServerAt,IntentSerial);
}
void URuneSwordComponent::ReceiveGuardResult(const FString& Weapon,uint8 Outcome,float StaminaSpent,double ServerAt,uint32 IntentSerial)
{
    auto* Pawn=Character.Get();if(!Pawn)return;
    // The accepted block still spent stamina if equipment changed before this receipt.
    if(auto* Model=ColdSteelAuthority::ForPawn(Pawn);Model&&StaminaSpent>0.f)Model->SpendStamina(FMath::Min(Model->Stamina(),StaminaSpent));
    if(Weapon!=GuardWeaponInstance()||IntentSerial!=GuardIntentSerial)return;
    if(Outcome==3){ReleaseGuard();return;}
    // Replicated guard-break lock owns the pose. A separate RPC must not reset
    // the same animation when the subobject's OnRep has already started it.
    if(Outcome==2){ReleaseGuard();return;}
    GuardFeedback(Outcome==1);
    if(Outcome!=1)return;
    const auto* GS=GetWorld()->GetGameState();
    const double Age=FMath::Max(0.,(GS?GS->GetServerWorldTimeSeconds():ServerAt)-ServerAt);
    const auto& Mods=GuardModifiers();
    if(ToolGuardInstance.IsEmpty()&&Mods.ClovenSeconds>Age)
    {
        ClovenGrantedAt=GetWorld()->GetTimeSeconds()-Age;
        ClovenReadyUntil=ClovenGrantedAt+Mods.ClovenSeconds;
    }
    if(Mods.RiposteSeconds>Age)
        UCombatStatusFormula::GetOrAdd(Pawn)->GrantRiposteGuard(Mods.RiposteSeconds-Age,Mods.RiposteSpeed,Mods.RiposteStamina);
}

bool URuneSwordComponent::ClaimNetworkClovenAttack(uint32 Serial)
{
    auto* Pawn=Character.Get();auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Model?Model->Equipped():nullptr;
    if(!Pawn||!Pawn->HasAuthority()||!Serial||!Item||Item->InstanceId!=InstanceId
        ||Item->Definition!=TEXT("ue_highland_claymore")||Model->ActiveProductionTool())return false;
    const double Now=GetWorld()->GetTimeSeconds();
    if(Serial==ConsumedClovenSerial)return ClovenAttackWeapon==InstanceId&&Now<ClovenAttackUntil;
    if(ClovenReceivedSerial&&int32(Serial-ClovenReceivedSerial)<=0)return false;
    ClovenReceivedSerial=Serial;
    // A late contact can reuse an accepted attack, but it cannot create a new
    // counter while food or another hand action has reserved the pawn.
    if(Pawn->IsCastBlockingLeftHandAction())return false;
    if(static_cast<int32>(Serial-ConsumedClovenSerial)<=0||Now>=ClovenReadyUntil)return false;
    const auto Mods=ColdSteelMelee::EquippedModifiers(Model);
    if(Mods.ClovenSeconds<=0)return false;
    ConsumedClovenSerial=Serial;ClovenAttackWeapon=InstanceId;ClovenReadyUntil=0.;
    ClovenAttackUntil=Now+2.;ClovenAttackPhysical=Mods.ClovenPhysical;ClovenAttackToughness=Mods.ClovenToughness;
    GrantBroadbladeSweep(InstanceId);
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
