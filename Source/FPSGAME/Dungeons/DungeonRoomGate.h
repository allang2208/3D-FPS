#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DungeonRoomGate.generated.h"

class UBoxComponent;
class UInstancedStaticMeshComponent;
class UStaticMeshComponent;
class UPrimitiveComponent;
struct FDungeonRunDoor;

/** Door-local, four-track grille derived from the accepted corridor gate.
 * The encounter owns its lifetime and animation clock. Entry-only boundaries
 * tick while locked to admit individual outside players, including local prediction.
 * Local X crosses the opening, Y points into the room, Z starts on its floor.
 */
UCLASS(NotBlueprintable)
class FPSGAME_API ADungeonRoomGate : public AActor
{
    GENERATED_BODY()
public:
    ADungeonRoomGate();
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UFUNCTION() void OnRep_GateShape();
    UFUNCTION() void OnRep_GateState();
    UPROPERTY(ReplicatedUsing=OnRep_GateShape) FVector NetFloor=FVector::ZeroVector;
    UPROPERTY(ReplicatedUsing=OnRep_GateShape) FVector NetNormal=FVector::ZeroVector;
    UPROPERTY(ReplicatedUsing=OnRep_GateShape) FVector2D NetSize=FVector2D::ZeroVector;
    UPROPERTY(ReplicatedUsing=OnRep_GateState) float NetOpen=1.f;
    UPROPERTY(ReplicatedUsing=OnRep_GateState) bool NetLocked=false;
    UPROPERTY(ReplicatedUsing=OnRep_GateState) bool NetEntryOnly=false;
    static TArray<FString> AssetPaths();
    bool Configure(const FDungeonRunDoor& Door);
    void SetOpenFraction(float Fraction);
    /** Close the full doorway to pawns immediately while the visible grille travels. */
    void SetEncounterLocked(bool bLocked);
    void SetEntryOnly(bool bEnabled);
    bool WantsInboundOpening() const { return NetEntryOnly && NetLocked && !InboundCapsules.IsEmpty(); }
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
    UPROPERTY() TObjectPtr<UBoxComponent> EncounterBarrier;
    TSet<TWeakObjectPtr<UPrimitiveComponent>> InboundCapsules;
    void UpdateInboundAccess(bool bStartingLock = false);
    void ClearInboundAccess();
    void SetInboundAccess(UPrimitiveComponent* Capsule,bool bAllowed);
};
