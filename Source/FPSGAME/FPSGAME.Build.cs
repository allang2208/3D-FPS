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
            "AdaptivePathfindingSystem",
            "GameplayTasks",
            "ImageWrapper"
            ,"Json"
            // Public headers expose RenderCore types: FacilityHallSpawnSubsystem.h and
            // GameResourcePreparation.h use FRenderCommandFence; TemperateVegetationRenderAudit.h
            // includes RenderingThread.h. Keep this dependency public for their consumers.
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
        PrivateDependencyModuleNames.Add("RHI");
        if (Target.Platform == UnrealTargetPlatform.Win64)
        {
            PrivateDependencyModuleNames.Add("D3D12RHI"); // Public native-resource identity API for opt-in F6 capture.
            PublicSystemLibraries.Add("advapi32.lib"); // ETW controller/provider; no external recorder process.
        }
        PrivateDependencyModuleNames.AddRange(new[] { "ClothingSystemRuntimeCommon", "ClothingSystemRuntimeInterface" });
        PrivateDependencyModuleNames.AddRange(new[] { "PCG", "GeometryCore", "GeometryFramework" });
        if (Target.bBuildEditor) PrivateDependencyModuleNames.Add("NiagaraEditor");
        if (Target.bBuildEditor) PrivateDependencyModuleNames.Add("SlateRHIRenderer"); // Offscreen ammo-wheel diagnosis.
        if (Target.bBuildEditor) PrivateDependencyModuleNames.AddRange(new[] { "UnrealEd", "EditorScriptingUtilities", "AssetRegistry", "Projects" });
        if (Target.bBuildEditor) PrivateDependencyModuleNames.AddRange(new[] { "MeshDescription", "StaticMeshDescription", "SkeletalMeshDescription" });
        if (Target.bBuildEditor) PrivateDependencyModuleNames.AddRange(new[]
        {
            "ClothingSystemEditor", "ClothingSystemEditorInterface",
            "ChaosCloth"
        });
    }
}
