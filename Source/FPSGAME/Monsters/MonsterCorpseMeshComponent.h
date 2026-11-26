#pragma once

#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "MonsterCorpseMeshComponent.generated.h"

/** Only manages render invalidation after the existing death solver has frozen. */
UCLASS()
class FPSGAME_API UMonsterCorpseMeshComponent : public USkeletalMeshComponent
{
    GENERATED_BODY()
public:
    void BeginFrozenShadowCaching();
    bool TryBuildFrozenStaticMesh();
    /** Returns the lightweight LOD reserved for frozen corpses, or INDEX_NONE. */
    UFUNCTION(BlueprintCallable, Category="Development|Monsters")
    static int32 PrepareFrozenProxyLOD(USkeletalMesh* Source);
    bool HasFrozenStaticMesh() const { return FrozenStaticMesh != nullptr; }
    void RestoreFrozenSkeletalMesh();
    virtual bool ShouldCreateRenderState() const override;
private:
    UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> FrozenStaticMesh;
public:
    virtual void FinalizeBoneTransform() override;
    virtual FPrimitiveSceneProxy* CreateSceneProxy() override;
private:
    bool bFrozenShadowCacheManaged = false;
};

/** Same frozen-pose policy for the soft-body solver's display mesh. */
UCLASS()
class FPSGAME_API UMonsterCorpsePoseableMeshComponent : public UPoseableMeshComponent
{
    GENERATED_BODY()
public:
    void BeginFrozenShadowCaching();
    virtual void FinalizeBoneTransform() override;
    virtual FPrimitiveSceneProxy* CreateSceneProxy() override;
private:
    bool bFrozenShadowCacheManaged = false;
    bool bFrozenPose = false;
};
