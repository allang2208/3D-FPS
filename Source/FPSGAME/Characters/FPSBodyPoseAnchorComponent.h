#pragma once

#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "FPSBodyPoseAnchorComponent.generated.h"

/** Permanent non-rendering recipe/attachment anchor; visible parts use its leader. */
UCLASS()
class FPSGAME_API UFPSBodyPoseAnchorComponent : public USkeletalMeshComponent
{
    GENERATED_BODY()
public:
    // Hiding every material section still allocates a skeletal render object.
    // This anchor never owns visible skin, shadows or ray-tracing geometry.
    virtual bool ShouldCreateRenderState() const override { return false; }
    virtual void CreateRenderState_Concurrent(FRegisterComponentContext* Context) override;
    virtual FPrimitiveSceneProxy* CreateSceneProxy() override { return nullptr; }
};
