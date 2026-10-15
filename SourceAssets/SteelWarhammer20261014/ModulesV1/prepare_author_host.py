"""Build a minimal authoring host without linking unrelated in-flight gameplay code."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];H=P/'AuthorHost';M=H/'Source/WarhammerModuleAuthor';M.mkdir(parents=True,exist_ok=True)
(H/'WarhammerModuleAuthor.uproject').write_text(json.dumps({'FileVersion':3,'EngineAssociation':'5.8','Category':'Asset Authoring',
    'Modules':[{'Name':'WarhammerModuleAuthor','Type':'Editor','LoadingPhase':'Default'}]},indent=2),encoding='utf-8')
(H/'Source/WarhammerModuleAuthorEditor.Target.cs').write_text('''using UnrealBuildTool;
public class WarhammerModuleAuthorEditorTarget : TargetRules {
 public WarhammerModuleAuthorEditorTarget(TargetInfo Target) : base(Target) {
  Type=TargetType.Editor;DefaultBuildSettings=BuildSettingsVersion.V7;IncludeOrderVersion=EngineIncludeOrderVersion.Latest;
  ExtraModuleNames.Add("WarhammerModuleAuthor");
 }
}
''',encoding='utf-8')
(M/'WarhammerModuleAuthor.Build.cs').write_text('''using UnrealBuildTool;
public class WarhammerModuleAuthor : ModuleRules {
 public WarhammerModuleAuthor(ReadOnlyTargetRules Target) : base(Target) {
  PCHUsage=PCHUsageMode.UseExplicitOrSharedPCHs;
  PublicDependencyModuleNames.AddRange(new string[]{"Core","CoreUObject","Engine","Json","RenderCore","RHI","UnrealEd"});
 }
}
''',encoding='utf-8')
(M/'WarhammerModuleAuthor.cpp').write_text('''#include "Modules/ModuleManager.h"
#include "Misc/PackageName.h"
class FWarhammerModuleAuthor : public IModuleInterface {
 public: virtual void StartupModule() override {
  FPackageName::RegisterMountPoint(TEXT("/Game/"),TEXT("D:/FPS3D/FPSGAME/Content/"));
 }
};
IMPLEMENT_MODULE(FWarhammerModuleAuthor,WarhammerModuleAuthor)
''',encoding='utf-8')
for ext in ('h','cpp'):
    source=(ROOT/'Source/FPSGAME/Weapons'/('FrostSwordModuleAuthoringCommandlet.'+ext)).read_text(encoding='utf-8-sig')
    (M/('WarhammerMountAuthoringCommandlet.'+ext)).write_text(source.replace('FrostSwordModuleAuthoringCommandlet','WarhammerMountAuthoringCommandlet'),encoding='utf-8')
print(str(H/'WarhammerModuleAuthor.uproject'))
