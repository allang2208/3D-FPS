#pragma once
#include "Commandlets/Commandlet.h"
#include "SwordBladeFinishAuditCommandlet.generated.h"

/** Isolated assembly and observer reconstruction checks; no player save or map. */
UCLASS()
class USwordBladeFinishAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
