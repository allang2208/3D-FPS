#pragma once
#include "CoreMinimal.h"
#include "ColdSteelSkillTree.h"

/** Grid layout + orthogonal link routing for the skill tree and spec pages. C++ port of
    Work/SkillTreeMockup20261115/grid.js (itself adapted from game-dev src/ui/technology-tree-panel.js):
    right edge out / left edge in, one bus per source with 2+ targets, gutter routing for links that
    span 2+ columns, OR gates, ports ordered by approach height and staggered arrival verticals so links
    from different sources never cross (audited offline with grid_check.js). Units are layout pixels. */
namespace ColdSteelSkillTreeLayout
{
    struct FConfig { float W = 212, H = 84, Gap = 84, LaneGap = 40, OX = 168, OY = 64; int32 Columns = 4; };
    struct FItem { FName Id; int32 Lane = 0, Column = 0; TArray<ColdSteelSkillTree::FRequirement> Requires; };
    struct FRow { FName Key; FString Name, Note, Group; int32 Lanes = 1; TArray<FItem> Items; };

    struct FEntry { FName From, To; int32 Requirement = 0; FName Gate; };
    struct FLink { int32 Entry = 0; TArray<FVector2D> Points; TArray<FVector2D> FullPoints; bool bArrow = true; FVector2D Label; bool bHasLabel = false; };
    struct FBus { FName From; TArray<int32> Entries; TArray<FVector2D> Stub, Trunk; };
    struct FJunction { FName From; FVector2D At; TArray<int32> Entries; };
    struct FPort { int32 Entry = 0; FVector2D At; };
    struct FGate { FName Id, To; int32 Requirement = 0; FVector2D Center; TArray<FVector2D> Output; TArray<int32> Inputs; };
    struct FBadge { FName Id; int32 Requirement = 0; };
    struct FBand { FName Key; FString Name, Note, Group; int32 Lane = 0, Span = 1; TArray<FName> Items; };
    struct FCard { FName Id; FVector2D Pos; int32 Column = 0, Lane = 0; };

    struct FResult
    {
        FConfig Config;
        TArray<FCard> Cards; TMap<FName,int32> CardIndex;
        TArray<FBand> Bands;
        TArray<FEntry> Entries; TArray<FLink> Links; TArray<FBus> Buses; TArray<FJunction> Junctions; TArray<FPort> Ports; TArray<FGate> Gates; TArray<FBadge> Badges;
        FVector2D Size = FVector2D::ZeroVector;
        const FCard* Card(FName Id) const { const int32* I = CardIndex.Find(Id); return I ? &Cards[*I] : nullptr; }
    };
    FPSGAME_API FResult Build(const TArray<FRow>& Rows, const FConfig& Config);
}
