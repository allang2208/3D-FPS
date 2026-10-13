#pragma once
#include <cstdint>
#include <vector>

// Pure bounded grid planner, shared by the world mesh and standalone offline checks.
// Rectangles cover only occupied cells; edges include holes and disconnected islands.
namespace WoodworkingStockGeometry
{
struct FRect { int X0,Y0,X1,Y1; };
struct FEdge { int X0,Y0,X1,Y1,NX,NY; };
struct FPlan
{
    std::vector<FRect> Faces;
    std::vector<FEdge> Edges;
    int Area=0,Perimeter=0;
    bool Valid=false;
};
constexpr int MaximumCells=768*512;
constexpr int MaximumQuads=65536;
FPlan Plan(const uint8_t* Cells,int Count,int Width,int Height);
}
