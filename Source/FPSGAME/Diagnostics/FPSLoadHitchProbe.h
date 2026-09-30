// Sync-load hitch probe (2026-09-21).
//
// The DayNight/L_Dungeon captures show 170-780 ms game-thread stalls whose cost
// lives in Exclusive/GameThread/FlushAsyncLoading and
// FileIO/GameThread/AsyncLoadingTime. CsvProfiler cannot say *which* package was
// loaded or which code asked for it, so this probe records both:
//
//   * timing around FCoreDelegates::OnSyncLoadPackage, which UObjectGlobals
//     broadcasts for game-thread synchronous loads, and
//   * the caller's callstack (module + offset) for loads above a threshold.
//
// Off by default. Enable for a diagnostic run with:
//   -ExecCmds="fps.diag.LoadHitch 1"
// Evidence is written to Saved/Profiling/LoadHitch/<profile>.log and is not part
// of normal gameplay.

#pragma once

#include "CoreMinimal.h"

struct FPSGAME_API FFPSLoadHitchProbe
{
    /** Binds the sync-load hook and the per-frame evidence flush. */
    static void Startup();

    /** Unbinds and flushes the evidence file. */
    static void Shutdown();

    /** Called once per game-thread frame to close the load opened since the last tick. */
    static void Tick();
};