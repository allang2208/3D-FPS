#pragma once

/** Drain instanced-skin scene batches before runtime-world resource teardown. */
struct FFPSGameSceneLifecycle
{
    static void Startup();
    static void Shutdown();
};
