#pragma once

// Shared by runtime streaming and the material/PCG authoring bridge, in cm.
// A cell must be generated before its instances become visible, and must not
// be cleaned while those instances can still contribute to the image.
namespace TemperateHillsVisibility
{
struct FLayer { float FadeStart,VisibleEnd,GenerateRadius; };
inline constexpr FLayer Layers[]={
    {20000.f,23000.f,25000.f}, // Trees: explicit canopy fade before cell cleanup.
    {11000.f,16000.f,18000.f}, // Rocks and forest-floor props.
    { 7000.f,11000.f,13000.f}, // Static shrubs.
    { 3500.f, 5000.f, 8000.f}, // Grass: keep visual distance, add 30 m preparation.
    { 4500.f, 7000.f,13000.f}  // Skinned understory shares the shrub graph.
};
inline constexpr float CleanupScale=1.3f;
inline constexpr float DirectionWeight=.15f;
}
