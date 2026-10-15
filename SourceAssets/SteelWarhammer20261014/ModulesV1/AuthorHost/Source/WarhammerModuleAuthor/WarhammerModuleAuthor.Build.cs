using UnrealBuildTool;
public class WarhammerModuleAuthor : ModuleRules {
 public WarhammerModuleAuthor(ReadOnlyTargetRules Target) : base(Target) {
  PCHUsage=PCHUsageMode.UseExplicitOrSharedPCHs;
  PublicDependencyModuleNames.AddRange(new string[]{"Core","CoreUObject","Engine","Json","RenderCore","RHI","UnrealEd"});
 }
}
