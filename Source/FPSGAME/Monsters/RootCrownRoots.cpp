#include "RootCrownRigPreview.h"
#include "RootCrownRootField.h"
#include "RootCrownSlashTiming.h"
#include "FPSCombatHealthComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

bool ARootCrownRigPreview::CanRoots(APawn* Victim) const
{
    if(Busy()||!RootClip||!RootKnotMesh||!RootFleshMaterial||!RootWarningMaterial||!MineSignalMaterial||RootField.IsValid()
        ||ActionClock()<NextRootsAt||!GetCharacterMovement()->IsMovingOnGround()||!IsValid(Victim)||!Victim->IsPlayerControlled())return false;
    if(const auto* VictimHealth=Victim->FindComponentByClass<UFPSCombatHealthComponent>();VictimHealth&&VictimHealth->IsDead())return false;
    const FVector Delta=Victim->GetActorLocation()-GetActorLocation();
    return Delta.Size2D()>=RootCrownRootTiming::MinRange&&Delta.Size2D()<=RootCrownRootTiming::MaxRange
        &&FMath::Abs(Victim->GetNavAgentLocation().Z-GetNavAgentLocation().Z)<=80.f
        &&FVector::DotProduct(Delta.GetSafeNormal2D(),GetActorForwardVector())>=.6f&&CanSeeTarget(Victim);
}
bool ARootCrownRigPreview::PrepareRootField(APawn* Victim)
{
    const FTransform SpawnTransform(FQuat::Identity,Victim->GetActorLocation());
    auto* Field=GetWorld()->SpawnActorDeferred<ARootCrownRootField>(ARootCrownRootField::StaticClass(),SpawnTransform,this,this,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if(!Field)return false;
    if(!Field->Prepare(this,Victim))
    {
        Field->Destroy();NextRootsAt=ActionClock()+1.5;return false;
    }
    RootField=Field;UGameplayStatics::FinishSpawningActor(Field,SpawnTransform);return true;
}
void ARootCrownRigPreview::CancelRootField()
{
    if(HasAuthority())if(auto* Field=RootField.Get())Field->Destroy();
    RootField.Reset();
}
