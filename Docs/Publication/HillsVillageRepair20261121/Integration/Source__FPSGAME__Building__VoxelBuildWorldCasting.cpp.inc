// Source/FPSGAME/Building/VoxelBuildWorldCasting.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 26-26 | AVoxelBuildPrefabActor* AVoxelBuildWorld::PrefabActorAt(FIntVector Cell) const
        if(It->GetOwner()==this&&It->AnchorCell()==Cell&&!It->IsSceneStation()&&!It->PrefabId().IsNone()&&!It->IsFalling())
