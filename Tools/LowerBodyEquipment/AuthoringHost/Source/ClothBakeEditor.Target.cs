using UnrealBuildTool;
public class ClothBakeEditorTarget : TargetRules {
 public ClothBakeEditorTarget(TargetInfo Target) : base(Target) {
  Type=TargetType.Editor; DefaultBuildSettings=BuildSettingsVersion.V7;
  IncludeOrderVersion=EngineIncludeOrderVersion.Latest; ExtraModuleNames.Add("ClothBake");
 }
}
