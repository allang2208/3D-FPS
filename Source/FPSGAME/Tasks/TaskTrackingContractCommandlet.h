#pragma once

#include "Commandlets/Commandlet.h"
#include "TaskTrackingSubsystem.h"
#include "TaskTrackingContractCommandlet.generated.h"

/** Explicit, data-only audit. No maps, assets, gameplay, rendering or profile writes. */
UCLASS()
class UTaskTrackingContractCommandlet : public UCommandlet, public ITaskTrackingSource
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
    virtual void AppendTrackedTasks(const APawn* Viewer, TArray<FTrackedTaskView>& Out) override;
private:
    TArray<FTrackedTaskView> Fixture;
};
