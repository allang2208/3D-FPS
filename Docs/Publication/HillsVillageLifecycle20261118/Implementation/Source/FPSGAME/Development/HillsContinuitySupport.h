#pragma once
#include "CoreMinimal.h"
#include "../Movement/FPSFurnitureRestComponent.h"
class APlayerController;
class AFPSGAMECharacter;
class ANurseZombie;
class FJsonObject;
namespace HillsContinuity
{
bool Enabled();
bool Restart();
void Save(const FString& Name,const TSharedRef<FJsonObject>& Json);
FFurnitureRestState RestState(AActor* Pawn);
bool BodyReady(AActor* Pawn,FString* Detail=nullptr);
bool Seated(AActor* Pawn,FString& Detail);
void KeyE(APlayerController* PC);
bool Aim(APlayerController* PC,const FVector& Point);
FString InteractionTrace(APlayerController* PC,const FVector& Point);
void Place(APlayerController* PC,const FVector& Feet,const FVector& Look,bool Damage=false);
TArray<ANurseZombie*> Raiders(UWorld* World);
AFPSGAMECharacter* Character(APlayerController* PC);
}
