#include "Modules/ModuleManager.h"
#include "Engine/World.h"
#include "IPythonScriptPlugin.h"

/** Python stays available for authoring, PIE and commandlets. A standalone -game
 * process has no Python gameplay and must not carry its full GC/wrapper graph. */
class FFPSStandaloneRuntime : public IModuleInterface
{
    FDelegateHandle TickHandle;
public:
    virtual void StartupModule() override
    {
        if (GIsEditor || IsRunningCommandlet()) return;
        // Python initializes at PostEngineInit too. Waiting for the first game
        // tick avoids depending on the ordering of startup module/delegate calls.
        TickHandle=FWorldDelegates::OnWorldTickStart.AddRaw(this,&FFPSStandaloneRuntime::FirstGameTick);
    }
    void FirstGameTick(UWorld* World,ELevelTick,float)
    {
        if (!World || World->WorldType!=EWorldType::Game) return;
        auto* Python=FModuleManager::GetModulePtr<IPythonScriptPlugin>(TEXT("PythonScriptPlugin"));
        // The first world's tick can precede Python's deferred startup scripts.
        // Keep the callback until initialization finishes; otherwise its wrappers
        // remain registered with every subsequent native garbage collection.
        if (!Python || !Python->IsPythonConfigured()) return;
        if (Python->IsPythonAvailable())
        {
            if (!Python->IsPythonInitialized()) return;
            Python->ForceDisablePythonAtRuntime();
            UE_LOG(LogTemp,Display,TEXT("GAME_RUNTIME released editor Python interpreter before gameplay"));
        }
        FWorldDelegates::OnWorldTickStart.Remove(TickHandle);TickHandle.Reset();
    }
    virtual void ShutdownModule() override
    {
        FWorldDelegates::OnWorldTickStart.Remove(TickHandle);
    }
};
IMPLEMENT_MODULE(FFPSStandaloneRuntime,FPSStandaloneRuntime)
