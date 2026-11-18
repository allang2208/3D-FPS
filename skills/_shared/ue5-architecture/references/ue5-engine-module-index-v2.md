# UE5.6-UE5.8 Engine Module Index V2.4

本页是下列生成日期和引擎目录的历史索引，模块数、分类与样本保持原始记录；使用时仅作查找线索，实际依赖与 API 读取当前工程及引擎源。原因：引擎版本与本机安装会变化，历史扫描结果不能保证当前模块可用，也不应为了维护文档自动重新扫描。

- Engine Source: `E:\UEVersion\UE_5.8\Engine\Source`
- Detected Engine Version: `5.8.2`
- Generated At: 2026-08-26 16:33:27
- Total Modules (.Build.cs): **755**
- Full CSV: `skills/ue5-architecture/references/ue5-engine-module-index-v2.csv`
- Final Routing CSV: `skills/ue5-architecture/references/ue5-module-routing-table-final.csv`

## Layer Distribution
- Runtime: 291
- Developer: 164
- ThirdParty: 153
- Editor: 145
- Programs: 2

## Domain V2 Distribution
- General: 490
- CoreEngine: 43
- NetworkingOnline: 41
- Rendering: 41
- Audio: 37
- AssetsBuildPipeline: 27
- Animation: 16
- UI: 15
- Media: 13
- Physics: 11
- GameplayFramework: 10
- AI_Mass: 9
- XR: 2

## Target Skill Distribution
- ue5-architecture: 532
- ue5-cpp-gameplay: 87
- ue5-performance-packaging: 70
- ue5-save-load-replication: 40
- ue5-ui-umg-slate: 15
- ue5-world-interaction: 11

## Routing Confidence Distribution
- medium: 625
- low: 103
- high: 27

## Sample (First 100)
| Module | Layer | DomainV2 | TargetSkill | Confidence | Build.cs |
|---|---|---|---|---|---|
| AITestSuite | Developer | General | ue5-architecture | medium | `Developer\AITestSuite\AITestSuite.Build.cs` |
| AndroidDeviceDetection | Developer | General | ue5-architecture | medium | `Developer\Android\AndroidDeviceDetection\AndroidDeviceDetection.Build.cs` |
| AndroidPlatformEditor | Developer | General | ue5-architecture | medium | `Developer\Android\AndroidPlatformEditor\AndroidPlatformEditor.Build.cs` |
| AndroidTargetPlatform | Developer | General | ue5-architecture | medium | `Developer\Android\AndroidTargetPlatform\AndroidTargetPlatform.Build.cs` |
| AndroidTargetPlatformControls | Developer | General | ue5-architecture | medium | `Developer\Android\AndroidTargetPlatformControls\AndroidTargetPlatformControls.Build.cs` |
| AndroidTargetPlatformSettings | Developer | General | ue5-architecture | medium | `Developer\Android\AndroidTargetPlatformSettings\AndroidTargetPlatformSettings.Build.cs` |
| AnimationDataController | Developer | Animation | ue5-cpp-gameplay | medium | `Developer\AnimationDataController\AnimationDataController.build.cs` |
| AnimationWidgets | Developer | Animation | ue5-cpp-gameplay | medium | `Developer\AnimationWidgets\AnimationWidgets.Build.cs` |
| AssetTools | Developer | AssetsBuildPipeline | ue5-performance-packaging | high | `Developer\AssetTools\AssetTools.Build.cs` |
| AudioFormatADPCM | Developer | Audio | ue5-cpp-gameplay | medium | `Developer\AudioFormatADPCM\AudioFormatADPCM.Build.cs` |
| AudioFormatBink | Developer | Audio | ue5-cpp-gameplay | medium | `Developer\AudioFormatBink\AudioFormatBink.Build.cs` |
| AudioFormatOgg | Developer | Audio | ue5-cpp-gameplay | medium | `Developer\AudioFormatOgg\AudioFormatOgg.Build.cs` |
| AudioFormatOpus | Developer | Audio | ue5-cpp-gameplay | medium | `Developer\AudioFormatOpus\AudioFormatOpus.Build.cs` |
| AudioFormatRad | Developer | Audio | ue5-cpp-gameplay | medium | `Developer\AudioFormatRad\AudioFormatRad.Build.cs` |
| AudioSettingsEditor | Developer | Audio | ue5-cpp-gameplay | medium | `Developer\AudioSettingsEditor\AudioSettingsEditor.Build.cs` |
| AutomationController | Developer | General | ue5-architecture | medium | `Developer\AutomationController\AutomationController.Build.cs` |
| AutomationDriver | Developer | General | ue5-architecture | medium | `Developer\AutomationDriver\AutomationDriver.Build.cs` |
| AutomationWindow | Developer | General | ue5-architecture | medium | `Developer\AutomationWindow\AutomationWindow.Build.cs` |
| BlankModule | Developer | General | ue5-architecture | medium | `Developer\BlankModule\BlankModule.Build.cs` |
| BSPUtils | Developer | General | ue5-architecture | medium | `Developer\BSPUtils\BSPUtils.Build.cs` |
| ChaosTestHarness | Developer | Physics | ue5-world-interaction | medium | `Developer\ChaosTestHarness\ChaosTestHarness.Build.cs` |
| CollectionManager | Developer | General | ue5-architecture | medium | `Developer\CollectionManager\CollectionManager.Build.cs` |
| CollisionAnalyzer | Developer | Physics | ue5-world-interaction | medium | `Developer\CollisionAnalyzer\CollisionAnalyzer.Build.cs` |
| CookedEditor | Developer | General | ue5-architecture | medium | `Developer\CookedEditor\CookedEditor.Build.cs` |
| CookMetadata | Developer | AssetsBuildPipeline | ue5-performance-packaging | medium | `Developer\CookMetadata\CookMetadata.Build.cs` |
| CookOnTheFlyNetServer | Developer | NetworkingOnline | ue5-performance-packaging | high | `Developer\CookOnTheFlyNetServer\CookOnTheFlyNetServer.Build.cs` |
| CQTest | Developer | General | ue5-architecture | medium | `Developer\CQTest\CQTest.Build.cs` |
| CrashDebugHelper | Developer | General | ue5-architecture | medium | `Developer\CrashDebugHelper\CrashDebugHelper.Build.cs` |
| CSVUtils | Developer | General | ue5-architecture | medium | `Developer\CSVUtils\CSVUtils.build.cs` |
| DatasmithExporter | Developer | General | ue5-architecture | medium | `Developer\Datasmith\DatasmithExporter\DatasmithExporter.Build.cs` |
| DatasmithExporterUI | Developer | UI | ue5-ui-umg-slate | medium | `Developer\Datasmith\DatasmithExporterUI\DatasmithExporterUI.Build.cs` |
| DatasmithFacade | Developer | General | ue5-architecture | medium | `Developer\Datasmith\DatasmithFacade\DatasmithFacade.Build.cs` |
| DerivedDataCache | Developer | General | ue5-architecture | medium | `Developer\DerivedDataCache\DerivedDataCache.Build.cs` |
| DesktopPlatform | Developer | General | ue5-architecture | medium | `Developer\DesktopPlatform\DesktopPlatform.Build.cs` |
| DesktopWidgets | Developer | General | ue5-architecture | medium | `Developer\DesktopWidgets\DesktopWidgets.Build.cs` |
| DeveloperToolSettings | Developer | General | ue5-architecture | medium | `Developer\DeveloperToolSettings\DeveloperToolSettings.Build.cs` |
| DevHttp | Developer | NetworkingOnline | ue5-save-load-replication | medium | `Developer\DevHttp\DevHttp.Build.cs` |
| DeviceManager | Developer | General | ue5-architecture | medium | `Developer\DeviceManager\DeviceManager.Build.cs` |
| DirectoryWatcher | Developer | General | ue5-architecture | medium | `Developer\DirectoryWatcher\DirectoryWatcher.Build.cs` |
| DistributedBuildInterface | Developer | General | ue5-architecture | medium | `Developer\DistributedBuildInterface\DistributedBuildInterface.build.cs` |
| DrawPrimitiveDebugger | Developer | General | ue5-architecture | medium | `Developer\DrawPrimitiveDebugger\DrawPrimitiveDebugger.Build.cs` |
| EditorAnalyticsSession | Developer | General | ue5-architecture | medium | `Developer\EditorAnalyticsSession\EditorAnalyticsSession.Build.cs` |
| ExternalImagePicker | Developer | General | ue5-architecture | medium | `Developer\ExternalImagePicker\ExternalImagePicker.Build.cs` |
| FileUtilities | Developer | General | ue5-architecture | medium | `Developer\FileUtilities\FileUtilities.Build.cs` |
| FunctionalTesting | Developer | General | ue5-architecture | medium | `Developer\FunctionalTesting\FunctionalTesting.Build.cs` |
| GDKPlatformEditor | Developer | General | ue5-architecture | medium | `Developer\Microsoft\GDKPlatformEditor\GDKPlatformEditor.Build.cs` |
| GeometryProcessingInterfaces | Developer | General | ue5-architecture | medium | `Developer\GeometryProcessingInterfaces\GeometryProcessingInterfaces.Build.cs` |
| GraphColor | Developer | General | ue5-architecture | medium | `Developer\GraphColor\GraphColor.Build.cs` |
| HierarchicalLODUtilities | Developer | General | ue5-architecture | medium | `Developer\HierarchicalLODUtilities\HierarchicalLODUtilities.Build.cs` |
| HlslParser | Developer | General | ue5-architecture | medium | `Developer\HlslParser\HlslParser.Build.cs` |
| Horde | Developer | General | ue5-architecture | medium | `Developer\Horde\Horde.Build.cs` |
| HotReload | Developer | General | ue5-architecture | medium | `Developer\HotReload\HotReload.Build.cs` |
| IOSPlatformEditor | Developer | General | ue5-architecture | medium | `Developer\IOS\IOSPlatformEditor\IOSPlatformEditor.Build.cs` |
| IOSTargetPlatform | Developer | General | ue5-architecture | medium | `Developer\IOS\IOSTargetPlatform\IOSTargetPlatform.Build.cs` |
| IOSTargetPlatformControls | Developer | General | ue5-architecture | medium | `Developer\IOS\IOSTargetPlatformControls\IOSTargetPlatformControls.Build.cs` |
| IOSTargetPlatformSettings | Developer | General | ue5-architecture | medium | `Developer\IOS\IOSTargetPlatformSettings\IOSTargetPlatformSettings.Build.cs` |
| IoStoreOnDemandUtilities | Developer | General | ue5-architecture | medium | `Developer\IoStore\OnDemandUtilities\IoStoreOnDemandUtilities.Build.cs` |
| IoStoreUtilities | Developer | General | ue5-architecture | medium | `Developer\IoStoreUtilities\IoStoreUtilities.Build.cs` |
| LauncherServices | Developer | General | ue5-architecture | medium | `Developer\LauncherServices\LauncherServices.Build.cs` |
| LegacyProjectLauncher | Developer | General | ue5-architecture | medium | `Developer\LegacyProjectLauncher\LegacyProjectLauncher.Build.cs` |
| LinuxArm64TargetPlatform | Developer | General | ue5-architecture | medium | `Developer\Linux\LinuxArm64TargetPlatform\LinuxArm64TargetPlatform.Build.cs` |
| LinuxArm64TargetPlatformControls | Developer | General | ue5-architecture | medium | `Developer\Linux\LinuxArm64TargetPlatformControls\LinuxArm64TargetPlatformControls.Build.cs` |
| LinuxArm64TargetPlatformSettings | Developer | General | ue5-architecture | medium | `Developer\Linux\LinuxArm64TargetPlatformSettings\LinuxArm64TargetPlatformSettings.Build.cs` |
| LinuxPlatformEditor | Developer | General | ue5-architecture | medium | `Developer\Linux\LinuxPlatformEditor\LinuxPlatformEditor.Build.cs` |
| LinuxTargetPlatform | Developer | General | ue5-architecture | medium | `Developer\Linux\LinuxTargetPlatform\LinuxTargetPlatform.Build.cs` |
| LinuxTargetPlatformControls | Developer | General | ue5-architecture | medium | `Developer\Linux\LinuxTargetPlatformControls\LinuxTargetPlatformControls.Build.cs` |
| LinuxTargetPlatformSettings | Developer | General | ue5-architecture | medium | `Developer\Linux\LinuxTargetPlatformSettings\LinuxTargetPlatformSettings.Build.cs` |
| LiveCoding | Developer | General | ue5-architecture | medium | `Developer\Windows\LiveCoding\LiveCoding.Build.cs` |
| LiveCodingServer | Developer | General | ue5-architecture | medium | `Developer\Windows\LiveCodingServer\LiveCodingServer.Build.cs` |
| Localization | Developer | General | ue5-architecture | medium | `Developer\Localization\Localization.Build.cs` |
| LocalizationService | Developer | General | ue5-architecture | medium | `Developer\LocalizationService\LocalizationService.Build.cs` |
| LogVisualizer | Developer | General | ue5-architecture | medium | `Developer\LogVisualizer\LogVisualizer.Build.cs` |
| LowLevelTestsRunner | Developer | General | ue5-architecture | medium | `Developer\LowLevelTestsRunner\LowLevelTestsRunner.Build.cs` |
| MacPlatformEditor | Developer | General | ue5-architecture | medium | `Developer\Mac\MacPlatformEditor\MacPlatformEditor.Build.cs` |
| MacTargetPlatform | Developer | General | ue5-architecture | medium | `Developer\Mac\MacTargetPlatform\MacTargetPlatform.Build.cs` |
| MacTargetPlatformControls | Developer | General | ue5-architecture | medium | `Developer\Mac\MacTargetPlatformControls\MacTargetPlatformControls.Build.cs` |
| MacTargetPlatformSettings | Developer | General | ue5-architecture | medium | `Developer\Mac\MacTargetPlatformSettings\MacTargetPlatformSettings.Build.cs` |
| MassEntityTestSuite | Developer | AI_Mass | ue5-cpp-gameplay | medium | `Developer\MassEntityTestSuite\MassEntityTestSuite.Build.cs` |
| MaterialBaking | Developer | Rendering | ue5-performance-packaging | medium | `Developer\MaterialBaking\MaterialBaking.Build.cs` |
| MaterialUtilities | Developer | Rendering | ue5-performance-packaging | medium | `Developer\MaterialUtilities\MaterialUtilities.Build.cs` |
| Merge | Developer | General | ue5-architecture | medium | `Developer\Merge\Merge.Build.cs` |
| MeshBoneReduction | Developer | General | ue5-architecture | medium | `Developer\MeshBoneReduction\MeshBoneReduction.Build.cs` |
| MeshBuilder | Developer | General | ue5-architecture | medium | `Developer\MeshBuilder\MeshBuilder.Build.cs` |
| MeshBuilderCommon | Developer | General | ue5-architecture | medium | `Developer\MeshBuilderCommon\MeshBuilderCommon.Build.cs` |
| MeshDescriptionOperations | Developer | General | ue5-architecture | medium | `Developer\MeshDescriptionOperations\MeshDescriptionOperations.Build.cs` |
| MeshMergeUtilities | Developer | General | ue5-architecture | medium | `Developer\MeshMergeUtilities\MeshMergeUtilities.Build.cs` |
| MeshReductionInterface | Developer | General | ue5-architecture | medium | `Developer\MeshReductionInterface\MeshReductionInterface.Build.cs` |
| MeshUtilities | Developer | General | ue5-architecture | medium | `Developer\MeshUtilities\MeshUtilities.Build.cs` |
| MeshUtilitiesEngine | Developer | CoreEngine | ue5-architecture | medium | `Developer\MeshUtilitiesEngine\MeshUtilitiesEngine.Build.cs` |
| MessageLog | Developer | General | ue5-architecture | medium | `Developer\MessageLog\MessageLog.Build.cs` |
| MetalShaderFormat | Developer | Rendering | ue5-performance-packaging | medium | `Developer\Apple\MetalShaderFormat\MetalShaderFormat.Build.cs` |
| NaniteBuilder | Developer | Rendering | ue5-performance-packaging | medium | `Developer\NaniteBuilder\NaniteBuilder.Build.cs` |
| NaniteUtilities | Developer | Rendering | ue5-performance-packaging | medium | `Developer\NaniteUtilities\NaniteUtilities.Build.cs` |
| OutputLog | Developer | General | ue5-architecture | medium | `Developer\OutputLog\OutputLog.Build.cs` |
| PakFileUtilities | Developer | General | ue5-architecture | medium | `Developer\PakFileUtilities\PakFileUtilities.Build.cs` |
| PhysicsUtilities | Developer | Physics | ue5-world-interaction | medium | `Developer\PhysicsUtilities\PhysicsUtilities.Build.cs` |
| ProfileVisualizer | Developer | General | ue5-architecture | medium | `Developer\ProfileVisualizer\ProfileVisualizer.Build.cs` |
| QuadricMeshReduction | Developer | General | ue5-architecture | medium | `Developer\MeshSimplifier\QuadricMeshReduction.Build.cs` |
| S3Client | Developer | General | ue5-architecture | medium | `Developer\S3Client\S3Client.Build.cs` |
| ScreenShotComparison | Developer | General | ue5-architecture | medium | `Developer\ScreenShotComparison\ScreenShotComparison.Build.cs` |
