#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "VoxelBuildTypes.h"
#include "VoxelCollapseFragment.generated.h"

class AVoxelBuildWorld;
class UDynamicMeshComponent;
class UMaterialInterface;
struct FVoxelGeometry;

/** One compound rigid body per connected piece, never one Actor per voxel. */
UCLASS()
class FPSGAME_API AVoxelCollapseFragment : public AActor
{
    GENERATED_BODY()
public:
    AVoxelCollapseFragment();
    void Initialize(AVoxelBuildWorld* OwnerWorld,const FVoxelFragmentSave& InState,
        TSharedPtr<FVoxelGeometry> Geometry,const TArray<TObjectPtr<UMaterialInterface>>& Materials);
    void Activate();
    void FreezeForReplacement();
    void SampleVelocity();
    void EnableWaitingCollision();
    FVoxelFragmentSave Snapshot() const;
    void UpdateCellDamage(TArray<FVoxelDebrisCell> Cells);
    virtual float TakeDamage(float Amount,const FDamageEvent& Event,AController* Instigator,AActor* Causer) override;
    FGuid Id() const {return State.Id;}
    int32 ShapeCount() const {return Shapes;}
    bool IsMoving() const;
    bool HasStarted() const {return bStarted;}
    const FVoxelFragmentSave& Data() const {return State;}
    float MassKg() const {return Mass;}
    UDynamicMeshComponent* PhysicsBody() const {return Body;}
private:
    UPROPERTY() TObjectPtr<UDynamicMeshComponent> Body;
    UPROPERTY() TWeakObjectPtr<AVoxelBuildWorld> Building;
    FVoxelFragmentSave State;
    FVector PreviousVelocity=FVector::ZeroVector;
    FVector DesiredCenter=FVector::ZeroVector;
    bool bStarted=false,bReplacing=false;
    float Mass=1;
    int32 Shapes=0;
    double LastImpactTime=-1;
    UFUNCTION() void OnCollision(UPrimitiveComponent* Component,AActor* Other,UPrimitiveComponent* OtherComponent,FVector NormalImpulse,const FHitResult& Hit);
};
