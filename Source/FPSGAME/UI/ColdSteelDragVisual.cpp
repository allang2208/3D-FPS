#include "ColdSteelDragVisual.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/SizeBox.h"
#include "Rendering/DrawElements.h"

void UColdSteelDragVisual::Configure(const FSlateBrush* Brush,FVector2D InSize,FVector2D Grab,FVector2D Position)
{
    if(Brush)ImageBrush=*Brush;
    Size=InSize;GrabOffset=Grab;Cursor=Position;
    WidgetTree->RootWidget=WidgetTree->ConstructWidget<USizeBox>();
    SetVisibility(ESlateVisibility::HitTestInvisible);
    SetIsFocusable(false);
    SetAnchorsInViewport(FAnchors(0,0,1,1));
}
void UColdSteelDragVisual::MoveTo(FVector2D Position)
{
    Cursor=Position;
    if(auto Widget=GetCachedWidget();Widget.IsValid())Widget->Invalidate(EInvalidateWidgetReason::Paint);
}
int32 UColdSteelDragVisual::NativePaint(const FPaintArgs& A,const FGeometry& G,const FSlateRect& C,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& S,bool Enabled)const
{
    Layer=Super::NativePaint(A,G,C,Out,Layer,S,Enabled);
    if(!ImageBrush.GetResourceObject())return Layer;
    const FVector2D Origin=ScreenOrigin();
    // Viewport paint geometry is window-relative; pointer events are desktop-absolute.
    const FGeometry Viewport=UWidgetLayoutLibrary::GetViewportWidgetGeometry(this);
    const FVector2D Ratio=G.GetLocalSize()/Viewport.GetLocalSize();
    const FVector2D Local=Viewport.AbsoluteToLocal(Origin)*Ratio;
    const FVector2D Extent=(Viewport.AbsoluteToLocal(Origin+Size)-Viewport.AbsoluteToLocal(Origin))*Ratio;
    const FVector2D Image=ImageBrush.ImageSize;
    const double Fit=FMath::Min(Extent.X/FMath::Max(1.0,Image.X),Extent.Y/FMath::Max(1.0,Image.Y));
    const FVector2D DrawSize=Image*Fit;
    FSlateDrawElement::MakeBox(Out,Layer+1,G.ToPaintGeometry(DrawSize,FSlateLayoutTransform(Local+(Extent-DrawSize)*.5)),&ImageBrush,ESlateDrawEffect::None,FLinearColor(1,1,1,.9f));
    return Layer+1;
}
