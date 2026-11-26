#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateBrush.h"
#include "ColdSteelMagicWheel.generated.h"

struct FStreamableHandle;
class UColdSteelHUDWidget;
class UColdSteelStatusModel;
class UTexture2D;

/** The configuration and combat views share all ten sector positions and hit geometry. */
UCLASS()
class FPSGAME_API UColdSteelMagicWheel : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelHUDWidget* OwnerHUD);
    void MovePointer(FVector2D ScreenDelta);
    int32 SelectedSlot() const;
    bool ClearsSelection() const;
    void ClearHover();
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual int32 NativePaint(const FPaintArgs&,const FGeometry&,const FSlateRect&,FSlateWindowElementList&,int32,const FWidgetStyle&,bool) const override;
    virtual FReply NativeOnMouseMove(const FGeometry&,const FPointerEvent&) override;
    virtual void NativeOnMouseLeave(const FPointerEvent&) override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent&) override;
    virtual bool NativeOnDragOver(const FGeometry&,const FDragDropEvent&,UDragDropOperation*) override;
    virtual void NativeOnDragLeave(const FDragDropEvent&,UDragDropOperation*) override;
    virtual bool NativeOnDrop(const FGeometry&,const FDragDropEvent&,UDragDropOperation*) override;
private:
    struct FLayout { FVector2D Center;float Radius=1,Scale=1; };
    FLayout Layout(const FGeometry& Geometry) const;
    void PointAt(const FGeometry& Geometry,FVector2D ScreenPosition);
    void UpdateHover();
    void RefreshBindings();
    void RequestIcons();
    void Repaint();
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<UTexture2D>> Textures;
    TWeakObjectPtr<UColdSteelHUDWidget> HUD;
    TSharedPtr<FStreamableHandle> IconLoad;
    TMap<FName,FSoftObjectPath> IconPaths;
    TMap<FName,FSlateBrush> Brushes;
    TArray<FName> Skills;
    FDelegateHandle ChangedHandle;
    FVector2D Pointer=FVector2D::ZeroVector;
    int32 Hover=INDEX_NONE,CurrentSlot=INDEX_NONE;
    bool bConfiguration=false,bDragHover=false,bValidDrop=false;
};
