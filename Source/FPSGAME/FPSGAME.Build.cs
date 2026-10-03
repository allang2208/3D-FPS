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
            // Public because FPSGAME.cpp (the module entry point) calls
            // AddShaderSourceDirectoryMapping from ShaderCore.h to expose Source/Shaders as
            // the virtual shader directory /Project, so material Custom nodes can
            // `#include "/Project/ClearwaterWaves.ush"`. Without file-scope functions a
            // Custom node cannot compile at all -- its code field is a function body.
            ,"RenderCore"
        });
        RuntimeDependencies.Add("$(ProjectDir)/Content/ColdSteelData/...", StagedFileType.UFS);
        RuntimeDependencies.Add("$(ProjectDir)/Content/UI/GunsmithWorkbench/Fonts/...", StagedFileType.UFS);
        PrivateDependencyModuleNames.Add("AudioMixer");
        PrivateDependencyModuleNames.Add("AutoFootstep");
        PrivateDependencyModuleNames.Add("MoviePlayer");
        PrivateDependencyModuleNames.Add("ImageCore"); // Bounded expedition thumbnails decoded off the game thread.
        RuntimeDependencies.Add("$(ProjectDir)/Content/UI/TransitLoading/...", StagedFileType.UFS);
        RuntimeDependencies.Add("$(ProjectDir)/Content/UI/MainMenu/...", StagedFileType.UFS);
        PrivateDependencyModuleNames.Add("Sockets");
        PrivateDependencyModuleNames.Add("NetCore"); // Packed body-motion vectors link UE::Net quantization helpers.
        PrivateDependencyModuleNames.Add("PhysicsCore");
        PrivateDependencyModuleNames.Add("Chaos");
        PrivateDependencyModuleNames.Add("ChaosCore"); // TAABB methods used by dungeon geometry are exported by ChaosCore in UE 5.8.
        PrivateDependencyModuleNames.Add("FPSBlast");
        PrivateDependencyModuleNames.Add("AnimationCore");
        PrivateDependencyModuleNames.Add("HairStrandsCore");
        PrivateDependencyModuleNames.Add("AnimationWarpingRuntime");
        PrivateDependencyModuleNames.AddRange(new[] { "RenderCore", "RHI" });
        PrivateDependencyModuleNames.AddRange(new[] { "ClothingSystemRuntimeCommon", "ClothingSystemRuntimeInterface" });
        PrivateDependencyModuleNames.AddRange(new[] { "PCG", "GeometryCore", "GeometryFramework" });
        if (Target.bBuildEditor) PrivateDependencyModuleNames.Add("NiagaraEditor");
        if (Target.bBuildEditor) PrivateDependencyModuleNames.AddRange(new[] { "UnrealEd", "EditorScriptingUtilities" });
        if (Target.bBuildEditor) PrivateDependencyModuleNames.AddRange(new[] { "MeshDescription", "StaticMeshDescription", "SkeletalMeshDescription" });
        if (Target.bBuildEditor) PrivateDependencyModuleNames.AddRange(new[]
        {
            "ClothingSystemEditor", "ClothingSystemEditorInterface",
            "ChaosCloth"
        });
    }
}
