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
            "AIModule",
            "NavigationSystem",
            "GameplayTasks",
            "ImageWrapper"
            ,"Json"
        });
        RuntimeDependencies.Add("$(ProjectDir)/Content/ColdSteelData/...", StagedFileType.UFS);
        PrivateDependencyModuleNames.Add("AudioMixer");
        PrivateDependencyModuleNames.Add("MoviePlayer");
        RuntimeDependencies.Add("$(ProjectDir)/Content/UI/TransitLoading/...", StagedFileType.UFS);
        PrivateDependencyModuleNames.Add("PhysicsCore");
        PrivateDependencyModuleNames.Add("AnimationCore");
        PrivateDependencyModuleNames.AddRange(new[] { "RenderCore", "RHI" });
        PrivateDependencyModuleNames.AddRange(new[] { "PCG", "GeometryCore", "GeometryFramework" });
        if (Target.bBuildEditor) PrivateDependencyModuleNames.Add("NiagaraEditor");
        if (Target.bBuildEditor) PrivateDependencyModuleNames.Add("UnrealEd");
    }
}
