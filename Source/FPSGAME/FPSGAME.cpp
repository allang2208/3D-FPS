// FPSGAME primary module.

#include "FPSGAME.h"

#include "Diagnostics/FPSLoadHitchProbe.h"

#include "Containers/Ticker.h"
#include "Modules/ModuleManager.h"

namespace
{
    FTSTicker::FDelegateHandle GLoadHitchTicker;

    bool TickLoadHitchProbe(float /*DeltaTime*/)
    {
        FFPSLoadHitchProbe::Tick();
        return true; // keep ticking for the module's lifetime
    }
}

class FFPSGAMEModule : public FDefaultGameModuleImpl
{
public:
    virtual void StartupModule() override
    {
        FDefaultGameModuleImpl::StartupModule();

        // NOTE: no shader directory registration here on purpose.
        //
        // The engine already maps the virtual directory "/Project" onto <ProjectDir>/Shaders,
        // in LaunchEngineLoop.cpp:
        //
        //     const FString ProjectShaderPath = FPaths::Combine(FPaths::ProjectDir(), TEXT("Shaders"));
        //     if (FPaths::DirectoryExists(ProjectShaderPath))
        //         AddShaderSourceDirectoryMapping(TEXT("/Project"), ProjectShaderPath);
        //
        // An earlier version of this file mapped "/Project" to Source/Shaders instead. Because
        // AddShaderSourceDirectoryMapping does not overwrite an existing entry, that call
        // silently did nothing, and the engine's own mapping won -- so materials that
        // `#include "/Project/ClearwaterWaves.ush"` failed with
        //     File '/Project/ClearwaterWaves.ush' not found
        // and UE fell back to the Default Material. The include file lives at
        // <ProjectDir>/Shaders/ClearwaterWaves.ush; see Tools/Fluids/clearwater_generate_nodes.py.
        FFPSLoadHitchProbe::Startup();
        GLoadHitchTicker = FTSTicker::GetCoreTicker().AddTicker(
            FTickerDelegate::CreateStatic(&TickLoadHitchProbe));
    }

    virtual void ShutdownModule() override
    {
        if (GLoadHitchTicker.IsValid())
        {
            FTSTicker::GetCoreTicker().RemoveTicker(GLoadHitchTicker);
            GLoadHitchTicker.Reset();
        }
        FFPSLoadHitchProbe::Shutdown();
        FDefaultGameModuleImpl::ShutdownModule();
    }
};

IMPLEMENT_PRIMARY_GAME_MODULE(FFPSGAMEModule, FPSGAME, "FPSGAME");