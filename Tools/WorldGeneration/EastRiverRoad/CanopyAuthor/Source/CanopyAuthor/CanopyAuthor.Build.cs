using UnrealBuildTool;
public class CanopyAuthor : ModuleRules
{
    public CanopyAuthor(ReadOnlyTargetRules Target) : base(Target)
    {
        PrivateDependencyModuleNames.AddRange(new[]{"Core","CoreUObject","Engine","UnrealEd","SkeletalMeshUtilitiesCommon","AssetRegistry"});
    }
}
