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
