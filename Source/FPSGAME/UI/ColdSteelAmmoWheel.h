#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelAmmoTypes.h"
#include "ColdSteelAmmoWheel.generated.h"

UCLASS()
class FPSGAME_API UColdSteelAmmoWheel : public UUserWidget
{
    GENERATED_BODY()
public:
    void OpenForWeapon(const FString& Id,int32 Hand=0);
    void MovePointer(FVector2D Delta);
    FString SelectedAmmo() const;
    const FString& WeaponId() const { return Instance; }
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual int32 NativePaint(const FPaintArgs&,const FGeometry&,const FSlateRect&,FSlateWindowElementList&,int32,const FWidgetStyle&,bool) const override;
private:
    UPROPERTY(Transient) TObjectPtr<class UColdSteelStatusModel> Model;
    FDelegateHandle ChangedHandle;
    TArray<FColdSteelAmmoChoice> Choices;
    FString Instance,Caption;
    FVector2D Pointer=FVector2D::ZeroVector;
    int32 Hover=INDEX_NONE;
    bool bDualHand=false;
    void RefreshCounts();
};
