#pragma once
#include "CoreMinimal.h"
#include "../Rendering/FPSFXAssetPreparation.h"

class AActor;
class USceneComponent;
class UWorld;

/** One new render operation per call. Release each temporary representative after preparation. */
class FPlayerSkillRenderPreparation
{
public:
    ~FPlayerSkillRenderPreparation();
    // Asset/script readiness always progresses. A temporary GPU representative
    // may be deferred without withholding the asset from its real consumer.
    bool Tick(UObject* Asset,UWorld* World,bool bAllowRepresentative,bool& bDeferred);
    void SkipCurrent();
private:
    AActor* Host(UWorld* World);
    TWeakObjectPtr<AActor> WarmHost;
    TWeakObjectPtr<UObject> CurrentAsset;
    TWeakObjectPtr<USceneComponent> CurrentComponent;
    FFPSFXAssetPreparation AssetPreparation;
    bool bActivated=false;
};
