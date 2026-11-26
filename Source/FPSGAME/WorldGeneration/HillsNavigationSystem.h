#pragma once
#include "CoreMinimal.h"
#include "NavigationSystem.h"
#include "HillsNavigationSystem.generated.h"

/** Map-local dynamic navigation: terrain is streamed and only invoker tiles are built. */
UCLASS(Config=Engine)
class FPSGAME_API UHillsNavigationSystem : public UNavigationSystemV1
{
    GENERATED_BODY()
public:
    UHillsNavigationSystem(const FObjectInitializer& Initializer=FObjectInitializer::Get());
    virtual void OnWorldInitDone(FNavigationSystemRunMode Mode) override;
    virtual void RegisterInvoker(AActor& Invoker,float GenerationRadius,float RemovalRadius,
        const FNavAgentSelector& Agents,ENavigationInvokerPriority Priority) override;
    UFUNCTION(BlueprintCallable,Category="Hills|Authoring",meta=(WorldContext="Context"))
    static bool InstallOnMap(UObject* Context);
};
