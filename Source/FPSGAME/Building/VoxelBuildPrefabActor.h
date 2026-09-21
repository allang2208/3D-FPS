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
    /**
     * 失去支撑后脱落：占位网格切成刚体自由落体，`LifeSeconds` 秒后销毁。
     * 逻辑构件（门／窗／喷泉）的根是空 SceneComponent，不能自己模拟物理，所以这里把它挂到
     * 占位网格上跟随落体、打上 `VoxelDetached` 停止 E 键交互并关掉碰撞与 Tick；
     * `FallbackMesh` 是逻辑构件在调色板里的代表网格（占位 Actor 平时不带网格）。
     * @return 成功进入落体状态返回 true；false 表示调用方应直接销毁该 Actor。
     */
    bool BeginFall(UStaticMesh* FallbackMesh,float LifeSeconds=8.f);
    /**
     * 是否正在坠落（`BeginFall` 成功进入落体后为 true，直到被销毁）。
     *
     * 为什么需要它：构件脱落后会立刻从 `AVoxelBuildWorld::Prefabs` 记录里移除，但 Actor 还要
     * 飞 8 秒。于是右键点一个正在下落的构件会走进 `RemovePrefab` 的"记录里查不到"分支，
     * 提示「该构件不在建筑记录中」——玩家清不掉它；更糟的是如果同一格已经放了**新**构件，
     * 用 `AnchorCell` 去查记录会命中新构件并把它销毁。有了这个标记，`RemovePrefab` 就能
     * 把"落体件"与"记录中的构件"分开处理。
     */
    bool IsFalling() const {return bFalling;}
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
    /** 见 IsFalling()。BeginFall 成功后置位；落体件不再占用 Prefabs 记录。 */
    bool bFalling=false;
};
