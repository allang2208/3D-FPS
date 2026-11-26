#pragma once
#include "Commandlets/Commandlet.h"
#include "Components/SceneCaptureComponent2D.h"
#include "GhostScytheMistCaptureCommandlet.generated.h"

UCLASS()
class UGhostScytheOwnerCapture : public USceneCaptureComponent2D
{
    GENERATED_BODY()
    virtual const AActor* GetViewOwner() const override { return GetOwner(); }
};

UCLASS()
class UGhostScytheMistCaptureCommandlet : public UCommandlet
{
    GENERATED_BODY()
    virtual int32 Main(const FString& Params) override;
};
