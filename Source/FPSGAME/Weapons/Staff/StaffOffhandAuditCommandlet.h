#pragma once
#include "Commandlets/Commandlet.h"
#include "StaffOffhandAuditCommandlet.generated.h"

/** Explicit, read-only asset/pose probe; no player profile or level is loaded. */
UCLASS()
class UStaffOffhandAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
