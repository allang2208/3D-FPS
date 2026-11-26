#pragma once
#include "CoreMinimal.h"
#include "DungeonRoomGate.h"
#include "DungeonShortcutGate.generated.h"

/** Optional maintenance return path, released only after both endpoint routes. */
UCLASS(NotBlueprintable,Transient)
class FPSGAME_API ADungeonShortcutGate : public ADungeonRoomGate
{
    GENERATED_BODY()
public:
    ADungeonShortcutGate();
    bool ConfigureReturnLink(class UDungeonRunSubsystem* InRun,const FDungeonRunDoor& Door,const FString& A,const FString& B);
    virtual void Tick(float DeltaSeconds) override;
private:
    UPROPERTY() TObjectPtr<class UBoxComponent> NavigationBarrier;
    TWeakObjectPtr<class UDungeonRunSubsystem> Run;
    FString RouteA,RouteB;
    bool bReleased=false;
};
