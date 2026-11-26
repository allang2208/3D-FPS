using UnrealBuildTool;
public class ForestPathStudyEditorTarget : TargetRules
{
    public ForestPathStudyEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("ForestPathStudy");
    }
}
