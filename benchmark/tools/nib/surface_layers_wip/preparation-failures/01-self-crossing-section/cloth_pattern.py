"""Pure source pattern, shared by native creation and lightweight preflight."""
import math

def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)


def hermite(values,t):
    """Cubic cardinal interpolation, no discontinuous ridge or normal step."""
    u=t*(len(values)-1);i=min(len(values)-2,int(u));s=u-i
    a=values[i];b=values[i+1]
    ma=(values[i+1]-values[max(i-1,0)])*.5
    mb=(values[min(i+2,len(values)-1)]-values[i])*.5
    return (2*s**3-3*s*s+1)*a+(s**3-2*s*s+s)*ma+(-2*s**3+3*s*s)*b+(s**3-s*s)*mb



RADII=[.042,.050,.060,.051,.064,.078,.067,.087,.095]
HEIGHTS=[.027,.019,.006,.017,-.005,-.021,-.005,-.029,-.040]

def point(angle,v):
    front=max(0,-math.sin(angle));back=max(0,math.sin(angle))
    shift=.043*math.sin(angle+.55)+.021*math.sin(2*angle-1.1)
    section=max(0,min(1,v+shift*math.sin(math.pi*v)))
    radius=hermite(RADII,section)
    z=1.010+hermite(HEIGHTS,section)-front**1.3*(.020+.009*math.sin(angle+.35))
    z+=back*.005+.0045*math.sin(angle*2+.8+v*1.2)*math.sin(math.pi*v)
    gather=(.40+.60*back)*(math.sin(math.pi*v)**.8)
    radius+=gather*(.0015*math.sin(9*angle+4*v)+.0008*math.sin(17*angle-5*v))
    return (math.cos(angle)*radius*1.06,.008+math.sin(angle)*radius,z)
