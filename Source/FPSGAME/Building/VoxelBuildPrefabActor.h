#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "VoxelBuildTypes.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildPrefabActor.generated.h"

class UMaterialInterface;
class UPhysicalMaterial;
class UStaticMesh;
class UStaticMeshComponent;

/** One placed prefab piece: a single collision mesh on the 20 cm building lattice. */
UCLASS()
class FPSGAME_API AVoxelBuildPrefabActor : public AActor
{
    GENERATED_BODY()
public:
    AVoxelBuildPrefabActor();
    void Configure(FName InId,FIntVector InCell,int32 InYaw,UStaticMesh* Mesh,UMaterialInterface* Surface,UPhysicalMaterial* Contact);
    FName PrefabId() const {return Id;}
    FIntVector AnchorCell() const {return Cell;}
    int32 Yaw() const {return QuarterTurns;}
    UStaticMeshComponent* Body() const {return MeshComponent;}
    /** 逻辑构件（门等自带 Actor 的构件）挂在占位记录下的实例；拆除时一并销毁。 */
    void AttachLogicActor(AActor* InLogicActor) {LogicActor=InLogicActor;}
    AActor* Logic() const {return LogicActor;}
    /** Authored footprint in 20 cm cells after the requested quarter turns. */
    static FIntVector RotatedFootprint(FIntVector Footprint,int32 QuarterTurns);
    /** Bounds-centred transform so a rotated piece keeps filling its snapped cell box. */
    static FTransform ComputeTransform(const FVoxelBuildPrefab& Definition,UStaticMesh* Mesh,FIntVector Cell,int32 QuarterTurns);
private:
    UPROPERTY() TObjectPtr<UStaticMeshComponent> MeshComponent;
    UPROPERTY(Transient) TObjectPtr<AActor> LogicActor;
    FName Id;
    FIntVector Cell=FIntVector::ZeroValue;
    int32 QuarterTurns=0;
};
