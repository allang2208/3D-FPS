"""Padded tongue, open throat and riveted eyelets of the TS01 coyote high boot."""
import numpy as np
from shapely.geometry import Point

from ridge_boots_author_surface import TAU, arr, collar, ease, last, normal, poly, surf, unit


def tongue_top(t):
    return 29.75-.88*(np.abs(t)/.71)**1.7


def tongue_surface(t,z,h=0.):
    t,z=np.broadcast_arrays(t,z)
    # A folded bellow near the throat gives way to a thick padded crown.
    edge=np.minimum(1.,abs(t)/.74)
    dome=(.11+.28*ease((z-6.1)/7.)+.22*ease((z-24.5)/3.6))*(1.-.64*edge*edge)
    point=surf(t,z,dome+h)
    # Curve the free tongue towards the shin above the last pair of eyelets.
    point[...,1]-=.72*ease((z-26.75)/3.)*(1.-.42*edge)
    return point


def open_upper(b):
    def shell(u,v):
        t=u*TAU
        z=2.45+(collar(t)-2.45)*v
        for _ in range(2):
            gap=.48*ease((z-5.85)/5.5)
            t=gap+(TAU-2*gap)*u
            z=2.45+(collar(t)-2.45)*v
        return surf(t,z,.008)
    b.grid('woven_quarters_and_vamp','Textile',shell,89,54)

    def tongue(u,v,inside=False):
        t=(u-.5)*1.48
        z=5.28+(tongue_top(t)-5.28)*v
        return tongue_surface(t,z,-.52 if inside else 0.)
    b.grid('padded_bellows_tongue','Textile',tongue,33,59)
    b.grid('tongue_inside_face','Lining',lambda u,v:tongue(u,v,True),27,29,
           lambda u,v:-normal((u-.5)*1.48,5.28+(tongue_top((u-.5)*1.48)-5.28)*v))
    def crown(u,v):
        t=(u-.5)*1.48
        a=v*np.pi
        return tongue_surface(t,tongue_top(t)+.25*np.sin(a),-.26+.26*np.cos(a))
    b.grid('folded_tongue_crown','Suede',crown,37,13,
           lambda u,v:normal((u-.5)*1.48,tongue_top((u-.5)*1.48))*np.cos(v*np.pi)[...,None]+arr(u*0,u*0,np.sin(v*np.pi)))
    for sign in [-1,1]:
        def sidewall(u,v):
            t=u*0+sign*.74
            z=5.28+(tongue_top(t)-5.28)*v
            return tongue_surface(t,z,-.52*u)
        b.grid('tongue_side_binding_'+str(sign),'Lining',sidewall,3,51,
               lambda u,v:unit(last(sign*.75,5.28+23.5*v)-last(sign*.73,5.28+23.5*v)))
    def keeper(u,v):
        t=(u-.5)*.85;z=24.9+.67*v+.15*(2*u-1)**2
        return tongue_surface(t,z,.04+.24*np.sin(u*np.pi))
    b.grid('upper_tongue_lace_keeper','Suede',keeper,23,5)

    def padded(u,v):
        t=.64+(TAU-1.28)*u;rear=(1.-np.cos(t))*.5
        z0=15.9-2.45*rear
        z=z0+(collar(t)-z0)*v
        compression=np.zeros_like(z)
        for line in (19.74,24.05):
            compression+=.32*np.exp(-((z-(line-3.04*rear))/.27)**2)
        lift=.15+(.52-compression)*ease(v/.095)*ease((1-v)/.14)
        return surf(t,z,lift)
    b.grid('quilted_achilles_cushion','Textile',padded,85,67)
    def lining(u,v):
        t=.44+(TAU-.88)*u
        z=collar(t)-4.2*(1.-v)
        return surf(t,z,-.46)
    b.grid('interior_collar_lining','Lining',lining,71,10,
           lambda u,v:-normal(.44+(TAU-.88)*u,collar(.44+(TAU-.88)*u)-4.2*(1-v)))
    # A hem only follows the cut sides/back. The front remains open for the tongue.
    def lip(u,v):
        t=.45+(TAU-.90)*u
        a=v*np.pi
        return surf(t,collar(t)+.23*np.sin(a),-.15+.32*np.cos(a))
    b.grid('turned_collar_lip','Textile',lip,75,11,
           lambda u,v:normal(.45+(TAU-.90)*u,collar(.45+(TAU-.90)*u))*np.cos(v*np.pi)[...,None]+arr(u*0,u*0,np.sin(v*np.pi)))


def lacing(b):
    rows=[(6.95,.55),(8.25,.62),(10.05,.73),(13.15,.82),
          (16.60,.88),(20.82,.88),(25.03,.84)]
    guides={}
    a=np.linspace(0,TAU,32,endpoint=False)
    for i,(z,theta) in enumerate(rows):
        for flank in (-1,1):
            t=flank*theta
            n=normal(t,z)
            along=unit(last(t+.008*flank,z)-last(t-.008*flank,z))
            along=unit(along-n*np.dot(along,n))
            up=unit(np.cross(along,n))
            if up[2]<0:up=-up
            center=surf(t,z,.78 if i>=4 else (.51 if i==3 else .32))
            name=str(flank)+'_'+str(i)
            def plane(q,h):
                return center+q[:,0,None]*along+q[:,1,None]*up+np.broadcast_to(h,len(q))[:,None]*n
            if i<3:
                # The woven tab lies over the cord, then returns to the quarter.
                def bridge(u,v):
                    qx=-.68+1.67*u
                    qy=(v-.5)*.59+.38*qx
                    lift=.015+.42*np.exp(-((qx+.38)/.31)**2)
                    return center+qx[...,None]*along+qy[...,None]*up+lift[...,None]*n
                b.grid('quarter_webbing_tunnel_'+name,'Textile',bridge,15,6,n)
                for border in (0.,1.):
                    u=np.linspace(0,1,15)
                    b.tube('rolled_guide_edge_'+name+str(border),'Textile',bridge(u,u*0+border),.052,6)
                guides[i,flank]=center-.42*along-.15*up+n*.20
            else:
                # Closed cast guide with a solid rivet pad and a raised nose.
                lock=(i==3)
                pan=poly([(-.77,-.28),(-.83,.12),(-.61,.33),(-.06,.31),
                          (.37,.43),(.69,.34),(.81,.12),(.79,-.23),
                          (.59,-.43),(.29,-.42),(-.06,-.26)],.12)
                if lock:
                    pan=pan.difference(Point(-.47,.02).buffer(.175,quad_segs=8))
                b.panel('riveted_eyelet_body_'+name,'Hardware',pan,plane,.18,.10,.18,.08)
                lens_center=center+.47*along
                def rivet(u,v):
                    theta=u*TAU
                    r=.315*(.01+.99*v)
                    h=.20+.14*np.maximum(0,1-v**2)**.6
                    return lens_center+(r*np.cos(theta))[...,None]*along+(r*np.sin(theta))[...,None]*up+h[...,None]*n
                b.grid('solid_eyelet_rivet_'+name,'Hardware',rivet,21,6,n)
                b.tube('eyelet_rivet_rim_'+name,'Hardware',lens_center+.326*np.cos(a)[:,None]*along+
                       .326*np.sin(a)[:,None]*up+.18*n,.045,6,True)
                path=center+(-.54-.13*np.sin(a))[:,None]*along+.29*np.cos(a)[:,None]*up+(.28+.26*np.sin(a))[:,None]*n
                b.tube('closed_cast_lace_port_'+name,'Hardware',path,.119,8,True)
                guides[i,flank]=center-.63*along+n*.29
    for i in range(len(rows)-1):
        z0,t0=rows[i];z1,t1=rows[i+1]
        for s in (-1,1):
            u=np.linspace(0,1,30)
            z=z0+(z1-z0)*u
            t=s*(t0*(1-u)-t1*u)
            height=.17+(.28 if s>0 else .00)*np.sin(np.pi*u)**5
            path=tongue_surface(t,z,height)
            path+=((1-u)**4)[:,None]*(guides[i,s]-path[0])+((u**4)[:,None])*(guides[i+1,-s]-path[-1])
            b.tube('braided_cross_lace_'+str(i)+'_'+str(s),'Lace',path,.166,10)
    u=np.linspace(0,1,24);t=(2*u-1)*rows[0][1];z=u*0+rows[0][0]
    path=tongue_surface(t,z,.17)
    path+=((1-u)**4)[:,None]*(guides[0,-1]-path[0])+(u**4)[:,None]*(guides[0,1]-path[-1])
    b.tube('toe_lace_bridge','Lace',path,.166,10)
    for s in (-1,1):
        t=s*np.array([.81,.76,.63,.46,.27,.14,.08,.10,.20,.31,.42])
        z=np.array([25.03,25.30,25.65,25.91,25.95,25.70,25.15,24.82,24.71,24.89,25.13])
        path=tongue_surface(t,z,.16);path[0]=guides[len(rows)-1,s]
        b.tube('tucked_lace_end_'+str(s),'Lace',path,.158,9)
