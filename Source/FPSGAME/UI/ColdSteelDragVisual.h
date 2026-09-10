#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelDragVisual.generated.h"

/** Pointer-event driven viewport overlay. UMG still owns the drag/drop transaction. */
UCLASS()
class UColdSteelDragVisual : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(const FSlateBrush* Brush,FVector2D Size,FVector2D Grab,FVector2D Position);
    void MoveTo(FVector2D Position);
    FVector2D ScreenOrigin()const{return Cursor-GrabOffset;}
    FVector2D ScreenSize()const{return Size;}
protected:
    virtual int32 NativePaint(const FPaintArgs&,const FGeometry&,const FSlateRect&,FSlateWindowElementList&,int32,const FWidgetStyle&,bool)const override;
private:
    UPROPERTY(Transient) FSlateBrush ImageBrush;
    FVector2D Size,GrabOffset,Cursor;
};
