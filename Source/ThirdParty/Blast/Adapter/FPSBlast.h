#pragma once
#include <stdint.h>

// Plain ABI isolates the pinned NVIDIA internal API, alignment and allocator
// from Unreal. Units are metres, kg, seconds, N and N*m.
struct FPSBlastNode { float position[3]; float mass; float inertia; float acceleration[3]; };
struct FPSBlastBond { uint32_t nodes[2]; float centroid[3]; };
struct FPSBlastForce { float linear[3]; float angular[3]; };
extern "C" bool FPSBlastSolve(const FPSBlastNode* nodes, uint32_t nodeCount,
    const FPSBlastBond* bonds, uint32_t bondCount, uint32_t iterations, FPSBlastForce* forces);
