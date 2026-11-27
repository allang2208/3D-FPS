#include "SColdSteelSkillTreeCanvas.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelUIAudio.h"
#include "Fonts/FontMeasure.h"
#include "Framework/Application/SlateApplication.h"
#include "Rendering/DrawElements.h"


namespace
{
    // Cold Steel palette (Docs/UI/ui-cold-steel-design-system.md) + HUD pale gold.
    const FLinearColor LineUnmet = ColdSteelUI::Gray(222, 87);
    const FLinearColor Flow = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("F7EED6FF")));
    FLinearColor WithAlpha(FLinearColor C, float A) { C.A *= A; return C; }
    FLinearColor Fill(const FSlateBrush& B, float A = 1.f) { return WithAlpha(B.TintColor.GetSpecifiedColor(), A); }
    FVector2D Measure(const FString& Text, const FSlateFontInfo& Font)
    { return FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure(Text, Font); }

    void Text(FSlateWindowElementList& Out, int32 Layer, const FGeometry& G, const FString& S, const FSlateFontInfo& Font, const FLinearColor& Color, FVector2D At, float AlignX = 0.f, float AlignY = 0.f)
    {
        if(S.IsEmpty()) return;
        const FVector2D Size = Measure(S, Font);
        FSlateDrawElement::MakeText(Out, Layer, G.ToPaintGeometry(Size, FSlateLayoutTransform(At - FVector2D(Size.X * AlignX, Size.Y * AlignY))), S, Font, ESlateDrawEffect::None, Color);
    }
    void Box(FSlateWindowElementList& Out, int32 Layer, const FGeometry& G, const FSlateBrush& Brush, FVector2D At, FVector2D Size, const FLinearColor& Tint = FLinearColor::White)
    { FSlateDrawElement::MakeBox(Out, Layer, G.ToPaintGeometry(Size, FSlateLayoutTransform(At)), &Brush, ESlateDrawEffect::None, Tint); }
    void Line(FSlateWindowElementList& Out, int32 Layer, const FGeometry& G, TArray<FVector2D> Points, const FLinearColor& Color, float Width)
    { if(Points.Num() >= 2) FSlateDrawElement::MakeLines(Out, Layer, G.ToPaintGeometry(), MoveTemp(Points), ESlateDrawEffect::None, Color, true, Width); }
    /** Dashes along a polyline; Phase shifts the pattern (flow animation). */
    void Dashed(FSlateWindowElementList& Out, int32 Layer, const FGeometry& G, const TArray<FVector2D>& P, const FLinearColor& Color, float Width, float Dash, float Gap, float Phase = 0.f)
    {
        const float Period = Dash + Gap; float Cursor = FMath::Fmod(Phase, Period); if(Cursor < 0) Cursor += Period;
        // Cursor = distance into the pattern at the start of the polyline.
        for(int32 I = 1; I < P.Num(); ++I)
        {
            const FVector2D A = P[I - 1], B = P[I]; const float Len = FVector2D::Distance(A, B); if(Len <= .01f) continue;
            const FVector2D Dir = (B - A) / Len; float T = 0.f;
            while(T < Len)
            {
                const float InPattern = Cursor;
                if(InPattern < Dash)
                {
                    const float Run = FMath::Min(Dash - InPattern, Len - T);
                    Line(Out, Layer, G, { A + Dir * T, A + Dir * (T + Run) }, Color, Width);
                    T += Run; Cursor += Run;
                }
                else { const float Run = FMath::Min(Period - InPattern, Len - T); T += Run; Cursor += Run; }
                if(Cursor >= Period) Cursor -= Period;
            }
        }
    }
    void Arrow(FSlateWindowElementList& Out, int32 Layer, const FGeometry& G, const TArray<FVector2D>& P, const FLinearColor& Color, float Width)
    {
        if(P.Num() < 2) return;
        const FVector2D Tip = P.Last(), Dir = (P.Last() - P[P.Num() - 2]).GetSafeNormal(), N(-Dir.Y, Dir.X);
        Line(Out, Layer, G, { Tip - Dir * 7 + N * 4.5f, Tip, Tip - Dir * 7 - N * 4.5f }, Color, Width);
    }
}

void SColdSteelSkillTreeCanvas::Construct(const FArguments& Args)
{ using namespace ColdSteelSkillTreeLayout;
    bFitWidth = Args._bFitWidth; bPannable = Args._bPannable; OnCardClicked = Args._OnCardClicked;
    // Panned / zoomed content is painted with an offset; clip to the canvas so cards and links never
    // draw over the header, legend or quickbar strip while scrolling (user report 2026-11-16).
    SetClipping(EWidgetClipping::ClipToBounds);
    using namespace ColdSteelUI;
    // Locked / Available / Learned / Maxed card surfaces (game-dev technology-card states, cold-steel tones).
    CardBrush[0] = RoundedBrush(Gray(27, 240), CardRadius, Gray(222, 20), 1);
    CardBrush[1] = RoundedBrush(Gray(44, 240), CardRadius, Accent, 1.4f);
    CardBrush[2] = RoundedBrush(Gray(33, 240), CardRadius, WithAlpha(HUDGold, .45f), 1);
    CardBrush[3] = RoundedBrush(FLinearColor::FromSRGBColor(FColor(43, 40, 34, 240)), CardRadius, HUDGoldLight, 1.4f);
    CardDim = RoundedBrush(Gray(27, 240), CardRadius, Gray(222, 14), 1);
    Glow = RoundedBrush(FLinearColor::White, CardRadius + 3, FLinearColor::Transparent, 0);
    SelectFrame = RoundedBrush(FLinearColor::Transparent, CardRadius + 1, HUDGoldLight, 2);
    PathFrame = RoundedBrush(FLinearColor::Transparent, CardRadius + 1, WithAlpha(HUDGoldLight, .85f), 1.2f);
    HoverFrame = RoundedBrush(FLinearColor::Transparent, CardRadius + 1, Gray(222, 140), 1);
    TabBrush = RoundedBrushCorners(Gray(16, 250), FVector4(4, 4, 0, 0), Gray(222, 46), 1);
    GateUnmet = RoundedBrush(Gray(18, 255), 4, Gray(222, 102), 1.4f);
    GateMet = RoundedBrush(Gray(18, 255), 4, HUDGold, 1.4f);
    BadgeBrush = RoundedBrush(FLinearColor::White, 6);
    GlyphFrame = RoundedBrush(Gray(26, 255), 9, Gray(169), 1.5f);
    BarTrack = RoundedBrush(FLinearColor(0, 0, 0, .55f), 1.5f, FLinearColor::Transparent, 0);
    BarFill = RoundedBrush(FLinearColor::White, 1.5f, FLinearColor::Transparent, 0);
    SetCanTick(true);
}

void SColdSteelSkillTreeCanvas::SetLayout(ColdSteelSkillTreeLayout::FResult InLayout)
{ using namespace ColdSteelSkillTreeLayout;
    Layout = MoveTemp(InLayout); bFitted = false; Hovered = NAME_None;
    Invalidate(EInvalidateWidgetReason::Paint);
}
FVector2D SColdSteelSkillTreeCanvas::ComputeDesiredSize(float) const
{ using namespace ColdSteelSkillTreeLayout; return bPannable ? FVector2D(200, 200) : Layout.Size * Zoom; }

void SColdSteelSkillTreeCanvas::Fit()
{ using namespace ColdSteelSkillTreeLayout;
    if(ViewSize.X <= 0) { bFitted = false; return; }
    Zoom = bFitWidth ? FMath::Clamp(float(ViewSize.X / FMath::Max(1., Layout.Size.X)), .5f, 1.f) : 1.f;
    Offset = FVector2D::ZeroVector; Clamp(); bFitted = true;
}
void SColdSteelSkillTreeCanvas::ZoomBy(float Factor)
{ using namespace ColdSteelSkillTreeLayout;
    const FVector2D Center = ViewSize / 2, Content = (Center - Offset) / Zoom;
    Zoom = FMath::Clamp(Zoom * Factor, .45f, 1.5f); Offset = Center - Content * Zoom; Clamp();
    Invalidate(EInvalidateWidgetReason::Paint);
}
void SColdSteelSkillTreeCanvas::Reveal(FName Id) { using namespace ColdSteelSkillTreeLayout; PendingReveal = Id; }
void SColdSteelSkillTreeCanvas::Clamp()
{ using namespace ColdSteelSkillTreeLayout;
    const FVector2D Scaled = Layout.Size * Zoom;
    for(int32 Axis = 0; Axis < 2; ++Axis)
    {
        if(Scaled[Axis] <= ViewSize[Axis]) Offset[Axis] = 0; // 2026-11-17: tree body aligns left, not centred
        else Offset[Axis] = FMath::Clamp(Offset[Axis], ViewSize[Axis] - Scaled[Axis], 0.);
    }
}
void SColdSteelSkillTreeCanvas::Tick(const FGeometry& Geometry, const double Time, const float Delta)
{ using namespace ColdSteelSkillTreeLayout;
    SLeafWidget::Tick(Geometry, Time, Delta);
    const FVector2D Size = Geometry.GetLocalSize();
    if(!Size.Equals(ViewSize, .5)) { ViewSize = Size; if(!bFitted) Fit(); else Clamp(); }
    if(!bFitted) Fit();
    if(!PendingReveal.IsNone())
        if(const FCard* C = Layout.Card(PendingReveal))
        {
            const FVector2D A = Offset + C->Pos * Zoom, B = A + FVector2D(Layout.Config.W, Layout.Config.H) * Zoom; const float M = 40;
            if(A.X < M || B.X > ViewSize.X - M) Offset.X += ViewSize.X / 2 - (A.X + B.X) / 2;
            if(A.Y < M || B.Y > ViewSize.Y - M) Offset.Y += ViewSize.Y / 2 - (A.Y + B.Y) / 2;
            Clamp(); PendingReveal = NAME_None;
        }
    FlowTime += Delta;
    Invalidate(EInvalidateWidgetReason::Paint); // flow line + available breathing
}

FVector2D SColdSteelSkillTreeCanvas::ToContent(const FGeometry& Geometry, const FVector2D& Screen) const
{ using namespace ColdSteelSkillTreeLayout; return (Geometry.AbsoluteToLocal(Screen) - Offset) / Zoom; }
FName SColdSteelSkillTreeCanvas::HitCard(const FGeometry& Geometry, const FVector2D& Screen) const
{ using namespace ColdSteelSkillTreeLayout;
    const FVector2D P = ToContent(Geometry, Screen);
    for(const FCard& C : Layout.Cards)
        if(P.X >= C.Pos.X && P.Y >= C.Pos.Y && P.X <= C.Pos.X + Layout.Config.W && P.Y <= C.Pos.Y + Layout.Config.H) return C.Id;
    return NAME_None;
}
FReply SColdSteelSkillTreeCanvas::OnMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event)
{ using namespace ColdSteelSkillTreeLayout;
    if(Event.GetEffectingButton() != EKeys::LeftMouseButton) return FReply::Unhandled();
    bPressed = true; bPanning = false; PressAt = Event.GetScreenSpacePosition(); PressOffset = Offset;
    return FReply::Handled().CaptureMouse(SharedThis(this));
}
FReply SColdSteelSkillTreeCanvas::OnMouseMove(const FGeometry& Geometry, const FPointerEvent& Event)
{ using namespace ColdSteelSkillTreeLayout;
    if(bPressed && bPannable)
    {
        const FVector2D Delta = Geometry.AbsoluteToLocal(Event.GetScreenSpacePosition()) - Geometry.AbsoluteToLocal(PressAt);
        if(!bPanning && Delta.Size() > 6) bPanning = true;
        if(bPanning) { Offset = PressOffset + Delta; Clamp(); return FReply::Handled(); }
    }
    const FName Hit = HitCard(Geometry, Event.GetScreenSpacePosition());
    if(Hit != Hovered) Hovered = Hit;
    return FReply::Unhandled();
}
FReply SColdSteelSkillTreeCanvas::OnMouseButtonUp(const FGeometry& Geometry, const FPointerEvent& Event)
{ using namespace ColdSteelSkillTreeLayout;
    if(Event.GetEffectingButton() != EKeys::LeftMouseButton || !bPressed) return FReply::Unhandled();
    bPressed = false;
    if(!bPanning) { const FName Hit = HitCard(Geometry, Event.GetScreenSpacePosition()); if(!Hit.IsNone()) { ColdSteelUIAudio::PlayFromSlate(ColdSteelUIAudio::ECue::Slot); OnCardClicked.ExecuteIfBound(Hit); } }
    bPanning = false;
    return FReply::Handled().ReleaseMouseCapture();
}
FReply SColdSteelSkillTreeCanvas::OnMouseWheel(const FGeometry& Geometry, const FPointerEvent& Event)
{ using namespace ColdSteelSkillTreeLayout;
    if(!bPannable) return FReply::Unhandled();
    if(Event.IsControlDown())
    {
        const FVector2D At = Geometry.AbsoluteToLocal(Event.GetScreenSpacePosition()), Content = (At - Offset) / Zoom;
        Zoom = FMath::Clamp(Zoom * FMath::Exp(Event.GetWheelDelta() * .12f), .45f, 1.5f); Offset = At - Content * Zoom;
    }
    else if(Event.IsShiftDown()) Offset.X += Event.GetWheelDelta() * 80;
    else Offset.Y += Event.GetWheelDelta() * 80;
    Clamp(); return FReply::Handled();
}
void SColdSteelSkillTreeCanvas::OnMouseLeave(const FPointerEvent& Event) { using namespace ColdSteelSkillTreeLayout; SLeafWidget::OnMouseLeave(Event); Hovered = NAME_None; }
FCursorReply SColdSteelSkillTreeCanvas::OnCursorQuery(const FGeometry&, const FPointerEvent&) const
{ using namespace ColdSteelSkillTreeLayout; return FCursorReply::Cursor(bPanning ? EMouseCursor::GrabHandClosed : !Hovered.IsNone() ? EMouseCursor::Hand : bPannable ? EMouseCursor::GrabHand : EMouseCursor::Default); }

int32 SColdSteelSkillTreeCanvas::OnPaint(const FPaintArgs&, const FGeometry& Geometry, const FSlateRect& Culling, FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle&, bool) const
{ using namespace ColdSteelSkillTreeLayout;
    using namespace ColdSteelUI;
    if(!Source.Card) return Layer;
    const FGeometry G = Geometry.MakeChild(Layout.Size, FSlateLayoutTransform(Zoom, Offset));
    const FConfig& C = Layout.Config;
    const bool bFocus = Source.Path.Num() > 1;
    const auto OnPath = [&](FName A, FName B) { return Source.Path.Contains(A) && Source.Path.Contains(B); };
    const auto Muted = [&](bool bOn) { return bFocus && !bOn ? .28f : 1.f; };
    const FSlateFontInfo F11 = NumberFont(11 * .75f), F12 = TextFont(12 * .75f), F13 = TextFont(13 * .75f, true), F16 = TextFont(16 * .75f, true);

    // ---- bands (系别行) and column heads (等阶) ----
    FString LastGroup;
    for(int32 I = 0; I < Layout.Bands.Num(); ++I)
    {
        const FBand& B = Layout.Bands[I];
        const float Top = C.OY + B.Lane * (C.H + C.LaneGap) - C.LaneGap / 2, Height = B.Span * (C.H + C.LaneGap);
        const bool bGroupStart = !B.Group.IsEmpty() && B.Group != LastGroup;
        if(I > 0) Line(Out, Layer, G, { FVector2D(8, Top), FVector2D(Layout.Size.X - 8, Top) }, bGroupStart ? WithAlpha(HUDGold, .22f) : Gray(222, 20), 1);
        Line(Out, Layer, G, { FVector2D(20, Top + 10), FVector2D(20, Top + Height - 10) }, WithAlpha(HUDGold, .35f), 2);
        float Y = Top + Height / 2 - (bGroupStart ? 24 : 16);
        if(bGroupStart) { Text(Out, Layer, G, B.Group, TextFont(11 * .75f), HUDGoldDim, FVector2D(32, Y)); Y += 16; }
        Text(Out, Layer, G, B.Name, F16, HUDGold, FVector2D(32, Y)); Y += 22;
        Text(Out, Layer, G, Source.BandNote ? Source.BandNote(B) : B.Note, F11, TextTertiary, FVector2D(32, Y));
        LastGroup = B.Group;
    }
    for(int32 I = 0; I < Source.Columns.Num(); ++I)
    {
        const float X = C.OX + I * (C.W + C.Gap);
        Text(Out, Layer, G, Source.Columns[I], F13, TextSecondary, FVector2D(X + C.W / 2, C.OY - 30), .5f, .5f);
        Line(Out, Layer, G, { FVector2D(X, C.OY - 16), FVector2D(X + C.W, C.OY - 16) }, Gray(222, 46), 1);
    }
    ++Layer;

    // ---- links: buses, branches, junctions, ports, gates (game-dev technology-link family) ----
    auto EdgeColor = [&](EEdge E) { return E == EEdge::Unmet ? LineUnmet : E == EEdge::Met ? HUDGoldDim : HUDGold; };
    auto Stroke = [&](const TArray<FVector2D>& P, EEdge E, float Width, float Alpha, bool bArrow)
    {
        const FLinearColor Col = WithAlpha(EdgeColor(E), Alpha);
        if(E == EEdge::Unmet) Dashed(Out, Layer, G, P, Col, Width, 7, 5);
        else { if(E == EEdge::Lit && Alpha > .5f) Line(Out, Layer, G, P, WithAlpha(HUDGold, .13f), 7); Line(Out, Layer, G, P, Col, Width); }
        if(bArrow) Arrow(Out, Layer + 1, G, P, Col, Width);
    };
    auto Strongest = [&](const TArray<int32>& Entries) { EEdge Best = EEdge::Unmet; for(int32 E : Entries) Best = FMath::Max(Best, Source.Edge(E)); return Best; };
    for(const FBus& B : Layout.Buses)
    {
        bool bOn = false; for(int32 E : B.Entries) bOn |= OnPath(Layout.Entries[E].From, Layout.Entries[E].To);
        const EEdge E = Strongest(B.Entries);
        Stroke(B.Stub, E, 3.4f, Muted(bOn), false); Stroke(B.Trunk, E, 3.4f, Muted(bOn), false);
    }
    for(const FLink& L : Layout.Links)
    {
        const FEntry& E = Layout.Entries[L.Entry];
        Stroke(L.Points, Source.Edge(L.Entry), 2.2f, Muted(OnPath(E.From, E.To)), L.bArrow);
    }
    for(const FJunction& J : Layout.Junctions)
    {
        bool bOn = false; for(int32 E : J.Entries) bOn |= OnPath(Layout.Entries[E].From, Layout.Entries[E].To);
        Box(Out, Layer + 1, G, BadgeBrush, J.At - FVector2D(3), FVector2D(6), WithAlpha(Strongest(J.Entries) == EEdge::Unmet ? Gray(106) : EdgeColor(Strongest(J.Entries)), Muted(bOn)));
    }
    for(const FPort& P : Layout.Ports) Box(Out, Layer + 1, G, BadgeBrush, P.At - FVector2D(3.5f), FVector2D(7), Source.Edge(P.Entry) == EEdge::Unmet ? Gray(106) : EdgeColor(Source.Edge(P.Entry)));
    for(int32 I = 0; I < Layout.Gates.Num(); ++I)
    {
        const FGate& Gt = Layout.Gates[I]; const EEdge State = Source.Gate ? Source.Gate(I) : EEdge::Unmet;
        bool bOn = Source.Path.Contains(Gt.To); bool bAny = false; for(int32 E : Gt.Inputs) bAny |= Source.Path.Contains(Layout.Entries[E].From); bOn &= bAny;
        const float A = Muted(bOn);
        Stroke(Gt.Output, State, 2.6f, A, true);
        const FSlateBrush& GateBox = State == EEdge::Unmet ? GateUnmet : GateMet;
        Box(Out, Layer + 1, G, GateBox, Gt.Center - FVector2D(22, 12), FVector2D(44, 24), Fill(GateBox, A));
        Text(Out, Layer + 2, G, TEXT("任一"), TextFont(12 * .75f, true), WithAlpha(State == EEdge::Unmet ? TextSecondary : HUDGoldLight, A), Gt.Center, .5f, .5f);
        if(Source.GateLabel) Text(Out, Layer + 2, G, Source.GateLabel(I), F11, WithAlpha(State == EEdge::Unmet ? TextTertiary : HUDGold, A), Gt.Center - FVector2D(0, 20), .5f, .5f);
    }
    // Labels last on the link layer so lines never cover them.
    if(Source.EdgeLabel)
        for(const FLink& L : Layout.Links)
        {
            if(!L.bHasLabel || !Layout.Entries[L.Entry].Gate.IsNone()) continue;
            const FString S = Source.EdgeLabel(L.Entry); if(S.IsEmpty()) continue;
            const FEntry& E = Layout.Entries[L.Entry]; const EEdge State = Source.Edge(L.Entry);
            FSlateFontInfo Font = F11; Font.OutlineSettings.OutlineSize = 3; Font.OutlineSettings.OutlineColor = Gray(16);
            Text(Out, Layer + 2, G, S, Font, WithAlpha(State == EEdge::Unmet ? TextTertiary : HUDGold, Muted(OnPath(E.From, E.To))), L.Label, .5f, .5f);
        }
    // Focus route: halo + flowing dashes from the centre-side start to the selected card.
    if(bFocus)
    {
        auto Focus = [&](const TArray<FVector2D>& P, bool bArrow)
        {
            Line(Out, Layer + 3, G, P, WithAlpha(HUDGoldLight, .2f), 9);
            Dashed(Out, Layer + 4, G, P, Flow, 2.6f, 12, 7, -FlowTime * 18.f);
            if(bArrow) Arrow(Out, Layer + 4, G, P, Flow, 2.4f);
        };
        for(const FLink& L : Layout.Links) { const FEntry& E = Layout.Entries[L.Entry]; if(OnPath(E.From, E.To)) Focus(L.FullPoints, L.bArrow); }
        for(const FGate& Gt : Layout.Gates)
        {
            bool bAny = false; for(int32 E : Gt.Inputs) bAny |= Source.Path.Contains(Layout.Entries[E].From);
            if(bAny && Source.Path.Contains(Gt.To)) Focus(Gt.Output, true);
        }
    }
    Layer += 5;

    // ---- cards ----
    // Layers: +0 available glow, +1 card fill, +2 icon / glyph frame / bar track, +3 text / bar fill,
    // +4 frames, brackets and tabs (outline-only frames use a transparent tint), +5 tab text.
    const float Breath = .5f + .5f * FMath::Sin(FlowTime * 2.6f);
    for(const FCard& Card : Layout.Cards)
    {
        const FCardView V = Source.Card(Card.Id);
        const int32 S = int32(V.Status); const float A = V.bDim ? .2f : 1.f;
        const FVector2D P = Card.Pos, Size(C.W, C.H);
        if(V.Status == EStatus::Available && !V.bDim) Box(Out, Layer, G, Glow, P - FVector2D(3), Size + FVector2D(6), WithAlpha(Accent, .10f + .32f * Breath));
        const FSlateBrush& Surface = V.bDim ? CardDim : CardBrush[S];
        Box(Out, Layer + 1, G, Surface, P, Size, Fill(Surface, V.bDim ? .5f : 1.f));
        const bool bSelected = Card.Id == Source.Selected, bPath = Source.Path.Contains(Card.Id) && !bSelected, bHover = Card.Id == Hovered;
        if(bSelected) Box(Out, Layer + 4, G, SelectFrame, P - FVector2D(1), Size + FVector2D(2), FLinearColor::Transparent);
        else if(bPath || V.bMatch) Box(Out, Layer + 4, G, PathFrame, P - FVector2D(1), Size + FVector2D(2), FLinearColor::Transparent);
        else if(bHover) Box(Out, Layer + 4, G, HoverFrame, P - FVector2D(1), Size + FVector2D(2), FLinearColor::Transparent);
        if(bSelected)
        {
            const FLinearColor Gold = HUDGoldLight; const float L = 14, O = 7;
            Line(Out, Layer + 4, G, { P + FVector2D(-O, -O + L), P + FVector2D(-O, -O), P + FVector2D(-O + L, -O) }, Gold, 2);
            Line(Out, Layer + 4, G, { P + Size + FVector2D(O, O - L), P + Size + FVector2D(O, O), P + Size + FVector2D(O - L, O) }, Gold, 2);
        }
        // icon or spec glyph
        const FVector2D IconAt = P + FVector2D(12, (C.H - 52) / 2);
        if(V.Icon) Box(Out, Layer + 2, G, *V.Icon, IconAt, FVector2D(52), WithAlpha(V.Status == EStatus::Locked && V.bLockedIcon ? FLinearColor(.38f, .38f, .38f, 1) : FLinearColor::White, A));
        else if(!V.Glyph.IsEmpty())
        {
            Box(Out, Layer + 2, G, GlyphFrame, IconAt, FVector2D(52), Fill(GlyphFrame, A));
            Text(Out, Layer + 3, G, V.Glyph, TextFont(24 * .75f, true), WithAlpha(V.Status == EStatus::Locked ? Gray(120) : V.GlyphColor, A), IconAt + FVector2D(26, 26), .5f, .5f);
        }
        const float TextX = P.X + 12 + 52 + 12;
        Text(Out, Layer + 3, G, V.Name, F16, WithAlpha(V.Status == EStatus::Locked ? TextTertiary : TextPrimary, A), FVector2D(TextX, P.Y + 22));
        Text(Out, Layer + 3, G, V.State, TextFont(12 * .75f, V.bStateHighlight), WithAlpha(V.bStateHighlight ? (V.bStateGold ? HUDGoldLight : Accent) : TextTertiary, A), FVector2D(TextX, P.Y + 46));
        // side value: level / MAX / + / lock
        const FVector2D Right(P.X + C.W - 14, P.Y + C.H / 2 - 2);
        if(V.Status == EStatus::Available && V.Side.IsEmpty())
        {
            Box(Out, Layer + 2, G, BadgeBrush, Right - FVector2D(24, 12), FVector2D(24), WithAlpha(Accent, A));
            Text(Out, Layer + 3, G, TEXT("+"), NumberFont(18 * .75f, true), WithAlpha(Gray(20), A), Right - FVector2D(12, 0), .5f, .5f);
        }
        else if(V.Side.IsEmpty())
        {
            const FVector2D L0 = Right - FVector2D(14, 4); const FLinearColor Lc = WithAlpha(TextTertiary, A);
            Line(Out, Layer + 3, G, { L0, L0 + FVector2D(12, 0), L0 + FVector2D(12, 9), L0 + FVector2D(0, 9), L0 }, Lc, 1.4f);
            Line(Out, Layer + 3, G, { L0 + FVector2D(2.5f, 0), L0 + FVector2D(2.5f, -3.5f), L0 + FVector2D(6, -6), L0 + FVector2D(9.5f, -3.5f), L0 + FVector2D(9.5f, 0) }, Lc, 1.4f);
        }
        else
        {
            const FVector2D Small = V.SideSmall.IsEmpty() ? FVector2D::ZeroVector : Measure(V.SideSmall, F11);
            Text(Out, Layer + 3, G, V.SideSmall, F11, WithAlpha(TextTertiary, A), Right, 1.f, .2f);
            Text(Out, Layer + 3, G, V.Side, NumberFont(20 * .75f, true), WithAlpha(HUDGoldLight, A), Right - FVector2D(Small.X, 0), 1.f, .5f);
        }
        // bottom progress
        const FVector2D BarAt = P + FVector2D(12, C.H - 9), BarSize(C.W - 24, 3);
        Box(Out, Layer + 2, G, BarTrack, BarAt, BarSize, Fill(BarTrack, A));
        const FLinearColor BarColor = V.Status == EStatus::Locked ? Gray(222, 77) : V.Status == EStatus::Available ? Accent : V.Status == EStatus::Maxed ? HUDGoldLight : HUDGold;
        if(V.Progress > 0) Box(Out, Layer + 3, G, BarFill, BarAt, FVector2D(BarSize.X * FMath::Clamp(V.Progress, 0.f, 1.f), BarSize.Y), WithAlpha(BarColor, A));
        // tabs above the card (game-dev technology-card-prerequisite-gate / cross-prerequisite)
        auto Tab = [&](const FString& Str, bool bRight, const FLinearColor& Col)
        {
            if(Str.IsEmpty()) return;
            const FVector2D TextSize = Measure(Str, F11); const FVector2D TabSize(TextSize.X + 12, 19);
            const FVector2D At = bRight ? FVector2D(P.X + C.W - 8 - TabSize.X, P.Y - 19) : FVector2D(P.X + 8, P.Y - 19);
            Box(Out, Layer + 4, G, TabBrush, At, TabSize, Fill(TabBrush, A));
            Text(Out, Layer + 5, G, Str, F11, WithAlpha(Col, A), At + TabSize / 2, .5f, .5f);
        };
        Tab(V.TabRight, true, HUDGoldLight);
        Tab(V.TabLeft, false, V.bTabLeftMet ? HUDGoldLight : TextTertiary);
    }
    return Layer + 6;
}
