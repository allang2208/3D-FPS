#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Blueprint/DragDropOperation.h"
#include "Styling/SlateBrush.h"
#include "ColdSteelIncineratorAmmoDrag.generated.h"
class UColdSteelHUDWidget;
UCLASS()
class UColdSteelIncineratorAmmoDrag : public UDragDropOperation
{
    GENERATED_BODY()
public:
    FString Ammo;
    int64 Available=0,Generation=0;
};
/** Pouch row that carries a quantity request, never creates owned ammunition during a drag. */
UCLASS()
class UColdSteelIncineratorAmmoSource : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelHUDWidget* Owner,const FString& Id,TSharedRef<SWidget> Content);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool Children) override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent&) override;
    virtual void NativeOnDragDetected(const FGeometry&,const FPointerEvent&,UDragDropOperation*&) override;
private:
    FString Ammo;
    TSharedPtr<SWidget> Contents;
    FSlateBrush Background;
    UPROPERTY(Transient) TObjectPtr<UColdSteelHUDWidget> HUD;
};
