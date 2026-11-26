using UnrealBuildTool;
public class CanopyAuthorEditorTarget : TargetRules
{
    public CanopyAuthorEditorTarget(TargetInfo Target) : base(Target)
    {
        Type=TargetType.Editor;
        DefaultBuildSettings=BuildSettingsVersion.Latest;
        IncludeOrderVersion=EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("CanopyAuthor");
    }
}
