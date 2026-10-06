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



RADII=[.040,.053,.059,.054,.066,.071,.078,.073,.088,.094]
HEIGHTS=[.030,.010,.008,.025,.008,-.014,-.016,.005,-.015,-.035]

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


def _sub(a,b):return tuple(x-y for x,y in zip(a,b))
def _dot(a,b):return sum(x*y for x,y in zip(a,b))
def _norm(a):return math.sqrt(_dot(a,a))

def segment_distance(a,b,c,d):
    # Exact minimum between3D segments with clamped closest parameters.
    u=_sub(b,a);v=_sub(d,c);w=_sub(a,c);A=_dot(u,u);B=_dot(u,v);C=_dot(v,v);D=_dot(u,w);E=_dot(v,w);den=A*C-B*B
    s=max(0,min(1,(B*E-C*D)/den))if den>1e-20 else 0
    t=max(0,min(1,(B*s+E)/C))
    s=max(0,min(1,(B*t-D)/A))
    t=max(0,min(1,(B*s+E)/C))
    return _norm(tuple(w[i]+u[i]*s-v[i]*t for i in range(3)))

