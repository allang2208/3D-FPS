#include "ColdSteelExplosiveWarnings.h"
#include "ColdSteelUIStyle.h"
#include "../Monsters/ExplosiveWarningSubsystem.h"
#include "../Monsters/BellowSacProjectile.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"
#include "Styling/CoreStyle.h"
#include "Layout/Geometry.h"
#include <initializer_list>

namespace
{
constexpr int32 MaxGroups = 8;
struct FWarningGroup
{
    const FExplosiveWarning* Threat = nullptr;
    FVector2D Point = FVector2D::ZeroVector;
    FVector2D Target = FVector2D::ZeroVector;
    int32 Count = 0;
};

// One bounded solid-geometry batch; no widget instances or texture loads in Paint.
class FWarningCanvas
{
public:
    FWarningCanvas(const FGeometry& InGeometry, FSlateWindowElementList& InElements,
        int32 InLayer, const FLinearColor& InTint, float InScale, int32 Groups)
        : Geometry(InGeometry), Elements(InElements), Layer(InLayer), Tint(InTint), S(InScale)
    {
        Vertices.Reserve(Groups * 640);
        Indices.Reserve(Groups * 2400);
    }

    void Polygon(std::initializer_list<FVector2D> Points, const FLinearColor& Color)
    {
        const int32 Start = Vertices.Num();
        for (const FVector2D& Point : Points) Vertex(Point, Color);
        for (int32 I = 1; I + 1 < static_cast<int32>(Points.size()); ++I)
            Triangle(Start, Start + I, Start + I + 1);
    }

    void Disk(const FVector2D& C, float Radius, const FLinearColor& Color, bool Sac = false)
    {
        constexpr int32 Segments = 32;
        const int32 Start = Vertices.Num();
        Vertex(C, Color);
        for (int32 I = 0; I <= Segments; ++I)
        {
            const float A = 2.f * PI * I / Segments;
            const FVector2D Unit(FMath::Cos(A), FMath::Sin(A));
            const float R = Radius * (Sac ? 1.f + .045f * FMath::Cos(A * 3.f) : 1.f);
            Vertex(C + Unit * R * S, Color);
            Vertex(C + Unit * (R + .8f) * S, Color.CopyWithNewOpacity(0.f));
            if (I == 0) continue;
            const int32 Previous = Start + 1 + (I - 1) * 2;
            const int32 Current = Previous + 2;
            Triangle(Start, Previous, Current);
            Quad(Previous, Previous + 1, Current, Current + 1);
        }
    }

    void Arc(const FVector2D& C, float Radius, float StartAngle, float Sweep,
        float Width, const FLinearColor& Color)
    {
        if (Sweep <= .001f) return;
        const int32 Segments = FMath::Max(2, FMath::CeilToInt(Sweep / (2.f * PI) * 48.f));
        const int32 Start = Vertices.Num();
        const float Half = Width * .5f;
        for (int32 I = 0; I <= Segments; ++I)
        {
            const float A = StartAngle + Sweep * I / Segments;
            const FVector2D Unit(FMath::Cos(A), FMath::Sin(A));
            Vertex(C + Unit * (Radius - Half - .8f) * S, Color.CopyWithNewOpacity(0.f));
            Vertex(C + Unit * (Radius - Half) * S, Color);
            Vertex(C + Unit * (Radius + Half) * S, Color);
            Vertex(C + Unit * (Radius + Half + .8f) * S, Color.CopyWithNewOpacity(0.f));
            if (I == 0) continue;
            const int32 Previous = Start + (I - 1) * 4;
            for (int32 Band = 0; Band < 3; ++Band)
                Quad(Previous + Band, Previous + Band + 1, Previous + Band + 4, Previous + Band + 5);
        }
    }

    void Bar(const FVector2D& A, const FVector2D& B, float Width, const FLinearColor& Color)
    {
        const FVector2D D = (B - A).GetSafeNormal();
        const FVector2D Side(-D.Y * Width * .5f * S, D.X * Width * .5f * S);
        Polygon({A + Side, B + Side, B - Side, A - Side}, Color);
    }

    void EdgeGlow(const FVector2D& C, const FVector2D& Tangent, const FVector2D& Inward,
        float HalfLength, float Depth, const FLinearColor& Color)
    {
        // Fade both along the edge and into the view, without a full-screen overlay.
        const int32 Start = Vertices.Num();
        for (int32 Row = 0; Row < 3; ++Row)
        {
            const float Fade = Row == 0 ? 1.f : (Row == 1 ? .3f : 0.f);
            for (int32 Column = 0; Column < 3; ++Column)
                Vertex(C + Tangent * (Column - 1) * HalfLength * S + Inward * Row * .5f * Depth * S,
                    Color.CopyWithNewOpacity(Column == 1 ? Color.A * Fade : 0.f));
        }
        for (int32 Row = 0; Row < 2; ++Row)
            for (int32 Column = 0; Column < 2; ++Column)
            {
                const int32 A = Start + Row * 3 + Column;
                Quad(A, A + 3, A + 1, A + 4);
            }
    }

    void Pill(const FVector2D& C, const FString& Value)
    {
        const auto Font = ColdSteelUI::NumberFont(14.f * .75f * S, true);
        const auto Measure = FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
        const FVector2D TextSize = Measure->Measure(Value, Font);
        const FVector2D Size = TextSize + FVector2D(12, 6) * S;
        const FVector2D Margin = Size * .5 + FVector2D(6.f * S, 6.f * S);
        const FVector2D View = Geometry.GetLocalSize();
        const FVector2D SafeCenter(
            FMath::Clamp(C.X, Margin.X, FMath::Max(Margin.X, View.X - Margin.X)),
            FMath::Clamp(C.Y, Margin.Y, FMath::Max(Margin.Y, View.Y - Margin.Y)));
        const auto Brush = ColdSteelUI::RoundedBrush(FLinearColor::White, 5.f * S,
            ColdSteelUI::Border * Tint, S);
        FSlateDrawElement::MakeBox(Elements, Layer + 1,
            Geometry.ToPaintGeometry(Size, FSlateLayoutTransform(SafeCenter - Size * .5)),
            &Brush, ESlateDrawEffect::None, ColdSteelUI::Content.CopyWithNewOpacity(.9f) * Tint);
        FSlateDrawElement::MakeText(Elements, Layer + 2,
            Geometry.ToPaintGeometry(TextSize, FSlateLayoutTransform(SafeCenter - TextSize * .5)),
            Value, Font, ESlateDrawEffect::None, ColdSteelUI::TextPrimary * Tint);
    }

    void Flush()
    {
        if (Vertices.IsEmpty()) return;
        const auto Resource = FSlateApplication::Get().GetRenderer()->GetResourceHandle(
            *FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")));
        FSlateDrawElement::MakeCustomVerts(Elements, Layer, Resource, Vertices, Indices, nullptr, 0, 0);
    }

private:
    void Vertex(const FVector2D& Point, const FLinearColor& Color)
    {
        Vertices.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(Geometry.GetAccumulatedRenderTransform(),
            FVector2f(Point), FVector2f(.5f, .5f), (Color * Tint).ToFColor(true)));
    }
    void Triangle(int32 A, int32 B, int32 C)
    { Indices.Append({SlateIndex(A), SlateIndex(B), SlateIndex(C)}); }
    void Quad(int32 A, int32 B, int32 C, int32 D)
    { Triangle(A, B, C); Triangle(C, B, D); }

    const FGeometry& Geometry;
    FSlateWindowElementList& Elements;
    int32 Layer;
    FLinearColor Tint;
    float S;
    TArray<FSlateVertex> Vertices;
    TArray<SlateIndex> Indices;
};

FLinearColor ThreatColor(const FExplosiveWarning& Threat, const ABellowSacProjectile& Projectile)
{
    if (!Threat.bExposed) return ColdSteelUI::TextSecondary;
    return Projectile.IsArmed() && Threat.Distance <= Projectile.GetBlastRadius()
        ? ColdSteelUI::Danger : ColdSteelUI::Warning;
}

float FusePulse(const ABellowSacProjectile& Projectile)
{
    if (!Projectile.IsArmed()) return 0.f;
    const float P = Projectile.FuseProgress();
    return .5f + .5f * FMath::Sin(2.f * PI * (P + P * P));
}

FString GroupLabel(const FWarningGroup& Group)
{
    FString Label = FString::Printf(TEXT("%.1fm"), Group.Threat->Distance * .01f);
    if (Group.Count > 1) Label += FString::Printf(TEXT(" ×%d"), Group.Count);
    return Label;
}
}

int32 ColdSteelExplosiveWarnings::Paint(APlayerController* PC, const FGeometry& Geometry,
    FSlateWindowElementList& Elements, int32 Layer, const FLinearColor& Tint)
{
    if (!PC || !PC->GetPawn() || !PC->PlayerCameraManager) return Layer;
    const auto* Registry = PC->GetWorld()->GetSubsystem<UExplosiveWarningSubsystem>();
    if (!Registry) return Layer;
    const auto& Warnings = Registry->ForPlayer(PC);
    if (Warnings.IsEmpty()) return Layer;

    const FVector2D View = Geometry.GetLocalSize(), Center = View * .5;
    if (View.X <= 0.f || View.Y <= 0.f) return Layer;
    const float DPI = FMath::Max(.1f, UWidgetLayoutLibrary::GetViewportScale(PC));
    const float S = FMath::Min(1.f / DPI, float(FMath::Min(View.X, View.Y)) / 240.f);
    const FVector2D EdgeExtent = Center - FVector2D(48.f, 48.f) * S;
    // The world badges retain their existing aiming clearance, independently of the edge arrows.
    const float ClearRadius = (FMath::Min(120.f, float(FMath::Min(View.X, View.Y)) / S * .18f) + 84.f) * S;
    const float FlightPulse = .5f + .5f * FMath::Sin(2.f * PI * 1.5f * PC->GetWorld()->GetTimeSeconds());
    const APlayerCameraManager* Camera = PC->PlayerCameraManager;
    const FVector Eye = Camera->GetCameraLocation();
    const FVector PlayerPosition = PC->GetPawn()->GetActorLocation();
    const FRotationMatrix BearingBasis(FRotator(0.f, Camera->GetCameraRotation().Yaw, 0.f));
    const FVector CameraForward = Camera->GetCameraRotation().Vector();
    const FGeometry Screen = UWidgetLayoutLibrary::GetPlayerScreenWidgetGeometry(PC);
    FWarningGroup Directions[MaxGroups], Markers[MaxGroups];
    int32 DirectionCount = 0, MarkerCount = 0;

    // Snapshots are already severity-sorted. Keep actual bearings continuous;
    // merge neighbours without the overlap/jump at fixed sector boundaries.
    for (const auto& Threat : Warnings)
    {
        const auto* Projectile = Threat.Projectile.Get();
        if (!Projectile || Projectile->IsSpent()) continue;
        const FVector Location = Projectile->GetActorLocation();
        const FVector Relative = Location - PlayerPosition;
        FVector2D Direction(FVector::DotProduct(Relative, BearingBasis.GetUnitAxis(EAxis::Y)),
            -FVector::DotProduct(Relative, BearingBasis.GetUnitAxis(EAxis::X)));
        if (!Direction.Normalize()) Direction = FVector2D(0, -1);
        int32 Match = INDEX_NONE;
        for (int32 I = 0; I < DirectionCount; ++I)
            if (FVector2D::DotProduct(Directions[I].Point, Direction) >= .8660254)
            { Match = I; break; }
        if (Match != INDEX_NONE) ++Directions[Match].Count;
        else if (DirectionCount < MaxGroups)
            Directions[DirectionCount++] = {&Threat, Direction, FVector2D::ZeroVector, 1};

        // A world marker denotes a visible screen position, never a mirrored
        // behind-camera projection. Rear/offscreen threats retain their bearing arrow.
        FVector2D Pixel = FVector2D::ZeroVector;
        if (FVector::DotProduct(Location - Eye, CameraForward) <= 1.f ||
            !PC->ProjectWorldLocationToScreen(Location, Pixel, true)) continue;
        const FVector2D Target = Geometry.AbsoluteToLocal(Screen.LocalToAbsolute(Pixel / DPI));
        if (Target.X < 0 || Target.Y < 0 || Target.X > View.X || Target.Y > View.Y) continue;
        FVector2D Point = Target - FVector2D(0, 54.f * S);
        FVector2D Offset = Point - Center;
        if (Offset.SizeSquared() < FMath::Square(ClearRadius))
        {
            if (!Offset.Normalize()) Offset = FVector2D(0, -1);
            Point = Center + Offset * ClearRadius;
        }
        Point.X = FMath::Clamp(Point.X, 42. * S, FMath::Max(42. * S, View.X - 42. * S));
        Point.Y = FMath::Clamp(Point.Y, 44. * S, FMath::Max(44. * S, View.Y - 70. * S));
        Match = INDEX_NONE;
        for (int32 I = 0; I < MarkerCount; ++I)
            if (FVector2D::DistSquared(Markers[I].Point, Point) < FMath::Square(88.f * S))
            { Match = I; break; }
        if (Match != INDEX_NONE) ++Markers[Match].Count;
        else if (MarkerCount < MaxGroups) Markers[MarkerCount++] = {&Threat, Point, Target, 1};
    }
    if (DirectionCount == 0 && MarkerCount == 0) return Layer;
    FWarningCanvas Canvas(Geometry, Elements, Layer + 1, Tint, S, DirectionCount + MarkerCount);
    const FLinearColor Ink = ColdSteelUI::Content.CopyWithNewOpacity(1.f);
    const FLinearColor White = ColdSteelUI::TextPrimary;

    // Draw the position markers first so the edge arrows remain prominent.
    for (int32 I = 0; I < MarkerCount; ++I)
    {
        const auto& Group = Markers[I];
        const auto* Projectile = Group.Threat->Projectile.Get();
        const FLinearColor Color = ThreatColor(*Group.Threat, *Projectile);
        const FVector2D C = Group.Point;
        const FVector2D ToTarget = Group.Target - C;
        // Stop the locator line outside the badge and before the aiming centre.
        if (ToTarget.SizeSquared() > FMath::Square(38.f * S))
        {
            const FVector2D A = C + ToTarget.GetSafeNormal() * 36.f * S;
            FVector2D B = Group.Target;
            const FVector2D Segment = B - A;
            const double T = FMath::Clamp(FVector2D::DotProduct(Center - A, Segment) / Segment.SizeSquared(), 0., 1.);
            const bool CrossesAim = FVector2D::DistSquared(A + Segment * T, Center) < FMath::Square(64.f * S);
            if (CrossesAim) B = A + Segment.GetSafeNormal() * FMath::Min(30.f * S, float(Segment.Size()));
            Canvas.Bar(A, B, 4.f, Ink.CopyWithNewOpacity(.8f));
            Canvas.Bar(A, B, 1.5f, Color);
            if (!CrossesAim) Canvas.Disk(Group.Target, 2.5f, Color);
        }
        Canvas.Disk(C, 35.f, Ink.CopyWithNewOpacity(.82f));
        Canvas.Arc(C, 34.f, 0.f, 2.f * PI, 1.5f, White.CopyWithNewOpacity(.8f));
        Canvas.Arc(C, 30.f, 0.f, 2.f * PI, 3.5f, ColdSteelUI::Gray(75));
        const float Remaining = Projectile->IsArmed() ? 1.f - Projectile->FuseProgress() : 1.f;
        Canvas.Arc(C, 30.f, -PI * .5f, 2.f * PI * Remaining, 3.5f, Color);
        if (Projectile->IsArmed())
            Canvas.Arc(C, 37.f + FusePulse(*Projectile) * 2.f, 0.f, 2.f * PI, 2.f,
                Color.CopyWithNewOpacity(.15f + .2f * FusePulse(*Projectile)));
        Canvas.Polygon({C + FVector2D(-4.5, -24) * S, C + FVector2D(4.5, -24) * S,
            C + FVector2D(4.5, -16) * S, C + FVector2D(-4.5, -16) * S}, White);
        Canvas.Disk(C + FVector2D(0, 2) * S, 20.5f, White, true);
        Canvas.Bar(C + FVector2D(0, -10) * S, C + FVector2D(0, 4) * S, 5.f, Ink);
        Canvas.Disk(C + FVector2D(0, 11) * S, 2.6f, Ink);
        Canvas.Pill(C + FVector2D(0, 51) * S, GroupLabel(Group));
    }

    for (int32 I = 0; I < DirectionCount; ++I)
    {
        const auto& Group = Directions[I];
        const auto* Projectile = Group.Threat->Projectile.Get();
        const FVector2D D = Group.Point, Side(-D.Y, D.X);
        // Intersect the horizontal bearing with the inset viewport rectangle.
        // Forward is top, rear is bottom; camera pitch and screen projection do not change this.
        const double BoundaryScale = FMath::Max(FMath::Abs(D.X) / EdgeExtent.X,
            FMath::Abs(D.Y) / EdgeExtent.Y);
        const FVector2D C = Center + D / BoundaryScale;
        const bool VerticalEdge = FMath::Abs(D.X) * EdgeExtent.Y > FMath::Abs(D.Y) * EdgeExtent.X;
        const FVector2D Outward = VerticalEdge ? FVector2D(FMath::Sign(D.X), 0.f)
            : FVector2D(0.f, FMath::Sign(D.Y));
        const FVector2D Tangent(-Outward.Y, Outward.X);
        const FVector2D EdgePoint = VerticalEdge
            ? FVector2D(D.X > 0.f ? View.X - 4.f * S : 4.f * S, C.Y)
            : FVector2D(C.X, D.Y > 0.f ? View.Y - 4.f * S : 4.f * S);
        const float EdgeSpace = float(VerticalEdge ? FMath::Min(C.Y, View.Y - C.Y)
            : FMath::Min(C.X, View.X - C.X)) / S - 6.f;
        const FLinearColor Color = ThreatColor(*Group.Threat, *Projectile);
        const bool Exposed = Group.Threat->bExposed;
        const bool Critical = Exposed && Projectile->IsArmed() && Group.Threat->Distance <= Projectile->GetBlastRadius();
        const float Pulse = Exposed ? (Projectile->IsArmed() ? FusePulse(*Projectile) : FlightPulse) : 0.f;
        const float Urgency = Exposed && Projectile->IsArmed() ? Projectile->FuseProgress() : 0.f;
        const FLinearColor Border = Exposed ? ColdSteelUI::Danger : ColdSteelUI::TextSecondary;
        const float HalfLength = FMath::Min(76.f + 12.f * Pulse, EdgeSpace);
        Canvas.EdgeGlow(EdgePoint, Tangent, -Outward, HalfLength, 48.f + 16.f * Urgency,
            Border.CopyWithNewOpacity(Exposed ? .14f + .16f * Pulse + (Critical ? .1f : 0.f) : .04f));
        const FVector2D Band = Tangent * HalfLength * .6f * S;
        Canvas.Bar(EdgePoint - Band, EdgePoint + Band, 3.f + 2.f * Pulse,
            Border.CopyWithNewOpacity(Exposed ? .55f + .4f * Pulse : .18f));
        Canvas.Disk(C, 28.f, Ink.CopyWithNewOpacity(.86f));
        const auto Chevron = [&](float Size, const FLinearColor& Fill)
        {
            Canvas.Polygon({C + D * 18.f * S * Size,
                C - D * 12.f * S * Size + Side * 17.f * S * Size,
                C - D * 4.f * S * Size,
                C - D * 12.f * S * Size - Side * 17.f * S * Size}, Fill);
        };
        Chevron(1.45f, Ink);
        // Keep a visible red outline between flashes; the solid arrow never blinks out.
        Chevron(1.25f + .04f * Pulse, Border.CopyWithNewOpacity(Exposed ? .65f + .35f * Pulse : .45f));
        Chevron(1.f, White);
        Chevron(.8f, Color);
        Canvas.Pill(C - D * 44.f * S, GroupLabel(Group));
    }
    Canvas.Flush();
    return Layer + 4;
}
