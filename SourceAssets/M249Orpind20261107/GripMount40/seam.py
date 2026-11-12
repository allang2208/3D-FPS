"""Partition the joined lower housing on existing source edges at the grip root."""
import numpy as np
import networkx as nx


def grip_faces(positions, faces, trigger):
    points = positions[faces] * 100
    center = points.mean(axis=1)
    # Labels are fixed on the trigger guard, grip body and upper housing.
    # Only the narrow transition at the top of the grip needs an edge cut.
    before = (center[:, 0] > 12.7) & (center[:, 2] < -6.3) & ~trigger
    grip = before | ((points[:, :, 0].min(1) > 11.4) & (points[:, :, 2].max(1) < -4.65))
    housing = (points[:, :, 0].min(1) < 10.6) | (points[:, :, 2].min(1) > -3.1) | (center[:, 0] > 20.5) | trigger
    verts, welded = np.unique(np.round(positions * 100, 4), axis=0, return_inverse=True)
    edges = {}
    for i, tri in enumerate(welded[faces]):
        for a, b in zip(tri, np.roll(tri, -1)):
            edges.setdefault(tuple(sorted((a, b))), []).append(i)
    graph = nx.Graph()
    for i in range(len(faces)):
        graph.add_node(i)
        if grip[i]:
            graph.add_edge('grip', i, capacity=1e7)
        elif housing[i]:
            graph.add_edge('housing', i, capacity=1e7)
    for (u, v), adjacent in edges.items():
        if len(adjacent) != 2:
            continue
        a, b = verts[[u, v]]
        cost = np.linalg.norm(b-a) * (1 + 4 * ((a[2]+b[2])*.5+4.0)**2)
        graph.add_edge(*adjacent, capacity=float(cost))
    _, (picked, _) = nx.minimum_cut(graph, 'grip', 'housing')
    return np.array([i in picked for i in range(len(faces))]) & ~trigger
