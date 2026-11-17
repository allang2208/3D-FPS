#pragma once

#include "CoreMinimal.h"
#include "Widgets/SWidget.h"
#include "ColdSteelWorldMapData.h"
#include "ColdSteelDungeonMap.h"
#include "ColdSteelMapMarkers.h"

class APlayerController;

struct FColdSteelWorldMapSession
{
    FColdSteelMapMarkers Markers;
    FGuid SelectedMarker;
    bool bEditingMarker = false;
    TOptional<FColdSteelMapMarker> MarkerDraft;
    uint32 MarkerUIRevision = 0;
    FColdSteelMapSurfaceCache SurfaceCache;
    FColdSteelDungeonMap DungeonMap;
};

TSharedRef<SWidget> MakeColdSteelWorldMap(APlayerController* Player,
    TSharedRef<FColdSteelWorldMapSession> Session, FSimpleDelegate Close);
