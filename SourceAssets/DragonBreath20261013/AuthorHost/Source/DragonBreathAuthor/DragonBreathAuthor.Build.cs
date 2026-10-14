using UnrealBuildTool;
public class DragonBreathAuthor : ModuleRules { public DragonBreathAuthor(ReadOnlyTargetRules Target) : base(Target) { PCHUsage=PCHUsageMode.UseExplicitOrSharedPCHs; PublicDependencyModuleNames.AddRange(new[]{"Core","CoreUObject","Engine","Niagara"}); PrivateDependencyModuleNames.AddRange(new[]{"NiagaraEditor","UnrealEd","RenderCore","RHI","Json"}); } }
