#pragma once
#include "CoreMinimal.h"
#include "Widgets/SLeafWidget.h"
#include "../Skills/ColdSteelSkillTreeLayout.h"

/** Paints one routed skill-tree grid (skill tree page or a specialization page) and handles
    drag-to-pan, wheel scroll, Ctrl+wheel zoom and card clicks. Visual state comes from the owner. */
class SColdSteelSkillTreeCanvas : public SLeafWidget
{
public:
    enum class EStatus : uint8 { Locked, Available, Learned, Maxed };
    struct FCardView
    {
        FString Name, State, Side, SideSmall;
        EStatus Status = EStatus::Locked;
        float Progress = 0.f;                 // 0..1 bottom bar
        const FSlateBrush* Icon = nullptr;    // skill icon
        FString Glyph; FLinearColor GlyphColor = FLinearColor::White; // spec nodes: one-character glyph
        FString TabRight, TabLeft; bool bTabLeftMet = false;          // "全部 1/2", "跨系 · …"
        bool bStateHighlight = false;         // state line in silver (可免费习得) / gold (专精点)
        bool bStateGold = false;
        bool bDim = false, bMatch = false, bFlash = false, bLockedIcon = true;
    };
    enum class EEdge : uint8 { Unmet, Met, Lit };
    struct FSource
    {
        TFunction<FCardView(FName)> Card;
        TFunction<EEdge(int32 Entry)> Edge;
        TFunction<FString(int32 Entry)> EdgeLabel;
        TFunction<EEdge(int32 Gate)> Gate;
        TFunction<FString(int32 Gate)> GateLabel;
        TFunction<FString(const ColdSteelSkillTreeLayout::FBand&)> BandNote;
        TArray<FString> Columns;
        TSet<FName> Path; FName Selected;
    };
    DECLARE_DELEGATE_OneParam(FOnCard, FName);

    SLATE_BEGIN_ARGS(SColdSteelSkillTreeCanvas) : _bFitWidth(true), _bPannable(true) {}
        SLATE_ARGUMENT(bool, bFitWidth)
        SLATE_ARGUMENT(bool, bPannable)
        SLATE_EVENT(FOnCard, OnCardClicked)
    SLATE_END_ARGS()

    void Construct(const FArguments& Args);
    void SetLayout(ColdSteelSkillTreeLayout::FResult InLayout);
    void SetSource(FSource InSource) { Source = MoveTemp(InSource); Invalidate(EInvalidateWidgetReason::Paint); }
    void Refresh() { Invalidate(EInvalidateWidgetReason::Paint); }
    void Reveal(FName Id);
    void ZoomBy(float Factor);
    void Fit();
    float GetZoom() const { return Zoom; }
    const ColdSteelSkillTreeLayout::FResult& GetLayout() const { return Layout; }
    FName CardAtScreen(const FVector2D& Screen) const { return HitCard(GetTickSpaceGeometry(), Screen); }

    virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& Culling, FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle& Style, bool bParentEnabled) const override;
    virtual FVector2D ComputeDesiredSize(float) const override;
    virtual void Tick(const FGeometry& Geometry, const double Time, const float Delta) override;
    virtual FReply OnMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event) override;
    virtual FReply OnMouseButtonUp(const FGeometry& Geometry, const FPointerEvent& Event) override;
    virtual FReply OnMouseMove(const FGeometry& Geometry, const FPointerEvent& Event) override;
    virtual FReply OnMouseWheel(const FGeometry& Geometry, const FPointerEvent& Event) override;
    virtual void OnMouseLeave(const FPointerEvent& Event) override;
    virtual FCursorReply OnCursorQuery(const FGeometry& Geometry, const FPointerEvent& Event) const override;

private:
    ColdSteelSkillTreeLayout::FResult Layout;
    FSource Source;
    FOnCard OnCardClicked;
    bool bFitWidth = true, bPannable = true, bFitted = false, bPressed = false, bPanning = false;
    float Zoom = 1.f, FlowTime = 0.f;
    FVector2D Offset = FVector2D::ZeroVector, ViewSize = FVector2D::ZeroVector, PressAt = FVector2D::ZeroVector, PressOffset = FVector2D::ZeroVector;
    FName Hovered, PendingReveal;
    // MakeBox uses the tint as the rounded-box FILL and the brush outline colour as-is (DrawElementTypes.cpp),
    // so fills are drawn with Fill(Brush) and every outline colour has its own outline-only brush.
    FSlateBrush CardBrush[4], CardDim, Glow, SelectFrame, PathFrame, HoverFrame, TabBrush, GateUnmet, GateMet, BadgeBrush, GlyphFrame, BarTrack, BarFill;
    void Clamp();
    FName HitCard(const FGeometry& Geometry, const FVector2D& Screen) const;
    FVector2D ToContent(const FGeometry& Geometry, const FVector2D& Screen) const;
};
