#pragma once

/** Keeps the editor's purged NULL scene from running real GPU particle dispatches. */
struct FFPSNiagaraSceneLifecycle
{
    static void Startup();
    static void Shutdown();
};
