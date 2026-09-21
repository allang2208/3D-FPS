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
    /** Failed-placement debris: falls like any other piece but never damages the standing building. */
    void SetFailureDebris(bool bFailure) {bFailureDebris=bFailure;}
    virtual float TakeDamage(float Amount,const FDamageEvent& Event,AController* Instigator,AActor* Causer) override;
    FGuid Id() const {return State.Id;}
    int32 ShapeCount() const {return Shapes;}
    bool IsMoving() const;
    /** Time this debris has spent at rest; the building world recycles it into voxel blocks. */
    bool AccrueRestSeconds(float Delta,float Threshold)
    {
        // 2026-09-21 修复（审计 P20）：必须先确认这件残骸**已经开始模拟**。
        // IsMoving() 是 `bStarted && !bReplacing && IsAnyRigidBodyAwake()`，而 bStarted 只在
        // Activate() 里置真、Initialize() 不置。所以"已生成但被准入预算挡住（Bodies=128 /
        // Shapes=2048）还没轮到模拟"的残骸 IsMoving() 恒为 false，RestSeconds 从生成那一刻
        // 就开始累加，2 s 后被 TickFragments 的回收分支转成方块并销毁——它从未模拟过，
        // 表现是"倒塌后一部分碎块凭空消失"。加 !bStarted 前提即修掉。
        if(!bStarted||IsMoving()){RestSeconds=0;return false;}
        RestSeconds+=Delta;
        return RestSeconds>=Threshold;
    }
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
    bool bFailureDebris=false;
    float RestSeconds=0;
    float Mass=1;
    int32 Shapes=0;
    double LastImpactTime=-1;
    UFUNCTION() void OnCollision(UPrimitiveComponent* Component,AActor* Other,UPrimitiveComponent* OtherComponent,FVector NormalImpulse,const FHitResult& Hit);
};
