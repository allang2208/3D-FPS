using UnrealBuildTool;
public class DragonBreathAuthorEditorTarget : TargetRules { public DragonBreathAuthorEditorTarget(TargetInfo Target) : base(Target) { Type=TargetType.Editor; DefaultBuildSettings=BuildSettingsVersion.V7; IncludeOrderVersion=EngineIncludeOrderVersion.Latest; ExtraModuleNames.Add("DragonBreathAuthor"); } }
