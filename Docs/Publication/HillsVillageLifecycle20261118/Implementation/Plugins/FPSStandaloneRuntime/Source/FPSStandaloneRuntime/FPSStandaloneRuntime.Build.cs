using UnrealBuildTool;

public class FPSStandaloneRuntime : ModuleRules
{
    public FPSStandaloneRuntime(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PrivateDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "PythonScriptPlugin" });
    }
}
