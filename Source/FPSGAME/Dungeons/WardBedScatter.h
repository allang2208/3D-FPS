#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "WardBedScatter.generated.h"

class UInstancedStaticMeshComponent;
class UStaticMesh;

USTRUCT(BlueprintType)
struct FWardBedRoom
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) FName RoomId;
    /** Local centimetres; Min.Z is the visible finished floor. */
    UPROPERTY(EditAnywhere) FBox Bounds=FBox(ForceInit);
};

USTRUCT(BlueprintType)
struct FWardBedPose
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) FName PoseId;
    UPROPERTY(EditAnywhere) FRotator Rotation=FRotator::ZeroRotator;
    /** Offline bounds of the rotated mesh AND collision, not its unrotated box. */
    UPROPERTY(EditAnywhere) FBox Bounds=FBox(ForceInit);
    UPROPERTY(EditAnywhere, meta=(ClampMin="0")) float Weight=1.f;
};

USTRUCT(BlueprintType)
struct FWardRoomProp
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) FName TypeId;
    UPROPERTY(EditAnywhere) TObjectPtr<UStaticMesh> Mesh;
    UPROPERTY(EditAnywhere, meta=(ClampMin="0",ClampMax="2")) int32 MinPerRoom=0;
    UPROPERTY(EditAnywhere, meta=(ClampMin="0",ClampMax="2")) int32 MaxPerRoom=1;
    /** Visual occupancy applies even when gameplay collision is disabled. */
    UPROPERTY(EditAnywhere) float Clearance=80.f;
    UPROPERTY(EditAnywhere) bool bBlocking=true;
};

/** One-shot dressing; beds and small props share a single occupancy ledger. */
UCLASS()
class FPSGAME_API AWardBedScatter : public AActor
{
    GENERATED_BODY()
public:
    AWardBedScatter();
    // The dungeon assembler populates only after all room collision is registered.
    bool bGenerateOnBeginPlay=true;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UInstancedStaticMeshComponent> Beds;
    UPROPERTY(EditAnywhere, Category="Beds") TObjectPtr<UStaticMesh> BedMesh;
    UPROPERTY(EditAnywhere, Category="Beds") TArray<FWardBedRoom> Rooms;
    UPROPERTY(EditAnywhere, Category="Beds") TArray<FWardBedPose> Poses;
    UPROPERTY(EditAnywhere, Category="Beds") TArray<FBox> KeepClear;
    UPROPERTY(EditAnywhere, Category="Beds", meta=(ClampMin="0",ClampMax="8")) int32 MinBedsPerRoom=3;
    UPROPERTY(EditAnywhere, Category="Beds", meta=(ClampMin="0",ClampMax="8")) int32 MaxBedsPerRoom=5;
    UPROPERTY(EditAnywhere, Category="Beds") float WallClearance=65.f;
    UPROPERTY(EditAnywhere, Category="Beds") float BedClearance=110.f;
    UPROPERTY(EditAnywhere, Category="Beds") bool bRandomizeOnBeginPlay=true;
    UPROPERTY(EditAnywhere, Category="Beds") int32 Seed=29481;
    UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Beds") int32 ActiveSeed=0;
    UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Beds") int32 PlacedBeds=0;
    UFUNCTION(BlueprintCallable, Category="Beds") void GenerateFromSeed(int32 InSeed);

protected:
    virtual void BeginPlay() override;

private:
    void GenerateInitial();

public:
    UPROPERTY(EditAnywhere, Category="Furnishings") TArray<FWardRoomProp> RoomProps;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> PropInstances;
};
