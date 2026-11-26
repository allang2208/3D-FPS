using UnrealBuildTool;
public class ForestPathStudy : ModuleRules
{
    public ForestPathStudy(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PrivateDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "UnrealEd", "Landscape", "LandscapeEditor", "PCG", "CinematicCamera", "AssetRegistry" });
    }
}
