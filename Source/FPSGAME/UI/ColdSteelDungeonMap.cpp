#include "ColdSteelDungeonMap.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Algo/Reverse.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"

namespace
{
    constexpr double TileSize = 200.;
    constexpr double BinSize = 1600.;

    FIntPoint Grid(FVector2D P, double Size)
    {
        return {FMath::FloorToInt32(P.X / Size), FMath::FloorToInt32(P.Y / Size)};
    }

    int32 DeckOffset(double Z, double Base)
    {
        const int32 Offset=FDungeonRunNode::FloorAtElevation(Z,Base);
        // Some authored decks have a full storey of clearance but are less than half
        // the 540 cm module spacing (e.g. the 240 cm gallery in the generator hall).
        if (Offset==0 && FMath::Abs(Z-Base)>=200.) return Z>Base?1:-1;
        return Offset;
    }

    bool IsAuthoredDeckSupport(const UPrimitiveComponent* Component)
    {
        const auto* Mesh=Cast<UStaticMeshComponent>(Component);
        if (!Mesh || !Mesh->GetStaticMesh()) return false;
        const FString Name=Mesh->GetStaticMesh()->GetName();
        return Name.EndsWith(TEXT("_Platforms")) || Name.EndsWith(TEXT("_BridgeDecks")) ||
            Name.EndsWith(TEXT("_GalleryDeck")) || Name.EndsWith(TEXT("_Stairs"));
    }

    bool IsAboveSameDeck(const APawn& Pawn,const UPrimitiveComponent& Support,FVector At,const FBox2D& Rect)
    {
        const FVector2D Points[]={Rect.GetCenter(),Rect.Min,Rect.Max,
            {Rect.Min.X,Rect.Max.Y},{Rect.Max.X,Rect.Min.Y}};
        const FCollisionQueryParams Query(SCENE_QUERY_STAT(DungeonMapDeck),false,&Pawn);
        for (FVector2D XY : Points)
        {
            FHitResult Hit;
            const FVector Top(XY,At.Z+30.),Bottom(XY,At.Z-35.);
            if (!Pawn.GetWorld()->LineTraceSingleByChannel(Hit,Top,Bottom,ECC_Pawn,Query) ||
                Hit.GetComponent()!=&Support || Hit.ImpactNormal.Z<.65) return false;
        }
        return true;
    }

    // The sweep covers the whole rectangle on the way from the player. A thin or
    // oblique leaf through a corner therefore blocks it even if its centre is visible.
    bool IsPatchClear(const APawn& Pawn,FVector Feet,const FBox2D& Rect)
    {
        const double HalfHeight=FMath::Max(12.,double(Pawn.GetSimpleCollisionHalfHeight()));
        const FVector Start(Feet.X,Feet.Y,Feet.Z+HalfHeight);
        const FVector End(Rect.GetCenter(),Start.Z);
        // Slice at torso height so a support ramp does not occlude its own map.
        const FVector Extent(Rect.GetExtent(),8.);
        const FCollisionShape Shape=FCollisionShape::MakeBox(Extent);
        const FCollisionQueryParams Query(SCENE_QUERY_STAT(DungeonMapReveal),false,&Pawn);
        const UWorld* World=Pawn.GetWorld();
        for (ECollisionChannel Channel : {ECC_Visibility,ECC_Pawn})
        {
            if (World->OverlapBlockingTestByChannel(Start,FQuat::Identity,Channel,Shape,Query) ||
                World->SweepTestByChannel(Start,End,FQuat::Identity,Channel,Shape,Query)) return false;
        }
        return true;
    }
}

void FColdSteelDungeonMap::FRamp::SetPath(const TArray<FVector>& Anchors,FVector Low,FVector High)
{
    if (Anchors.Num()<2) return;
    const bool bReverse=Anchors[0].Equals(High,2.) && Anchors.Last().Equals(Low,2.);
    if (!bReverse && !(Anchors[0].Equals(Low,2.) && Anchors.Last().Equals(High,2.))) return;
    Path=Anchors;
    if (bReverse) Algo::Reverse(Path);
    Distance.Add(0.);
    for (int32 I=1; I<Path.Num(); ++I) Distance.Add(Distance.Last()+FVector::Distance(Path[I],Path[I-1]));
}

double FColdSteelDungeonMap::FRamp::Project(FVector At,double& Along) const
{
    double Best=DBL_MAX;
    for (int32 I=1; I<Path.Num(); ++I)
    {
        const FVector Delta=Path[I]-Path[I-1];
        const double LengthSquared=Delta.SizeSquared();
        if (LengthSquared<1.) continue;
        const double T=FMath::Clamp(FVector::DotProduct(At-Path[I-1],Delta)/LengthSquared,0.,1.);
        const double Squared=FVector::DistSquared(At,Path[I-1]+T*Delta);
        if (Squared<Best)
        {
            Best=Squared;
            Along=FMath::Lerp(Distance[I-1],Distance[I],T);
        }
    }
    return FMath::Sqrt(Best);
}

void FColdSteelDungeonMapFloor::ForEachVisiblePatch(const FBox2D& View,TFunctionRef<void(const FColdSteelDungeonPatch&)> Draw) const
{
    if (!Bounds.Intersect(View)) return;
    const FIntPoint Min=Grid(FVector2D::Max(Bounds.Min,View.Min),TileSize);
    const FIntPoint Max=Grid(FVector2D::Min(Bounds.Max,View.Max),TileSize);
    const int64 SpanX=int64(Max.X)-Min.X+1, SpanY=int64(Max.Y)-Min.Y+1;
    if (SpanX*SpanY < Tiles.Num())
    {
        for (int32 X=Min.X; X<=Max.X; ++X)
            for (int32 Y=Min.Y; Y<=Max.Y; ++Y)
                if (const auto* Indices=Tiles.Find({X,Y}))
                    for (int32 I : *Indices) Draw(Patches[I]);
        return;
    }
    for (const auto& Tile : Tiles)
        for (int32 I : Tile.Value)
            if (Patches[I].Bounds.Intersect(View)) Draw(Patches[I]);
}

FString FColdSteelDungeonMap::FloorName(int32 Floor)
{
    if (Floor == 0) return TEXT("入口层");
    if (Floor > 0) return FString::Printf(TEXT("上 %d 层"),Floor);
    return FString::Printf(TEXT("地下 %d 层"),-Floor);
}

void FColdSteelDungeonMap::ResetExploration()
{
    const uint32 NextLayout = LayoutSerial+1;
    const auto Player=Owner;
    *this = FColdSteelDungeonMap();
    LayoutSerial = NextLayout;
    Owner=Player;
}

void FColdSteelDungeonMap::PauseSampling()
{
    SamplingPawn.Reset();
    LastSample=FVector(UE_DOUBLE_BIG_NUMBER);
    LastSupport.Reset();
    LastFootprint=INDEX_NONE;
    RetryBlockedAt=0.;
    PlayerArea.Reset();
}

bool FColdSteelDungeonMap::Update(APlayerController* Player)
{
    if (!Player || !Player->IsLocalController()) return false;
    // A menu belongs to one controller. A remote pawn or another local player's menu
    // cannot contribute exploration to this session.
    if (!Owner.IsExplicitlyNull() && Owner.Get()!=Player) return false;
    Owner=Player;
    auto* Run=UDungeonRunSubsystem::Get(Player->GetWorld());
    ULevel* Level=Run?Run->MapLevel():nullptr;
    if (!Level)
    {
        if (!RunId.IsEmpty()) ResetExploration();
        PauseSampling();
        return false;
    }
    if (Source.Get()!=Run || RunId!=Run->RunId() || BoundLevel.Get()!=Level) Bind(*Run);
    APawn* Pawn=Player->GetPawn();
    const auto* State=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    if (!Pawn || Pawn->GetController()!=Player || !UDungeonRoomSubsystem::IsDungeonPawn(Pawn) ||
        (State && State->RoomTransferToken.IsValid()))
    {
        PauseSampling();
        return false;
    }
    if (SamplingPawn.Get()!=Pawn) PauseSampling();
    SamplingPawn=Pawn;
    Record(*Pawn);
    return true;
}

void FColdSteelDungeonMap::Bind(UDungeonRunSubsystem& Run)
{
    ResetExploration();
    Source = &Run;
    BoundLevel=Run.MapLevel();
    RunId = Run.RunId();
    auto Add = [this](const FBox& Box, int32 Node, int32 Floor, double Z, bool bPassage, bool bFallback,FName ModuleTag)
    {
        if (!Box.IsValid || Box.Min.X >= Box.Max.X || Box.Min.Y >= Box.Max.Y) return;
        const int32 Index = Footprints.Add({Box, Node, Floor, Z, bPassage, bFallback,ModuleTag});
        const FIntPoint Min = Grid(FVector2D(Box.Min), BinSize), Max = Grid(FVector2D(Box.Max), BinSize);
        for (int32 X = Min.X; X <= Max.X; ++X)
            for (int32 Y = Min.Y; Y <= Max.Y; ++Y)
                SpatialBins.FindOrAdd({X,Y}).Add(Index);
    };

    // The fixed spawn room is outside the generated node graph.
    Add(Run.StartRoomBounds(), INDEX_NONE, 0, Run.EntryPosition().Z, false, true,NAME_None);
    for (const FDungeonRunNode& Node : Run.AllNodes())
    {
        if (Node.Id == INDEX_NONE || !Node.Volume.IsValid) continue;
        const FName ModuleTag(*FString::Printf(TEXT("DungeonModule.%d.%s"),Node.Id,*Node.Module));
        if (Node.bConnector && Node.Doors.Num() == 2)
        {
            const double A = Node.Doors[0].FloorCenter.Z, B = Node.Doors[1].FloorCenter.Z;
            const int32 Low = FDungeonRunNode::FloorAtElevation(FMath::Min(A,B), Run.EntryPosition().Z);
            const int32 High = FDungeonRunNode::FloorAtElevation(FMath::Max(A,B), Run.EntryPosition().Z);
            if (Low != High)
            {
                auto& Ramp=Ramps.Add(Node.Id);
                Ramp.MiddleZ=(A+B)*.5;
                Ramp.Lower=Low;
                Ramp.Upper=High;
                Ramp.HalfWidth=FMath::Max(Node.Doors[0].Width,Node.Doors[1].Width)*.5;
                Ramp.SetPath(Node.NavigationAnchors,Node.Doors[A<B?0:1].FloorCenter,Node.Doors[A<B?1:0].FloorCenter);
            }
        }
        if (!Node.bConnector) for (const FVector& Anchor : Node.NavigationAnchors)
        {
            const int32 Offset=DeckOffset(Anchor.Z,Node.Origin.Z);
            if (Offset!=0) DeckAnchors.FindOrAdd(Node.Id).Add({Anchor,Node.Floor+Offset});
        }
        // Walk masks carry authored floor and balcony heights. Occupancy boxes cover the remaining
        // playable doorways, stairs and modules that have no walk mask; only record footsteps there.
        for (const FBox& Box : Node.WalkCells)
        {
            const int32 Floor = Node.Floor + DeckOffset(Box.Min.Z,Node.Origin.Z);
            Add(Box,Node.Id,Floor,Box.Min.Z,Node.bConnector,false,ModuleTag);
        }
        auto AddOccupancy = [&](const FBox& Box)
        {
            Add(Box,Node.Id,Node.Floor,FMath::Clamp(Node.Origin.Z,Box.Min.Z,Box.Max.Z),Node.bConnector,true,ModuleTag);
        };
        if (Node.Cells.IsEmpty()) AddOccupancy(Node.Volume);
        else for (const FBox& Box : Node.Cells) AddOccupancy(Box);
    }
}

int32 FColdSteelDungeonMap::FindFootprint(FVector At,const UPrimitiveComponent* Support) const
{
    const auto* Candidates = SpatialBins.Find(Grid(FVector2D(At), BinSize));
    if (!Candidates) return INDEX_NONE;
    const bool bSharedMesh=Support && Support->IsA<UInstancedStaticMeshComponent>();
    int32 Best = INDEX_NONE;
    double BestScore = DBL_MAX;
    for (int32 Index : *Candidates)
    {
        const FFootprint& Part = Footprints[Index];
        const FBox& B = Part.Box;
        if (At.X < B.Min.X || At.X > B.Max.X || At.Y < B.Min.Y || At.Y > B.Max.Y ||
            At.Z < B.Min.Z-24. || At.Z > B.Max.Z+30.) continue;
        const double Height = FMath::Abs(At.Z-Part.GroundZ);
        // The manifest extends walk masks up to the room ceiling. A lower mask cannot
        // identify the player on an overpass. Prefer a matching authored surface.
        double Score = Height + (Part.bFallback ? 70. : 0.);
        if (const auto* Ramp=Ramps.Find(Part.Node); Ramp && !Ramp->Path.IsEmpty())
        {
            double Along=0.;
            // The bounding volume of the triple-flight stair includes both overlapping flights.
            Score=FMath::Max(0.,Ramp->Project(At,Along)-Ramp->HalfWidth);
        }
        if (Support && !Part.ModuleTag.IsNone() && (bSharedMesh ? Support->ComponentHasTag(Part.ModuleTag) :
            (Support->GetOwner() && Support->GetOwner()->ActorHasTag(Part.ModuleTag)))) Score-=10000.;
        if (Index==LastFootprint) Score-=.1;
        if (Score < BestScore) { Best = Index; BestScore = Score; }
    }
    return Best;
}

int32 FColdSteelDungeonMap::FloorFor(int32 Index, FVector At,const UPrimitiveComponent* Support) const
{
    const FFootprint& Part = Footprints[Index];
    if (const FRamp* Ramp = Ramps.Find(Part.Node))
    {
        if (Ramp->Path.IsEmpty()) return At.Z > Ramp->MiddleZ ? Ramp->Upper : Ramp->Lower;
        double Along=0.;
        Ramp->Project(At,Along);
        const double FromMiddle=Along-Ramp->Distance.Last()*.5;
        if (Support && Footprints.IsValidIndex(LastFootprint) && Footprints[LastFootprint].Node==Part.Node &&
            FMath::Abs(FromMiddle)<=12.) return PlayerFloor;
        return FromMiddle>0. ? Ramp->Upper : Ramp->Lower;
    }
    // Some mezzanines have navigation anchors but no separate walk mask. Confirm a
    // matching authored elevation so standing on a crate cannot unlock a new floor.
    if ((Part.bFallback || FMath::Abs(At.Z-Part.GroundZ)>=180.) && Part.Node!=INDEX_NONE)
    {
        if (const auto* Anchors=DeckAnchors.Find(Part.Node))
        {
            if (Support && !IsAuthoredDeckSupport(Support)) return Part.Floor;
            double Best=60.;
            int32 Floor=Part.Floor;
            for (const auto& Anchor : *Anchors)
            {
                const double Difference=FMath::Abs(At.Z-Anchor.Point.Z);
                if (Difference<Best && (Support || FVector::DistSquared2D(At,Anchor.Point)<=FMath::Square(140.)))
                {
                    Best=Difference;
                    Floor=Anchor.Floor;
                }
            }
            return Floor;
        }
    }
    return Part.Floor;
}

int32 FColdSteelDungeonMap::LandmarkFloor(FVector At) const
{
    const int32 Index = FindFootprint(At);
    if (Index != INDEX_NONE) return FloorFor(Index, At);
    return Source.IsValid() ? FDungeonRunNode::FloorAtElevation(At.Z,Source->EntryPosition().Z) : 0;
}

bool FColdSteelDungeonMap::IsKnown(FVector2D Point, int32 Floor) const
{
    const auto* Layer = Layers.Find(Floor);
    const auto* Indices = Layer ? Layer->Tiles.Find(Grid(Point,TileSize)) : nullptr;
    if (Indices)
        for (int32 I : *Indices)
            if (Layer->Patches[I].Bounds.IsInsideOrOn(Point)) return true;
    return false;
}

bool FColdSteelDungeonMap::IsLandmarkKnown(FVector At, int32 Floor) const
{
    if (!Source.IsValid()) return false;
    const auto* Layer = Layers.Find(Floor);
    const FVector2D XY(At);
    const auto* Indices = Layer ? Layer->Tiles.Find(Grid(XY,TileSize)) : nullptr;
    if (!Indices) return false;
    const int32 Part = FindFootprint(At);
    if (Part == INDEX_NONE || FloorFor(Part,At)!=Floor) return false;
    for (int32 I : *Indices)
    {
        const auto& Patch = Layer->Patches[I];
        if (Footprints[Patch.Footprint].Node==Footprints[Part].Node && Patch.Bounds.IsInsideOrOn(XY) &&
            FloorFor(Patch.Footprint,At)==Floor)
            return true;
    }
    return false;
}

bool FColdSteelDungeonMap::MarkerGround(APawn& Viewer,FVector2D Point,int32 Floor,FVector& Position) const
{
    const auto* Layer=Layers.Find(Floor);
    const auto* Indices=Layer?Layer->Tiles.Find(Grid(Point,TileSize)):nullptr;
    if (!Indices || !BoundLevel.IsValid()) return false;
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic);
    Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(DungeonMarkerGround),false,&Viewer);
    double Best=DBL_MAX;
    for (int32 I:*Indices)
    {
        const auto& Patch=Layer->Patches[I];
        if (!Patch.Bounds.IsInsideOrOn(Point)) continue;
        TArray<FHitResult> Hits;
        // Start close to the observed walk surface, never above the whole stacked building.
        Viewer.GetWorld()->LineTraceMultiByObjectType(Hits,FVector(Point,Patch.GroundZ+160.),
            FVector(Point,Patch.GroundZ-160.),Objects,Query);
        for (const auto& Hit:Hits)
        {
            if (!Hit.GetActor() || Hit.GetActor()->GetLevel()!=BoundLevel.Get() || Hit.ImpactNormal.Z<.5) continue;
            const int32 Part=FindFootprint(Hit.ImpactPoint,Hit.GetComponent());
            if (Part==INDEX_NONE || Footprints[Part].Node!=Footprints[Patch.Footprint].Node ||
                FloorFor(Part,Hit.ImpactPoint,Hit.GetComponent())!=Floor) continue;
            const double Distance=FMath::Abs(Hit.ImpactPoint.Z-Patch.GroundZ);
            if (Distance<Best) { Best=Distance; Position=Hit.ImpactPoint; }
        }
    }
    return Best<DBL_MAX;
}

bool FColdSteelDungeonMap::Reveal(FIntPoint Tile, int32 Index, int32 Floor, const FBox2D& Rect,double GroundZ)
{
    auto& Layer = Layers.FindOrAdd(Floor);
    auto& Indices = Layer.Tiles.FindOrAdd(Tile);
    // A door may have opened since a tile was partially recorded. Reuse a smaller
    // patch and retire its siblings from the live tile index when promoting it.
    int32 Reuse=INDEX_NONE;
    for (int32 I=Indices.Num()-1; I>=0; --I)
    {
        auto& Patch=Layer.Patches[Indices[I]];
        if (Patch.Footprint==Index && Rect.IsInsideOrOn(Patch.Bounds.Min) && Rect.IsInsideOrOn(Patch.Bounds.Max))
        {
            if (Reuse==INDEX_NONE) Reuse=Indices[I];
            else Indices.RemoveAtSwap(I);
        }
    }
    if (GroundZ==UE_DOUBLE_BIG_NUMBER) GroundZ=Footprints[Index].GroundZ;
    if (Reuse==INDEX_NONE) Indices.Add(Layer.Patches.Add({Rect, Index, Footprints[Index].bPassage, GroundZ}));
    else Layer.Patches[Reuse].Bounds=Rect;
    Layer.Bounds += Rect;
    return true;
}

void FColdSteelDungeonMap::Record(APawn& Pawn)
{
    FVector At = Pawn.GetNavAgentLocation();
    const UPrimitiveComponent* Support=nullptr;
    if (const auto* Character = Cast<ACharacter>(&Pawn))
    {
        const auto* Movement=Character->GetCharacterMovement();
        if (!Movement || !Movement->IsMovingOnGround()) return;
        if (Movement->CurrentFloor.IsWalkableFloor())
        {
            Support=Movement->CurrentFloor.HitResult.GetComponent();
            At.Z-=Movement->CurrentFloor.GetDistanceToFloor();
        }
    }
    RecordGround(Pawn,At,Support);
}

void FColdSteelDungeonMap::RecordGround(APawn& Pawn,FVector At,const UPrimitiveComponent* Support)
{
    const double Now=Pawn.GetWorld()->GetTimeSeconds();
    if (At==LastSample && Support==LastSupport.Get() && Now<RetryBlockedAt) return;
    RetryBlockedAt=DBL_MAX;
    LastSample = At;
    LastSupport=Support;
    const int32 Index = FindFootprint(At,Support);
    if (Index == INDEX_NONE) { LastFootprint=INDEX_NONE; PlayerArea.Reset(); return; }
    const FFootprint& Part = Footprints[Index];
    const int32 Floor = FloorFor(Index,At,Support);
    const bool bEntered = LastFootprint!=Index || PlayerFloor!=Floor;
    LastFootprint=Index;
    PlayerFloor=Floor;
    const FIntPoint Here = Grid(FVector2D(At),TileSize);
    const FRamp* Ramp = Ramps.Find(Part.Node);
    const int32 Radius = Part.bFallback || Ramp || FMath::Abs(At.Z-Part.GroundZ)>=200. ? 0 : 1;
    bool bAdded = false;
    TArray<FBox2D,TInlineAllocator<8>> Pending;
    for (int32 X=Here.X-Radius; X<=Here.X+Radius; ++X)
        for (int32 Y=Here.Y-Radius; Y<=Here.Y+Radius; ++Y)
        {
            const FVector2D Min(FMath::Max(X*TileSize,Part.Box.Min.X),FMath::Max(Y*TileSize,Part.Box.Min.Y));
            const FVector2D Max(FMath::Min((X+1)*TileSize,Part.Box.Max.X),FMath::Min((Y+1)*TileSize,Part.Box.Max.Y));
            if (Min.X>=Max.X || Min.Y>=Max.Y) continue;
            const FIntPoint Tile(X,Y);
            const FBox2D Whole(Min,Max);
            Pending.Add(Whole);
            while (!Pending.IsEmpty())
            {
                const FBox2D Rect=Pending.Pop(EAllowShrinking::No);
                bool bKnown=false;
                if (const auto* Layer=Layers.Find(Floor))
                    if (const auto* Indices=Layer->Tiles.Find(Tile))
                        for (int32 I : *Indices)
                        {
                            const auto& Old=Layer->Patches[I];
                            if (Old.Footprint==Index && Old.Bounds.IsInsideOrOn(Rect.Min) &&
                                Old.Bounds.IsInsideOrOn(Rect.Max)) { bKnown=true; break; }
                        }
                if (bKnown) continue;
                if (IsPatchClear(Pawn,At,Rect) && (!Support || Floor==Part.Floor || Ramp ||
                    IsAboveSameDeck(Pawn,*Support,At,Rect)))
                {
                    bAdded|=Reveal(Tile,Index,Floor,Rect,At.Z);
                    continue;
                }
                RetryBlockedAt=Now+.5;
                // Only subdivide the player's tile. Neighbours behind a leaf stay dark
                // and do not generate a fan of collision queries on each sample.
                if (Tile!=Here || Rect.GetSize().GetMax()<=TileSize/8.) continue;
                const FVector2D Mid=Rect.GetCenter();
                for (int32 A=0; A<2; ++A)
                    for (int32 B=0; B<2; ++B)
                    {
                        const FBox2D Sub({A?Mid.X:Rect.Min.X,B?Mid.Y:Rect.Min.Y},
                            {A?Rect.Max.X:Mid.X,B?Rect.Max.Y:Mid.Y});
                        if (Rect==Whole || Sub.IsInsideOrOn(FVector2D(At))) Pending.Add(Sub);
                    }
            }
        }
    if (bAdded)
    {
        ++Revision;
        if (!DiscoveredFloors.Contains(Floor)) { DiscoveredFloors.Add(Floor); DiscoveredFloors.Sort(); }
    }
    if (!IsKnown(FVector2D(At),Floor)) { LastFootprint=INDEX_NONE; PlayerArea.Reset(); return; }
    if (!bEntered) return;
    auto& Labels=Layers.FindChecked(Floor).Labels;
    if (Ramp)
    {
        const bool bLower=Floor==Ramp->Lower;
        PlayerArea=TEXT("跨层通道");
        if (!Labels.ContainsByPredicate([&](const auto& Label){ return Label.RampNode==Part.Node; }))
        {
            Labels.Add({FVector2D(At), bLower?TEXT("上行"):TEXT("下行"), Part.Node, bLower?Ramp->Upper:Ramp->Lower});
            ++Revision;
        }
        return;
    }
    const FDungeonRunNode* Node=Source.IsValid()?Source->NodeById(Part.Node):nullptr;
    const FString Name=Node ? Source->MapAreaName(*Node) : FString(TEXT("起始区"));
    PlayerArea=Name.IsEmpty() ? (Part.bPassage?TEXT("连接通道"):TEXT("过渡区域")) : Name;
    if (!Name.IsEmpty() && !Labels.ContainsByPredicate([&](const auto& Label){return Label.Text==Name;}))
    {
        Labels.Add({FVector2D(At),Name});
        ++Revision;
    }
}
