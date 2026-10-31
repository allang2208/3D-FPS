using UnrealBuildTool;
public class CityAuthoring : ModuleRules
{
    public CityAuthoring(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] {"Core", "CoreUObject", "Engine"});
        PrivateDependencyModuleNames.AddRange(new[] {"PCG", "Json", "JsonUtilities", "UnrealEd"});
    }
}
