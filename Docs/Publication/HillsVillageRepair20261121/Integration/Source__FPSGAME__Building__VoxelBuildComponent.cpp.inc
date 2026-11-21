// Source/FPSGAME/Building/VoxelBuildComponent.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 289-289 | void UVoxelBuildComponent::TryInitializeWorld()
        VillageWorld=Hills;

// Lines 535-535 | void UVoxelBuildComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
    if(bPanelOpen||VillageBuildDefense::IsVillageRecipe(SelectedComponent))RefreshVillageConstructionAccess();
