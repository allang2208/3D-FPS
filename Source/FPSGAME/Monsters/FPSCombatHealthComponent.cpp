#include "FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameModeBase.h"
#include "Camera/PlayerCameraManager.h"
#include "TimerManager.h"

void UFPSCombatHealthComponent::BeginPlay()
{
    Super::BeginPlay();
    Health = MaxHealth;
    GetOwner()->OnTakeAnyDamage.AddDynamic(this, &UFPSCombatHealthComponent::OnDamage);
}

void UFPSCombatHealthComponent::OnDamage(AActor* Actor, float Damage, const UDamageType*, AController*, AActor*)
{
    if (!Actor->HasAuthority() || IsDead() || Damage <= 0.f) return;
    if(GetWorld()->GetNetMode()==NM_Standalone)
        if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            Damage=FMath::Max(1.f,Damage-Profile->Derived(TEXT("def")));
    Health = FMath::Max(0.f, Health - Damage);
    UE_LOG(LogTemp, Display, TEXT("PLAYER_DAMAGE amount=%.1f health=%.1f"), Damage, Health);
    if (GEngine) GEngine->AddOnScreenDebugMessage(91401, 3.f, FColor::Red,
        FString::Printf(TEXT("HP %.0f / %.0f%s"), Health, MaxHealth, IsDead() ? TEXT(" - Respawning...") : TEXT("")));
    ACharacter* Character = Cast<ACharacter>(Actor);
    APlayerController* PC = Character ? Cast<APlayerController>(Character->GetController()) : nullptr;
    if (PC && PC->PlayerCameraManager)
        PC->PlayerCameraManager->StartCameraFade(.3f, 0.f, .3f, FLinearColor(.6f,0,0), false, false);
    if (IsDead() && Character && PC)
    {
        Character->DisableInput(PC);
        Character->GetCharacterMovement()->StopMovementImmediately();
        Character->GetCharacterMovement()->DisableMovement();
        Character->SetActorTickEnabled(false); // Stops held-fire and movement updates until the new pawn exists.
        GetWorld()->GetTimerManager().SetTimer(RespawnTimer, this, &UFPSCombatHealthComponent::Respawn, 2.f, false);
    }
}

void UFPSCombatHealthComponent::Respawn()
{
    APawn* Pawn = Cast<APawn>(GetOwner());
    AController* Controller = Pawn ? Pawn->GetController() : nullptr;
    AGameModeBase* Mode = GetWorld()->GetAuthGameMode();
    if (!Pawn || !Controller || !Mode) return;
    Controller->UnPossess();
    Pawn->Destroy();
    Mode->RestartPlayer(Controller);
}

void UFPSCombatHealthComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorld()->GetTimerManager().ClearTimer(RespawnTimer);
    Super::EndPlay(Reason);
}
