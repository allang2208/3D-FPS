#pragma once
#include "Commandlets/Commandlet.h"
#include "LoneOffhandBladeAuditCommandlet.generated.h"

/** Read-only pose probe of the lone off-hand blade (main hand empty, the single kukri / hatchet clips mirrored onto the left
 *  arm): the left blade against the mirrored right one, and the grip through clip changes.  No profile or level. */
UCLASS()
class ULoneOffhandBladeAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
