#pragma once
#include "Commandlets/Commandlet.h"
#include "StaffGunsmithAuditCommandlet.generated.h"

/** Explicit, headless staff transaction diagnosis using a unique disposable profile. */
UCLASS()
class UStaffGunsmithAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
