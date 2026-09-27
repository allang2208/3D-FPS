#pragma once
#include "Commandlets/Commandlet.h"
#include "StaffAssemblyAuditCommandlet.generated.h"

// Explicit staff inspection. Uses a transient preview world and never loads a player save.
UCLASS()
class UStaffAssemblyAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
