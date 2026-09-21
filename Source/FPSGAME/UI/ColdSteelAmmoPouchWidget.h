#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateTypes.h"
#include "ColdSteelAmmoPouchWidget.generated.h"

UCLASS()
class FPSGAME_API UColdSteelAmmoPouchWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetHUD(class UColdSteelHUDWidget* Owner);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool ReleaseChildren) override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry&,float) override;
private:
    UPROPERTY(Transient) TObjectPtr<class UColdSteelStatusModel> Model;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelHUDWidget> HUD;
    TSharedPtr<class SVerticalBox> Surface;
    TSharedPtr<class SScrollBox> List;
    FDelegateHandle ChangedHandle;
    TSet<FString> Expanded;
    FString Selected,WeaponInstance,LastWeapon;
    float LastScale=0;
    FButtonStyle Buttons;
    TMap<FString,TSharedPtr<FButtonStyle>> AmmoButtons;
    void Refresh();
};
