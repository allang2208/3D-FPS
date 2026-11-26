#pragma once
#include "Commandlets/Commandlet.h"
#include "HatchetGripAuditCommandlet.generated.h"

/** Explicit offline catalog and damage checks, using an isolated disposable profile. */
UCLASS()
class UHatchetGripAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
