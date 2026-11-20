"""Cut a thumb reinforcement against its native phalanx triangles."""
import numpy as np
import shapely

from coyote_glove_author_surface import Hand


def supported_triangle(q, weights, threshold):
    """Clip one chart triangle at the interpolated phalanx influence."""
    points=[]
    for i in range(3):
        prior=i-1
        a,b=weights[prior],weights[i]
        if (a>=threshold)!=(b>=threshold):
            points.append(q[prior]+(q[i]-q[prior])*((threshold-a)/(b-a)))
        if b>=threshold:
            points.append(q[i])
    return shapely.Polygon(points) if len(points)>=3 else None


def cut_supported_thumb(base,shell,part,mapping,corners):
    # Bent thumb references project both sides of the web into the chart. A single
    # free-triangulated panel can join the two sides of that fold when posed.
    # Retain the original curved pattern on the supported middle phalanx.
    # The continuous native shell carries the visible fabric in the flex zone.
    q=part["uv"]*4
    planar=shapely.polygons(q[part["faces"]])
    pattern=shapely.union_all(planar[shapely.area(planar)>1.e-8])
    chart=Hand(base,part["side"]).digits["thumb"][0]
    bone=next(b["index"] for b in shell.src["bones"] if b["name"]=="thumb_02_"+part["side"])
    weights=np.array([sum(w for j,w in row if j==bone) for row in shell.ws])
    ids=[];coords=[];bary=[];faces=[];heights=[];vertices={}
    for chart_id in sorted(chart.tree.query(pattern,predicate="intersects")):
        origin=chart.faces[chart_id]
        vertex=shell.f[mapping[origin]][corners[origin]]
        w=weights[vertex]
        tri=chart.q[chart_id,:,:2]
        region=supported_triangle(tri,w,.88)
        if region is None or region.area<1.e-8:
            continue
        clipped=region.intersection(pattern)
        for polygon in shapely.get_parts(clipped):
            if polygon.area<1.e-8:
                continue
            for piece in shapely.get_parts(shapely.constrained_delaunay_triangles(polygon)):
                if piece.area<1.e-8:
                    continue
                xy=np.asarray(piece.exterior.coords)[:3]
                coeff=chart.bary(xy,np.full(3,chart_id)).clip(0,1)
                coeff/=coeff.sum(axis=1,keepdims=True)
                edge=shapely.distance(shapely.points(xy),pattern.boundary)
                feather=np.minimum(np.clip(edge/.12,0,1),np.clip((coeff@w-.88)/.045,0,1))
                face=[]
                for point,at,world,height in zip(xy,coeff,coeff@shell.p[vertex],.010+.050*feather):
                    key=tuple(np.round(np.r_[point,world,height],5))
                    if key not in vertices:
                        vertices[key]=len(ids)
                        ids.append(origin);coords.append(point/4);bary.append(at);heights.append(height)
                    face.append(vertices[key])
                if len(set(face))==3:
                    faces.append(face)
    if not faces:
        raise ValueError(f"No native thumb triangles support {shell.rig}/{part['name']}")
    return dict(part,anchor=np.asarray(ids),uv=np.asarray(coords),w=np.asarray(bary),
                height=np.asarray(heights),faces=np.array(faces))
