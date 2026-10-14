#pragma once
#include "Commandlets/Commandlet.h"
#include "MultiplayerAssetInventoryCommandlet.generated.h"

/** Read-only multiplayer asset inventory; never initializes gameplay or saves packages. */
UCLASS()
class UMultiplayerAssetInventoryCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
