using UnrealBuildTool;

public class ColdSteelNet : ModuleRules
{
    public ColdSteelNet(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[]
        {
            "Core",
            "CoreUObject",
            "Engine",
            "InputCore",
            // 游戏主模块：引用 AFPSGAMECharacter / AFPSGAMEPlayerController
            "FPSGAME"
        });

        // FPSGAME 是平铺布局模块（无 Public/Private 分层），头文件默认对外不可见；
        // 显式暴露其源码根目录供本插件 include。
        PublicIncludePaths.Add("$(ProjectDir)/Source/FPSGAME");
    }
}
