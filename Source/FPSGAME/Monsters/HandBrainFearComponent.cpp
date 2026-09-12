#include "HandBrainFearComponent.h"
#include "FPSCombatHealthComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "Engine/World.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Movement/FPSTraversalComponent.h"
float UHandBrainFearComponent::GetRemainingSeconds() const {return Expirations.IsEmpty()?0.f:FMath::Max(0.f,float(Expirations.Last()-GetWorld()->GetTimeSeconds()));}
UHandBrainFearComponent::UHandBrainFearComponent(){ PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false; }
void UHandBrainFearComponent::Apply(AActor* Source)
{
 auto* C=Cast<ACharacter>(GetOwner());if(!C||!C->HasAuthority()||!Source)return;
 Threat=Source;
 const double Now=GetWorld()->GetTimeSeconds();Expirations.RemoveAll([Now](double T){return T<=Now;});
 if(Expirations.Num()>=3)Expirations.RemoveAt(0);Expirations.Add(Now+3.0);Stacks=Expirations.Num();
 if(!LockedController.IsValid()&&C->GetController()){LockedController=C->GetController();LockedController->SetIgnoreMoveInput(true);}
 // Fear takes physical control; ordinary UI input locks do not drop the player.
 if(auto* Traversal=C->FindComponentByClass<UFPSTraversalComponent>())Traversal->Cancel();
 // Movement already ticks before its owner; placing fear before both avoids a cycle.
 C->GetCharacterMovement()->AddTickPrerequisiteComponent(this);SetComponentTickEnabled(true);
 UStatusEffectsComponent::Notify(GetOwner());
}
void UHandBrainFearComponent::TickComponent(float Dt,ELevelTick T,FActorComponentTickFunction* F)
{
 Super::TickComponent(Dt,T,F);auto* C=Cast<ACharacter>(GetOwner());if(!C)return;
 auto* Health=C->FindComponentByClass<UFPSCombatHealthComponent>();double Now=GetWorld()->GetTimeSeconds();
 const int32 Before=Stacks;Expirations.RemoveAll([Now](double End){return End<=Now;});Stacks=Expirations.Num();
 if(!Stacks||!Threat.IsValid()||(Health&&Health->IsDead())){Release();return;}
 auto* Move=C->GetCharacterMovement();RestoreSpeed=Move->MaxWalkSpeed;
 Move->MaxWalkSpeed=RestoreSpeed*FMath::Max(.01f,1.f-.33f*Stacks);
 C->ConsumeMovementInputVector();C->AddMovementInput((C->GetActorLocation()-Threat->GetActorLocation()).GetSafeNormal2D(),1.f,true);
 if(Stacks!=Before)UStatusEffectsComponent::Notify(GetOwner());
}
void UHandBrainFearComponent::Release()
{
 if(LockedController.IsValid())LockedController->SetIgnoreMoveInput(false);LockedController.Reset();
 if(auto* C=Cast<ACharacter>(GetOwner())){if(RestoreSpeed>0)C->GetCharacterMovement()->MaxWalkSpeed=RestoreSpeed;C->GetCharacterMovement()->RemoveTickPrerequisiteComponent(this);}
 Expirations.Empty();Stacks=0;SetComponentTickEnabled(false);
 if(!GetOwner()->IsActorBeingDestroyed())UStatusEffectsComponent::Notify(GetOwner());
}
void UHandBrainFearComponent::EndPlay(const EEndPlayReason::Type Reason){Release();Super::EndPlay(Reason);}
