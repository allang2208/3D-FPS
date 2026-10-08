#include "BoundCongregateCaptureComponent.h"
#include "BoundCongregate.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Movement/FPSTraversalComponent.h"
#include "GameFramework/RootMotionSource.h"
#include "Net/UnrealNetwork.h"

UBoundCongregateCaptureComponent::UBoundCongregateCaptureComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PrePhysics;
}
UBoundCongregateCaptureComponent* UBoundCongregateCaptureComponent::GetOrAdd(ACharacter* Victim)
{
    if(!Victim||!Victim->HasAuthority())return nullptr;
    auto* Result=Victim->FindComponentByClass<UBoundCongregateCaptureComponent>();
    if(!Result){Result=NewObject<UBoundCongregateCaptureComponent>(Victim);Victim->AddInstanceComponent(Result);Result->RegisterComponent();}
    return Result;
}
bool UBoundCongregateCaptureComponent::IsCaptured(const AActor* Victim)
{
    const auto* C=Victim?Victim->FindComponentByClass<UBoundCongregateCaptureComponent>():nullptr;
    return C&&C->IsHeld();
}
bool UBoundCongregateCaptureComponent::IsHeld() const
{
    return IsValid(Source)&&!Source->Dead()&&!Source->Controlled();
}
bool UBoundCongregateCaptureComponent::IsHeldBy(const ABoundCongregate* Captor) const {return Source==Captor;}
bool UBoundCongregateCaptureComponent::HitRestraintWithQuickMelee()
{
    if(!GetOwner()->HasAuthority()||!IsHeld())return false;
    if(const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
    // Each weapon's existing contact latch admits exactly one hit per F action.
    // The restraint is on the victim, so escape does not require facing the captor.
    ++EscapeHits;
    GetOwner()->ForceNetUpdate();
    if(EscapeHits>=RequiredEscapeHits)Source->CancelTentacle();
    return true;
}
bool UBoundCongregateCaptureComponent::Capture(ABoundCongregate* Captor)
{
    auto* Victim=Cast<ACharacter>(GetOwner());
    if(!Victim||!Victim->HasAuthority()||!Captor||IsValid(Source))return false;
    const auto* Health=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    const auto* Status=Victim->FindComponentByClass<UCombatStatusFormula>();
    if((Health&&(Health->IsDead()||Health->IsInvulnerable()))||(Status&&Status->IsImmune()))return false;
    EscapeHits=0;Source=Captor;ApplyControl();Victim->ForceNetUpdate();return true;
}
void UBoundCongregateCaptureComponent::Release(ABoundCongregate* Captor)
{
    if(!GetOwner()->HasAuthority()||Source!=Captor)return;
    Source=nullptr;ClearControl();GetOwner()->ForceNetUpdate();
}
void UBoundCongregateCaptureComponent::OnRep_Captor(){if(IsValid(Source))ApplyControl();else ClearControl();}
void UBoundCongregateCaptureComponent::ApplyControl()
{
    auto* Victim=Cast<ACharacter>(GetOwner());if(!Victim)return;
    if(auto* Traversal=Victim->FindComponentByClass<UFPSTraversalComponent>())Traversal->Cancel();
    if(auto* Movement=Cast<UFPSCharacterMovementComponent>(Victim->GetCharacterMovement()))Movement->CancelDodge();
    // IgnoreMoveInput is also treated as a full weapon/UI action lock. Use the
    // character's movement-only gate so held hands, aim and F remain available.
    Victim->StopJumping();Victim->ConsumeMovementInputVector();
    Victim->GetCharacterMovement()->StopMovementImmediately();
    Victim->GetCharacterMovement()->AddTickPrerequisiteComponent(this);SetComponentTickEnabled(true);
}
void UBoundCongregateCaptureComponent::ClearControl()
{
    if(auto* Victim=Cast<ACharacter>(GetOwner()))
    {
        auto* Move=Victim->GetCharacterMovement();
        if(PullMotionId){Move->RemoveRootMotionSourceByID(PullMotionId);Move->Velocity.X=Move->Velocity.Y=0;}
        Move->RemoveTickPrerequisiteComponent(this);
    }
    PullMotionId=0;SetComponentTickEnabled(false);
}
void UBoundCongregateCaptureComponent::TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Dt,Type,Tick);
    auto* Victim=Cast<ACharacter>(GetOwner());
    if(!Victim||!IsValid(Source)||Source->Dead()||Source->Controlled()){ClearControl();return;}
    if(const auto* Health=Victim->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())
    {if(Victim->HasAuthority())Source->CancelTentacle();else ClearControl();return;}
    if(!Victim->HasAuthority()&&!Victim->IsLocallyControlled())return;
    auto* Move=Victim->GetCharacterMovement();
    Victim->StopJumping();Victim->ConsumeMovementInputVector();
    if(auto Existing=Move->GetRootMotionSource(TEXT("BoundCongregateCapture")))PullMotionId=Existing->LocalID;
    if(!PullMotionId||!Move->GetRootMotionSourceByID(PullMotionId))
    {
        auto Motion=MakeShared<FRootMotionSource_ConstantForce>();
        Motion->InstanceName=TEXT("BoundCongregateCapture");Motion->Priority=2000;
        Motion->AccumulateMode=ERootMotionAccumulateMode::Override;Motion->Duration=-1.f;
        Motion->Settings.SetFlag(ERootMotionSourceSettingsFlags::IgnoreZAccumulate);
        Motion->FinishVelocityParams.Mode=ERootMotionFinishVelocityMode::MaintainLastRootMotionVelocity;
        PullMotionId=Move->ApplyRootMotionSource(Motion);
    }
    if(auto Motion=Move->GetRootMotionSourceByID(PullMotionId))
        StaticCastSharedPtr<FRootMotionSource_ConstantForce>(Motion)->Force=Source->CapturePullVelocity(Victim);
}
void UBoundCongregateCaptureComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if(GetOwner()->HasAuthority()&&IsValid(Source))Source->CancelTentacle();
    ClearControl();Super::EndPlay(Reason);
}
void UBoundCongregateCaptureComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UBoundCongregateCaptureComponent,Source);
    DOREPLIFETIME(UBoundCongregateCaptureComponent,EscapeHits);
}
