#pragma once
#include "Components/Button.h"
#include "ColdSteelMountButton.generated.h"

class UColdSteelHUDWidget;
enum class EMountPageAction : uint8 { Back, Deploy, Call, Potion, Buy, Release, ReleaseConfirm, ReleaseCancel };

UCLASS()
class UColdSteelMountButton : public UButton
{
    GENERATED_BODY()
public:
    void Bind(UColdSteelHUDWidget* Widget,EMountPageAction InAction,FGuid InHorse={},int32 InTier=0);
private:
    TWeakObjectPtr<UColdSteelHUDWidget> Journal;
    EMountPageAction Action=EMountPageAction::Back;
    FGuid Horse;
    int32 Tier=0;
    UFUNCTION() void Press();
};
