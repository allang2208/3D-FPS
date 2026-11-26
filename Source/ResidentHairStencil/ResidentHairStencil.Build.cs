using UnrealBuildTool;
using System.IO;

public class ResidentHairStencil : ModuleRules
{
    public ResidentHairStencil(ReadOnlyTargetRules Target) : base(Target)
    {
        PublicDependencyModuleNames.Add("Core");
        PrivateDependencyModuleNames.AddRange(new[] { "CoreUObject", "Engine", "Renderer", "RenderCore", "RHI" });
        // UE 5.8 exposes strand visibility samples to deferred view extensions through FViewInfo.
        PrivateIncludePaths.Add(Path.Combine(EngineDirectory, "Source/Runtime/Renderer/Private"));
        PrivateIncludePaths.Add(Path.Combine(EngineDirectory, "Source/Runtime/Renderer/Internal"));
    }
}
