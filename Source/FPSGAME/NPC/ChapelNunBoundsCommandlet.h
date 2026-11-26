#pragma once
#include "Commandlets/Commandlet.h"
#include "ChapelNunBoundsCommandlet.generated.h"

/** Explicit, headless diagnosis for the reported missing nun face. */
UCLASS()
class UChapelNunBoundsCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
