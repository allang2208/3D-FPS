#include "Modules/ModuleManager.h"
#include "Misc/PackageName.h"
class FWarhammerModuleAuthor : public IModuleInterface {
 public: virtual void StartupModule() override {
  FPackageName::RegisterMountPoint(TEXT("/Game/"),TEXT("D:/FPS3D/FPSGAME/Content/"));
 }
};
IMPLEMENT_MODULE(FWarhammerModuleAuthor,WarhammerModuleAuthor)
