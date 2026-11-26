#pragma once
#include "Commandlets/Commandlet.h"
#include "ChapelNunQualityCommandlet.generated.h"

/** Explicit offscreen inspection of the nun's imported face and groom assets. */
UCLASS()
class UChapelNunQualityCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
    /** Restore native strand root UVs after the task's Alembic import. */
    UFUNCTION(BlueprintCallable, Category="Chapel Nun Authoring")
    static bool ApplyRefinedRootUV();
};
