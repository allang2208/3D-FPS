using UnrealBuildTool;
public class WarhammerModuleAuthorEditorTarget : TargetRules {
 public WarhammerModuleAuthorEditorTarget(TargetInfo Target) : base(Target) {
  Type=TargetType.Editor;DefaultBuildSettings=BuildSettingsVersion.V7;IncludeOrderVersion=EngineIncludeOrderVersion.Latest;
  ExtraModuleNames.Add("WarhammerModuleAuthor");
 }
}
