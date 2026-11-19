using UnrealBuildTool;
public class JasonAuthoringEditorTarget : TargetRules
{
    public JasonAuthoringEditorTarget(TargetInfo target) : base(target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("JasonReviewEditor");
    }
}
