using UnrealBuildTool;
using System.IO;
public class FPSBlast : ModuleRules
{
    public FPSBlast(ReadOnlyTargetRules Target) : base(Target)
    {
        Type = ModuleType.External;
        if (Target.Platform != UnrealTargetPlatform.Win64)
            throw new BuildException("FPSBlast currently supports Win64. Build its adapter for the target platform before enabling it.");
        PublicSystemIncludePaths.Add(Path.Combine(ModuleDirectory, "Adapter"));
        string Library = Path.Combine(ModuleDirectory, "Lib", "Win64", "FPSBlast.lib");
        if (!File.Exists(Library))
            throw new BuildException("Build Blast first: python Tools/Building/build_blast.py");
        PublicAdditionalLibraries.Add(Library);
        RuntimeDependencies.Add("$(TargetOutputDir)/ThirdPartyNotices/Blast-LICENSE.md", Path.Combine(ModuleDirectory,"SDK","LICENSE.md"), StagedFileType.NonUFS);
        RuntimeDependencies.Add("$(TargetOutputDir)/ThirdPartyNotices/Blast-NOTICE.md", Path.Combine(ModuleDirectory,"NOTICE.md"), StagedFileType.NonUFS);
    }
}
