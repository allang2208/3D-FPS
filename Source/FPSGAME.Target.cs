using UnrealBuildTool;
using System.Collections.Generic;

public class FPSGAMETarget : TargetRules
{
    public FPSGAMETarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("FPSGAME");
    }
}
