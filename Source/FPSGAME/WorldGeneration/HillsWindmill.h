#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HillsWindmill.generated.h"

class UStaticMesh;
class UStaticMeshComponent;

/** Placed at the existing mill-yard threshold in the streamed village. */
UCLASS()
class FPSGAME_API AHillsWindmill : public AActor
{
    GENERATED_BODY()
public:
    AHillsWindmill();
    void ApplyRepairState(bool bRepaired);
    bool IsRepairFootprintOccupied() const;
    virtual void Tick(float DeltaSeconds) override;

    // Hard references on this level instance also carry the imported kit into cooked builds.
    UPROPERTY(EditInstanceOnly, Category="Windmill")
    TMap<FName,TObjectPtr<UStaticMesh>> PartMeshes;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void Assemble();
    void UpdateDrive();
    void ShowState();
    void UpdateKeeper();
    USceneComponent* Pivot(const TCHAR* Name, USceneComponent* Parent, const FVector& Position);
    UStaticMeshComponent* Part(const TCHAR* Id, USceneComponent* Parent, const FVector& Position,
        bool bSolid = false, FQuat Rotation = FQuat::Identity, FVector Scale = FVector::OneVector);

    UPROPERTY(Transient) TObjectPtr<USceneComponent> Windshaft;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> UprightShaft;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> StoneSpindle;
    UPROPERTY(Transient) TObjectPtr<AActor> Keeper;
    bool bReady = false;
    bool bRestored = false;
    bool bAssembled = false;
};
