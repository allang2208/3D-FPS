#include "ResidentConversation.h"
#include "ResidentTurnAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"

bool ResidentConversation::CanReach(const APawn* Pawn, const AActor* Speaker)
{
    if (!IsValid(Pawn) || !IsValid(Speaker) || Pawn->GetWorld() != Speaker->GetWorld()) return false;

    const auto* Capsule = Speaker->FindComponentByClass<UCapsuleComponent>();
    const FVector Center = Capsule ? Capsule->GetComponentLocation() : Speaker->GetActorLocation();
    if (FVector::DistSquared(Pawn->GetActorLocation(), Center) > FMath::Square(380.f)) return false;
    const FVector TalkPoint = Center + FVector(0, 0, 45);

    const auto* PC = Cast<APlayerController>(Pawn->GetController());
    const auto* Health = Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if (!PC || PC->GetPawn() != Pawn || !Health || Health->IsDead()) return false;

    FVector Eye;
    FRotator View;
    ColdSteelWorldInteraction::GetReachViewPoint(PC, Eye, View);
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ResidentConversation), false, Pawn);
    return !Pawn->GetWorld()->LineTraceSingleByChannel(Hit, Eye, TalkPoint, ECC_Visibility, Query)
        || Hit.GetActor() == Speaker;
}

void FResidentConversationFacing::SetLocalPlayer(APlayerController* Player)
{
    if (Player && !Player->IsLocalController()) return;
    LocalPlayer = Player;
    if (auto* Instance=Animation.Get()) Instance->ConversationPlayer=LocalPlayer;
}

void FResidentConversationFacing::StartIdle(USkeletalMeshComponent& Body, UAnimSequence& Idle, float StartSeconds)
{
    Body.AnimationData.AnimToPlay=&Idle;
    Body.AnimationData.SavedPosition=StartSeconds;
    Body.SetAnimInstanceClass(UResidentTurnAnimInstance::StaticClass());
    Animation=CastChecked<UResidentTurnAnimInstance>(Body.GetAnimInstance());
    Animation->ConversationPlayer=LocalPlayer;
}
