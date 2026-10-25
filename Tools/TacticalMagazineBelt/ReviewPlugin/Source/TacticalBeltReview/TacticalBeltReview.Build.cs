using UnrealBuildTool;
public class TacticalBeltReview : ModuleRules
{
    public TacticalBeltReview(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage=PCHUsageMode.UseExplicitOrSharedPCHs;
        PrivateDependencyModuleNames.AddRange(new[]{"Core","CoreUObject","Engine","Json","JsonUtilities","UMG","SlateCore","PhysicsCore","GameplayTags","NetCore","RenderCore","RHI"});
        PrivateIncludePaths.Add("D:/FPS3D/FPSGAME/Source/FPSGAME");
        PrivateIncludePaths.Add("D:/FPS3D/FPSGAME/Intermediate/Build/Win64/UnrealEditor/Inc/FPSGAME/UHT");
        PublicDefinitions.Add("FPSGAME_API=DLLIMPORT");
        PublicDefinitions.Add("FPSGAME_NON_ATTRIBUTED_API=DLLIMPORT");
        PublicAdditionalLibraries.Add("D:/FPS3D/FPSGAME/Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME/UnrealEditor-FPSGAME.lib");
    }
}
