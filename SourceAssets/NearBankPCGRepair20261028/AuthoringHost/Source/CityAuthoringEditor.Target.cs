using UnrealBuildTool;
public class CityAuthoringEditorTarget : TargetRules
{
    public CityAuthoringEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("CityAuthoring");
    }
}
