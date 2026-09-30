#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DungeonBloodScatter.generated.h"

class UDecalComponent;
class UMaterialInterface;

/** A bounded receiver rectangle in the scatter actor's local centimetre space. */
USTRUCT(BlueprintType)
struct FDungeonBloodSurface
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector Center=FVector::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector Normal=FVector::UpVector;
    /** Primary tangent; the second tangent is Normal cross AxisU. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector AxisU=FVector::ForwardVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector2D HalfSize=FVector2D(100.f,100.f);
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bWall=false;
};

/** Seeded, one-shot room dressing. No Tick, per-decal MID, or gameplay damage. */
UCLASS()
class FPSGAME_API ADungeonBloodScatter : public AActor
{
    GENERATED_BODY()
public:
    ADungeonBloodScatter();
    bool bGenerateOnBeginPlay=true;

    UPROPERTY(EditAnywhere, Category="Blood") TArray<FDungeonBloodSurface> Surfaces;
    UPROPERTY(EditAnywhere, Category="Blood") TObjectPtr<UMaterialInterface> BloodMaterial;
    UPROPERTY(EditAnywhere, Category="Blood", meta=(ClampMin="0",ClampMax="128")) int32 FloorCount=44;
    UPROPERTY(EditAnywhere, Category="Blood", meta=(ClampMin="0",ClampMax="64")) int32 WallCount=16;
    UPROPERTY(EditAnywhere, Category="Blood") bool bRandomizeOnBeginPlay=true;
    UPROPERTY(EditAnywhere, Category="Blood") int32 Seed=19429;
    /** Only this room's explicitly marked structural meshes receive blood. */
    UPROPERTY(EditAnywhere, Category="Blood") FName ReceiverTag=TEXT("BloodScatter.Surface");
    UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Blood") int32 ActiveSeed=0;

    /** Future generated rooms can supply their own seed after placement. */
    UFUNCTION(BlueprintCallable, Category="Blood") void GenerateFromSeed(int32 InSeed);

protected:
    virtual void BeginPlay() override;

private:
    void ScatterGroup(FRandomStream& Random, bool bOnWall, int32 DesiredCount,
                      TArray<FVector>& PlacedCenters);
    UPROPERTY(Transient) TArray<TObjectPtr<UDecalComponent>> GeneratedDecals;

public:
    /** Full square scan width in centimetres, randomized between X and Y.
     *  Zero retains the legacy procedural families for other authored rooms. */
    UPROPERTY(EditAnywhere, Category="Blood", meta=(ClampMin="0"))
    FVector2D ScannedSizeRangeCm=FVector2D::ZeroVector;
    /** Enlarge floor marks without stretching the approved wall blood. */
    UPROPERTY(EditAnywhere, Category="Blood", meta=(ClampMin="0.1")) float FloorSizeScale=1.f;
};
