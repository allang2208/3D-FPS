#pragma once
#include "Widgets/SCompoundWidget.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "ColdSteelUIStyle.h"

/** Shared, resolution-independent cold-steel mount for firearm part images. */
class SFramedAttachmentIcon : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SFramedAttachmentIcon) : _Selected(false), _Installed(false), _FramedImage(false) {}
        SLATE_ATTRIBUTE(bool, Selected)
        SLATE_ATTRIBUTE(bool, Installed)
        SLATE_ARGUMENT(bool, FramedImage)
        SLATE_DEFAULT_SLOT(FArguments, Content)
    SLATE_END_ARGS()

    void Construct(const FArguments& Args)
    {
        Selected=Args._Selected; Installed=Args._Installed;
        bFramedImage=Args._FramedImage;
        ChildSlot.Padding(bFramedImage?0:5)[Args._Content.Widget];
    }

    virtual int32 OnPaint(const FPaintArgs& Args,const FGeometry& G,const FSlateRect& Cull,
        FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool Enabled) const override
    {
        const FVector2D Size=G.GetLocalSize();
        const auto Tint=Style.GetColorAndOpacityTint();
        const auto* White=FCoreStyle::Get().GetBrush("WhiteBrush");
        const auto Box=[&](int32 Z,FVector2D P,FVector2D S,FLinearColor C)
        {
            FSlateDrawElement::MakeBox(Out,Z,G.ToPaintGeometry(S,FSlateLayoutTransform(P)),White,
                ESlateDrawEffect::None,C*Tint);
        };
        // Recessed dark face, with a lit upper bevel and shaded lower bevel.
        if(!bFramedImage)
        {
        Box(Layer,{0,0},Size,ColdSteelUI::Content);
        const auto Edge=Selected.Get()?ColdSteelUI::Success:IsHovered()?ColdSteelUI::Accent:ColdSteelUI::Border;
        Box(Layer+1,{0,0},{Size.X,1},Edge);
        Box(Layer+1,{0,0},{1,Size.Y},Edge);
        Box(Layer+1,{0,Size.Y-1},{Size.X,1},ColdSteelUI::Border);
        Box(Layer+1,{Size.X-1,0},{1,Size.Y},ColdSteelUI::Border);
        Box(Layer+1,{2,2},{Size.X-4,1},ColdSteelUI::Border);
        Box(Layer+1,{2,Size.Y-3},{Size.X-4,1},ColdSteelUI::GlassFallback);
        }
        const int32 Top=SCompoundWidget::OnPaint(Args,G,Cull,Out,Layer+2,Style,Enabled);
        if(Installed.Get())
        {
            Box(Top+1,{Size.X-13,Size.Y-13},{11,11},ColdSteelUI::Content);
            TArray<FVector2D> Check{{Size.X-11,Size.Y-8},{Size.X-8,Size.Y-5},{Size.X-4,Size.Y-10}};
            FSlateDrawElement::MakeLines(Out,Top+2,G.ToPaintGeometry(),Check,ESlateDrawEffect::None,
                ColdSteelUI::Accent*Tint,true,1.f);
        }
        return Top+2;
    }
private:
    TAttribute<bool> Selected,Installed;
    bool bFramedImage=false;
};
