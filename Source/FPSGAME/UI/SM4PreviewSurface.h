#pragma once
#include "Widgets/Layout/SBorder.h"
#include "InputCoreTypes.h"

DECLARE_DELEGATE_OneParam(FWorkbenchOrbit, FVector2D);
DECLARE_DELEGATE_OneParam(FWorkbenchZoom, float);

// Only the central preview owns pointer capture; adjacent equipment controls retain their normal input.
class SM4PreviewSurface : public SBorder
{
public:
    SLATE_BEGIN_ARGS(SM4PreviewSurface) {}
        SLATE_DEFAULT_SLOT(FArguments, Content)
        SLATE_ATTRIBUTE(bool, CanRotate)
        SLATE_EVENT(FWorkbenchOrbit, OnOrbit)
        SLATE_EVENT(FWorkbenchZoom, OnZoom)
        SLATE_EVENT(FSimpleDelegate, OnReset)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args)
    {
        CanRotate=Args._CanRotate;Orbit=Args._OnOrbit;Zoom=Args._OnZoom;Reset=Args._OnReset;
        SBorder::Construct(SBorder::FArguments().Padding(0).BorderImage(nullptr)[Args._Content.Widget]);
    }
    virtual FReply OnMouseButtonDown(const FGeometry&,const FPointerEvent& E) override
    {
        if(E.GetEffectingButton()!=EKeys::LeftMouseButton||!CanRotate.Get())return FReply::Unhandled();
        return FReply::Handled().CaptureMouse(SharedThis(this));
    }
    virtual FReply OnMouseMove(const FGeometry& G,const FPointerEvent& E) override
    {
        if(!HasMouseCapture())return FReply::Unhandled();
        if(!CanRotate.Get()||!E.IsMouseButtonDown(EKeys::LeftMouseButton))return FReply::Handled().ReleaseMouseCapture();
        Orbit.ExecuteIfBound(G.AbsoluteToLocal(E.GetScreenSpacePosition())-G.AbsoluteToLocal(E.GetLastScreenSpacePosition()));
        return FReply::Handled();
    }
    virtual FReply OnMouseButtonUp(const FGeometry&,const FPointerEvent& E) override
    {
        return HasMouseCapture()&&E.GetEffectingButton()==EKeys::LeftMouseButton?FReply::Handled().ReleaseMouseCapture():FReply::Unhandled();
    }
    virtual FReply OnMouseWheel(const FGeometry&,const FPointerEvent& E) override
    {
        if(!CanRotate.Get()||!Zoom.IsBound())return FReply::Unhandled();
        Zoom.Execute(E.GetWheelDelta());return FReply::Handled();
    }
    virtual FReply OnMouseButtonDoubleClick(const FGeometry&,const FPointerEvent& E) override
    {
        if(E.GetEffectingButton()!=EKeys::LeftMouseButton||!CanRotate.Get())return FReply::Unhandled();
        Reset.ExecuteIfBound();return FReply::Handled().ReleaseMouseCapture();
    }
    virtual FCursorReply OnCursorQuery(const FGeometry&,const FPointerEvent&) const override
    {return FCursorReply::Cursor(CanRotate.Get()?(HasMouseCapture()?EMouseCursor::GrabHandClosed:EMouseCursor::GrabHand):EMouseCursor::Default);}
private:
    TAttribute<bool> CanRotate;
    FWorkbenchOrbit Orbit;
    FWorkbenchZoom Zoom;
    FSimpleDelegate Reset;
};
