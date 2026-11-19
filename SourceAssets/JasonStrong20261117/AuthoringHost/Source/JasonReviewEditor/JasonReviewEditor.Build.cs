using UnrealBuildTool;
public class JasonReviewEditor : ModuleRules
{
    public JasonReviewEditor(ReadOnlyTargetRules target) : base(target)
    {
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine" });
        PrivateDependencyModuleNames.AddRange(new[] { "UnrealEd", "AnimGraph", "AnimGraphRuntime", "BlueprintGraph", "KismetCompiler" });
    }
}
