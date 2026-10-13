#pragma once

#include "PreviewScene.h"

/** Editor studios suspend their renderer through the world scene-recreation contract.
 * Runtime builds retain the scene until normal subsystem/world teardown. */
class FColdSteelPreviewScene final : public FPreviewScene
{
public:
    explicit FColdSteelPreviewScene(ConstructionValues Values);
    virtual void AddComponent(UActorComponent* Component, const FTransform& Transform, bool bAttachToRoot = false) override;
    virtual void RemoveComponent(UActorComponent* Component) override;
    void SuspendRendering();
    void ResumeRendering();

private:
    TArray<TWeakObjectPtr<UActorComponent>> StudioComponents;
    bool bRenderingSuspended = false;
    bool bHadFXSystem = false;
};
