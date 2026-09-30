#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DungeonRoomGate.generated.h"

class UBoxComponent;
class UInstancedStaticMeshComponent;
class UStaticMeshComponent;
struct FDungeonRunDoor;

/** Door-local, four-track grille derived from the accepted corridor gate.
 * The encounter owns its lifetime and animation clock; this actor never ticks.
 * Local X crosses the opening, Y points into the room, Z starts on its floor.
 */
UCLASS(NotBlueprintable)
class FPSGAME_API ADungeonRoomGate : public AActor
{
    GENERATED_BODY()
public:
    ADungeonRoomGate();
    bool Configure(const FDungeonRunDoor& Door);
    void SetOpenFraction(float Fraction);
    bool IsSweepOccupied(const APawn* Pawn) const;

private:
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Panels;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> GuideLeft;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> GuideRight;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Head;
    UPROPERTY() TArray<TObjectPtr<UBoxComponent>> Blockers;
    double ClearWidth = 0.;
    double ClearHeight = 0.;
    double PanelHeight = 0.;
    float LastOpenFraction = -1.f;
    UPROPERTY() TArray<TObjectPtr<UBoxComponent>> FrameBlockers;
};
