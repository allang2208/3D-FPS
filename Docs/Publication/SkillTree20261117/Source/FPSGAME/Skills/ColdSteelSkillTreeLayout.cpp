#include "ColdSteelSkillTreeLayout.h"

namespace ColdSteelSkillTreeLayout
{
using namespace ColdSteelSkillTree;
namespace
{
    struct FTarget { FVector2D At; bool bGate = false; };
    struct FGateGeo { FName Id, To; int32 Requirement = 0; float GX = 0, GY = 0, InX = 0; TArray<int32> Ins; };
}

FResult Build(const TArray<FRow>& Rows, const FConfig& C)
{
    FResult R; R.Config = C;
    int32 Lane = 0;
    for(const FRow& Row : Rows)
    {
        FBand Band; Band.Key = Row.Key; Band.Name = Row.Name; Band.Note = Row.Note; Band.Group = Row.Group; Band.Lane = Lane; Band.Span = Row.Lanes;
        for(const FItem& It : Row.Items)
        {
            FCard Card; Card.Id = It.Id; Card.Column = It.Column; Card.Lane = Lane + It.Lane;
            Card.Pos = FVector2D(C.OX + It.Column * (C.W + C.Gap), C.OY + Card.Lane * (C.H + C.LaneGap));
            R.CardIndex.Add(It.Id, R.Cards.Add(Card)); Band.Items.Add(It.Id);
        }
        R.Bands.Add(MoveTemp(Band)); Lane += Row.Lanes;
    }
    TArray<FGateGeo> GateGeo;
    for(const FRow& Row : Rows) for(const FItem& It : Row.Items) for(int32 Ri = 0; Ri < It.Requires.Num(); ++Ri)
    {
        const FRequirement& Q = It.Requires[Ri];
        if(Q.Kind == EReqKind::Skill)
        {
            if(R.CardIndex.Contains(Q.Skills[0])) R.Entries.Add({ Q.Skills[0], It.Id, Ri, NAME_None });
            else R.Badges.Add({ It.Id, Ri });
        }
        else if(Q.Kind == EReqKind::AnyOf)
        {
            TArray<FName> Visible; for(FName Id : Q.Skills) if(R.CardIndex.Contains(Id)) Visible.Add(Id);
            if(Q.bCrossBranch || Visible.IsEmpty()) { R.Badges.Add({ It.Id, Ri }); continue; }
            const FName Gate(*FString::Printf(TEXT("%s:%d"), *It.Id.ToString(), Ri));
            FGateGeo G; G.Id = Gate; G.To = It.Id; G.Requirement = Ri;
            const FVector2D B = R.Card(It.Id)->Pos; G.GY = B.Y + C.H / 2; G.GX = B.X - 40; G.InX = B.X - 62;
            for(FName Id : Visible) { G.Ins.Add(R.Entries.Num()); R.Entries.Add({ Id, It.Id, Ri, Gate }); }
            GateGeo.Add(MoveTemp(G));
        }
        else R.Badges.Add({ It.Id, Ri });
    }
    const auto P = [&R](FName Id) { return *R.Card(Id); };
    const auto MidY = [&](FName Id) { return P(Id).Pos.Y + C.H / 2; };
    const auto Delta = [&](const FEntry& E) { return P(E.To).Column - P(E.From).Column; };
    // Same-lane long links stack on gutter tracks below the source, nearest target first.
    TMap<int32,int32> SameLaneIndex; TMap<FName,TArray<int32>> BySource; TArray<FName> SourceOrder;
    for(int32 I = 0; I < R.Entries.Num(); ++I) { if(!BySource.Contains(R.Entries[I].From)) SourceOrder.Add(R.Entries[I].From); BySource.FindOrAdd(R.Entries[I].From).Add(I); }
    for(const auto& Pair : BySource)
    {
        TArray<int32> Same; for(int32 I : Pair.Value) if(Delta(R.Entries[I]) > 1 && P(R.Entries[I].To).Lane == P(R.Entries[I].From).Lane) Same.Add(I);
        Same.Sort([&](int32 A, int32 B) { return P(R.Entries[A].To).Column < P(R.Entries[B].To).Column; });
        for(int32 K = 0; K < Same.Num(); ++K) SameLaneIndex.Add(Same[K], K);
    }
    const auto GutterY = [&](int32 I)
    {
        const FCard A = P(R.Entries[I].From), B = P(R.Entries[I].To);
        if(B.Lane == A.Lane) return A.Pos.Y + C.H + 12 + 10 * SameLaneIndex.FindRef(I);
        if(B.Lane > A.Lane) return B.Pos.Y - C.LaneGap / 2;
        return A.Pos.Y - 12;
    };
    const auto Approach = [&](int32 I) { return Delta(R.Entries[I]) > 1 ? GutterY(I) : MidY(R.Entries[I].From); };
    // Ports: distributed on the card's left edge, or on the gate's input column; ordered by approach height.
    TMap<FString,TArray<int32>> Groups; TArray<FString> GroupOrder;
    for(int32 I = 0; I < R.Entries.Num(); ++I)
    {
        const FString Key = R.Entries[I].Gate.IsNone() ? TEXT("c:") + R.Entries[I].To.ToString() : TEXT("g:") + R.Entries[I].Gate.ToString();
        if(!Groups.Contains(Key)) GroupOrder.Add(Key); Groups.FindOrAdd(Key).Add(I);
    }
    TMap<int32,FTarget> Target;
    for(const FString& Key : GroupOrder)
    {
        TArray<int32>& List = Groups[Key];
        List.StableSort([&](int32 A, int32 B) { const float Da = Approach(A), Db = Approach(B); return Da != Db ? Da < Db : P(R.Entries[A].From).Column > P(R.Entries[B].From).Column; });
        if(Key.StartsWith(TEXT("g:")))
        {
            const FGateGeo* G = GateGeo.FindByPredicate([&](const FGateGeo& X) { return X.Id == R.Entries[List[0]].Gate; });
            const float Spacing = FMath::Min(12.f, 40.f / FMath::Max(1, List.Num() - 1));
            for(int32 K = 0; K < List.Num(); ++K) Target.Add(List[K], { FVector2D(G->InX, G->GY + (K - (List.Num() - 1) / 2.f) * Spacing), true });
        }
        else
        {
            const FVector2D B = P(R.Entries[List[0]].To).Pos;
            for(int32 K = 0; K < List.Num(); ++K) Target.Add(List[K], { FVector2D(B.X, B.Y + C.H * (K + 1) / (List.Num() + 1)), false });
        }
    }
    // Sources with 2+ targets draw one bus: a short stub, then a vertical trunk the branches leave from.
    TMap<int32,float> Track; TMap<FName,float> BusX;
    for(FName Src : SourceOrder)
    {
        const TArray<int32>& List = BySource[Src];
        const float SX = P(Src).Pos.X + C.W, SY = MidY(Src);
        float Top = SY, Bottom = SY;
        for(int32 I : List) { const float T = Delta(R.Entries[I]) > 1 ? GutterY(I) : Target[I].At.Y; Track.Add(I, T); Top = FMath::Min(Top, T); Bottom = FMath::Max(Bottom, T); }
        if(List.Num() < 2) continue;
        const float BX = SX + 10; BusX.Add(Src, BX);
        FBus Bus; Bus.From = Src; Bus.Entries = List; Bus.Stub = { FVector2D(SX, SY), FVector2D(BX, SY) }; Bus.Trunk = { FVector2D(BX, Top), FVector2D(BX, Bottom) };
        R.Buses.Add(MoveTemp(Bus));
        R.Junctions.Add({ Src, FVector2D(BX, SY), List });
        for(int32 I : List) if(!FMath::IsNearlyEqual(Track[I], SY)) R.Junctions.Add({ Src, FVector2D(BX, Track[I]), { I } });
    }
    // Arrival verticals sit in the target-side half of the column gap: rising links to upper ports
    // turn first, falling links to lower ports turn first, so no two arrivals cross.
    TMap<int32,float> ArrivalX;
    for(const FString& Key : GroupOrder)
    {
        TArray<int32> Up, Down;
        for(int32 I : Groups[Key])
        {
            const float Ap = (BusX.Contains(R.Entries[I].From) || Delta(R.Entries[I]) > 1) ? Track[I] : MidY(R.Entries[I].From);
            const float Ty = Target[I].At.Y;
            if(FMath::Abs(Ap - Ty) <= .5f) continue;
            (Ap > Ty ? Up : Down).Add(I);
        }
        Up.Sort([&](int32 A, int32 B) { return Target[A].At.Y < Target[B].At.Y; });
        Down.Sort([&](int32 A, int32 B) { return Target[A].At.Y > Target[B].At.Y; });
        TArray<int32> Order = Up; Order.Append(Down);
        if(Order.IsEmpty()) continue;
        const bool bGate = Key.StartsWith(TEXT("g:"));
        const float TX = Target[Order[0]].At.X, Zone = bGate ? FMath::Max(6.f, C.Gap - 62 - 16) : C.Gap / 2 - 8;
        for(int32 K = 0; K < Order.Num(); ++K) ArrivalX.Add(Order[K], TX - (bGate ? 4 : 8) - Zone * float(Order.Num() - K) / Order.Num());
    }
    for(int32 I = 0; I < R.Entries.Num(); ++I)
    {
        const FEntry& E = R.Entries[I]; const FTarget& T = Target[I];
        const float SX = P(E.From).Pos.X + C.W, SY = MidY(E.From), Tr = Track[I];
        const float* AX = ArrivalX.Find(I);
        FLink L; L.Entry = I; L.bArrow = !T.bGate;
        TArray<FVector2D> Head;
        if(const float* BX = BusX.Find(E.From))
        {
            Head = { FVector2D(SX, SY), FVector2D(*BX, SY) };
            L.Points.Add(FVector2D(*BX, Tr));
        }
        else
        {
            L.Points.Add(FVector2D(SX, SY));
            if(Delta(E) > 1) { const float DX = SX + C.Gap / 3; L.Points.Add(FVector2D(DX, SY)); L.Points.Add(FVector2D(DX, Tr)); }
        }
        if(AX) { L.Points.Add(FVector2D(*AX, L.Points.Last().Y)); L.Points.Add(FVector2D(*AX, T.At.Y)); }
        L.Points.Add(FVector2D(T.At.X, L.Points.Last().Y));
        // Label on the longest horizontal run.
        float Best = -1;
        for(int32 K = 1; K < L.Points.Num(); ++K)
            if(FMath::IsNearlyEqual(L.Points[K].Y, L.Points[K - 1].Y))
            { const float Len = FMath::Abs(L.Points[K].X - L.Points[K - 1].X); if(Len > Best) { Best = Len; L.Label = FVector2D((L.Points[K].X + L.Points[K - 1].X) / 2, L.Points[K].Y - 7); L.bHasLabel = true; } }
        L.FullPoints = Head; L.FullPoints.Append(L.Points);
        R.Links.Add(MoveTemp(L));
        if(T.bGate) R.Ports.Add({ I, T.At });
    }
    for(const FGateGeo& G : GateGeo)
    {
        FGate Gate; Gate.Id = G.Id; Gate.To = G.To; Gate.Requirement = G.Requirement; Gate.Center = FVector2D(G.GX, G.GY); Gate.Inputs = G.Ins;
        Gate.Output = { FVector2D(G.GX + 22, G.GY), FVector2D(P(G.To).Pos.X, G.GY) };
        R.Gates.Add(MoveTemp(Gate));
    }
    R.Size = FVector2D(C.OX + C.Columns * (C.W + C.Gap) - C.Gap + 40, C.OY + Lane * (C.H + C.LaneGap) - C.LaneGap + 36);
    return R;
}
}
