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
            ,"Json"
        });
        RuntimeDependencies.Add("$(ProjectDir)/Content/ColdSteelData/...", StagedFileType.UFS);
        PrivateDependencyModuleNames.Add("AudioMixer");
        PrivateDependencyModuleNames.AddRange(new[] { "RenderCore", "RHI" });
        if (Target.bBuildEditor) PrivateDependencyModuleNames.Add("NiagaraEditor");
    }
}
