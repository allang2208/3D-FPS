using UnrealBuildTool;

public class FPSGAME : ModuleRules
{
    public FPSGAME(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[]
        {
            "Core",
            "CoreUObject",
            "Engine",
            "AnimGraphRuntime",
            "InputCore",
            "Niagara",
            "UMG",
            "Slate",
            "SlateCore",
            "CommonUI",
            "EnhancedInput",
            "GameplayTags",
            "ImageWrapper"
        });
        // Weather diagnostics and editor-only Niagara authoring bridge.
        PrivateDependencyModuleNames.AddRange(new[] { "RenderCore", "RHI" });
        if (Target.bBuildEditor) PrivateDependencyModuleNames.Add("NiagaraEditor");
    }
}
