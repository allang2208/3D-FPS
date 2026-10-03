using UnrealBuildTool;
public class ClothBake : ModuleRules {
 public ClothBake(ReadOnlyTargetRules Target) : base(Target) {
  PCHUsage=PCHUsageMode.UseExplicitOrSharedPCHs;
  PrivateDependencyModuleNames.AddRange(new[]{"Core","CoreUObject","Engine","UnrealEd","ChaosClothAssetEngine","ChaosClothAssetTools"});
 }
}
