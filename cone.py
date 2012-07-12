import itertools
from pyopengles import *
from math import *

def eglshorts(L):
    """Converts a tuple to an array of eglshorts (would a pointer return be better?)"""
    return (eglshort*len(L))(*L)

class Buffer(object):
    """Hold a pair of Buffer Objects to draw a part of a model"""
    def __init__(self,pts,faces):
        """Generate a vertex buffer to hold data and indices"""
        pts=[tuple(p) for p in pts]
        normals=[[] for p in pts]
        for f in faces:
            a,b,c=f[0:3]
            n=tuple(vec_normal(vec_cross(vec_sub(pts[b],pts[a]),vec_sub(pts[c],pts[a]))))
            for x in f[0:3]:
                normals[x].append(n) 
        for i,N in enumerate(normals):
            if len(N)==0:
                normals[i]=(0,0,.01)
                continue
            s=1.0/len(N)
            normals[i]=tuple( vec_normal( [sum(v[k] for v in N) for k in range(3)] ) )
        P=[ p+n for p,n in zip(pts,normals)]
        X=eglfloats([x for x in itertools.chain(*P)])

        P=[f[0:3] for f in faces]
        E=eglshorts([x for x in itertools.chain(*P)])
        
        self.vbuf=eglint()
        opengles.glGenBuffers(1,ctypes.byref(self.vbuf))
        self.ebuf=eglint()
        opengles.glGenBuffers(1,ctypes.byref(self.ebuf))
        self.select()
        opengles.glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(X), ctypes.byref(X), GL_STATIC_DRAW);
        opengles.glBufferData(GL_ELEMENT_ARRAY_BUFFER, ctypes.sizeof(E), ctypes.byref(E), GL_STATIC_DRAW);
        self.ntris = len(faces)
       
    def select(self):
        """Makes our buffers active"""
        opengles.glBindBuffer(GL_ARRAY_BUFFER, self.vbuf);
        opengles.glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebuf);
        
    def draw(self,s):
        self.select()
        opengles.glVertexAttribPointer(s.attr_normal, 3, GL_FLOAT, 0, 24, 12);
        opengles.glVertexAttribPointer(s.attr_vertex, 3, GL_FLOAT, 0, 24, 0);
        opengles.glEnableVertexAttribArray(s.attr_normal);
        opengles.glEnableVertexAttribArray(s.attr_vertex);
        opengles.glDrawElements ( GL_TRIANGLES, self.ntris*3, GL_UNSIGNED_SHORT, 0 );

            
class Shader(object):
    def __init__(self):
        """Prepares a shader for 3d point + normal"""

        self.vshader_source = ctypes.c_char_p(
              """
              attribute vec3 vertex;
              attribute vec3 normal;
              uniform mat4 view;
              varying vec3 n;
              void main(void) {
                //light = 0.5+max(0.0,0.5*dot(normal,vec3(0.7,0,0.7)));
                n=normal;
                gl_Position = view * vec4(vertex,1.0);
              }""")
      
        self.fshader_source = ctypes.c_char_p(
              """
              varying vec3 n;
              void main(void) {
                 gl_FragColor = vec4(n.x+0.5,n.y+0.5,n.z+0.5,1.0);
              }""")

        vshader = opengles.glCreateShader(GL_VERTEX_SHADER);
        opengles.glShaderSource(vshader, 1, ctypes.byref(self.vshader_source), 0)
        opengles.glCompileShader(vshader);
        self.showlog(vshader)

        fshader = opengles.glCreateShader(GL_FRAGMENT_SHADER);
        opengles.glShaderSource(fshader, 1, ctypes.byref(self.fshader_source), 0);
        opengles.glCompileShader(fshader);
        self.showlog(fshader);

        program = opengles.glCreateProgram();
        opengles.glAttachShader(program, vshader);
        opengles.glAttachShader(program, fshader);
        opengles.glLinkProgram(program);
        self.showprogramlog(program);

        self.program = program
        self.attr_vertex = opengles.glGetAttribLocation(program, "vertex");
        self.attr_normal = opengles.glGetAttribLocation(program, "normal");
        self.unif_view = opengles.glGetUniformLocation(program, "view");
        self.select()

    def select(self):
        """Makes this shader active"""
        opengles.glUseProgram ( self.program );

    def select_view(self,M,M_reflect=None):
        """Call this to program the view matrix.
        """
        E=eglfloats(list(itertools.chain(*M)))
        opengles.glUniformMatrix4fv(self.unif_view,16,eglint(0),ctypes.byref(E));
        
    def showlog(self,shader):
        """Prints the compile log for a shader"""
        N=1024
        log=(ctypes.c_char*N)()
        loglen=ctypes.c_int()
        opengles.glGetShaderInfoLog(shader,N,ctypes.byref(loglen),ctypes.byref(log))
        print log.value

    def showprogramlog(self,shader):
        """Prints the compile log for a program"""
        N=1024
        log=(ctypes.c_char*N)()
        loglen=ctypes.c_int()
        opengles.glGetProgramInfoLog(shader,N,ctypes.byref(loglen),ctypes.byref(log))
        print log.value

class View(object):
    """The view holds the perspective transformations for the current view.
    Call lookAt to set the camera.
    Call begin_matrix to start a new view based on this perspective, then translate or rotate to set up transform.
    Can use view.V to access the matrix representing the current transform"""
    
    def lookAt(self,at,eye):
        """Set up view matrix to look from eye to at including perspective"""
        self.L=LookAtMatrix(at,eye)
        self.P=ProjectionMatrix()
        self.M=mat_mult(self.L,self.P) # Apply transform/rotation first, then shift into perspective space
        self.L_reflect=LookAtMatrix(at,eye,reflect=True)
        self.M_reflect=mat_mult(self.L_reflect,self.P)

    def begin_matrix(self):
        self.V = [row[:] for row in self.M]

    def translate(self,pt):
        """Move an object to the given location"""
        V=self.V
        V[3]=[sum(pt[j]*V[j][i] for j in xrange(3))+V[3][i] for i in xrange(4)]

    def rotate(self,angle):
        """Rotate an object by an angle in degrees"""
        c=math.cos(angle*3.1415/180.0)
        s=math.sin(angle*3.1415/180.0)
        M=[[c,s,0,0],[-s,c,0,0],[0,0,1,0],[0,0,0,1]]
        self.V=mat_mult(M,self.V)
        
class Cone:
    
    def __init__(self,sz=20.0,numsides=20):
        """Prepares vertices and faces for a cone.  Both sides of each face are drawn"""
        pts = []
        faces = []
        for a in range(numsides):
            x=sz*math.sin(2*3.14159*a/numsides)
            y=sz*math.cos(2*3.14159*a/numsides)
            pts.append((x,y,0))
            faces.append((numsides,(a+1)%numsides,a))
        pts.append((0.0,0.0,sz))
        self.buf=Buffer(pts,faces)
        self.pts=pts
        self.faces=faces

    def draw(self,s):
        self.buf.draw(s)

def TranslateMatrix(pt):
    M=[[0]*4 for i in range(4)]
    for i in range(4):
        M[i][i]=1.0
    for i in range(3):
        M[3][i]=pt[i]
    return M

def ProjectionMatrix(near=10,far=1000.0,fov_h=1.7,fov_v=1.4):
    """Setup projection matrix with given distance to near and far planes
    and fields of view in radians"""
    # Matrices are considered to be M[row][col]
    # Use DirectX convention, so need to do rowvec*Matrix to transform
    w=1./tan(fov_h*0.5)
    h=1./tan(fov_v*0.5)
    Q=far/(far-near)
    M=[[0]*4 for i in range(4)]
    M[0][0]=w
    M[1][1]=h
    M[2][2]=Q
    M[3][2]=-Q*near
    M[2][3]=1
    return M

def vec_sub(A,B):
    return [a-b for a,b in zip(A,B)]

def vec_dot(A,B):
    return sum(a*b for a,b in zip(A,B))

def vec_cross(a,b):
    return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
    
def vec_normal(A):
    n=math.sqrt(sum(a**2 for a in A))+0.0001
    return [a/n for a in A]

def LookAtMatrix(at,eye,up=[0,0,1],reflect=False):
    """Define a matrix of an eye looking at"""
    # If reflect, then reflect in plane -20.0 (water depth)
    if reflect:
        depth=-20.0 # Shallower to avoid edge effects
        eye[2]=2*depth-eye[2]
        at[2]=2*depth-at[2] 
    zaxis = vec_normal(vec_sub(at,eye))
    xaxis = vec_normal(vec_cross(up,zaxis))
    yaxis = vec_cross(zaxis,xaxis)
    xaxis.append(-vec_dot(xaxis,eye))
    yaxis.append(-vec_dot(yaxis,eye))
    zaxis.append(-vec_dot(zaxis,eye))
    z=[0,0,0,1.0]
    return [ [xaxis[a],yaxis[a],zaxis[a],z[a]] for a in range(4)]

def BillboardMatrix():
    """Define a matrix that copies x,y and sets z to 0.9"""
    return [ [1.0,0.0,0.0,0.0],[0.0,1.0,0.0,0.0],[0.0,0.0,0.0,0.0],[0.0,0.0,0.9,1.0]]

def mat_mult(A,B):
    return [ [ sum(A[i][j]*B[j][k] for j in range(4)) for k in range(4)] for i in range(4)]

def mat_transpose(A):
    return [ [ A[k][i] for k in range(4)] for i in range(4)]

def vec_mat_mult(A,B):
    return [ sum(A[j]*B[j][k] for j in range(4)) for k in range(4)]


egl = EGL()
cone = Cone(50);
s = Shader()
v = View()
opengles.glViewport ( 0, 0, egl.width, egl.height );
opengles.glDepthRangef(eglfloat(-1.0),eglfloat(1.0))
opengles.glClearColor ( eglfloat(0.3), eglfloat(0.3), eglfloat(0.7), eglfloat(1.0) );
opengles.glBindFramebuffer(GL_FRAMEBUFFER,0)
opengles.glFrontFace(GL_CW)
opengles.glCullFace(GL_BACK)
opengles.glEnable(GL_CULL_FACE)
opengles.glEnable(GL_DEPTH_TEST)

print 'Setup viewport'
v.lookAt([0,0,0],[0,-100,50])

from pymouse import start_mouse

m=start_mouse()

frame=0
def draw(s):
    global frame
    frame+=1

    opengles.glBindFramebuffer(GL_FRAMEBUFFER,0)
    opengles.glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
    s.select()
    s.select_view(v.M)
    v.begin_matrix()
    v.rotate(frame*2)
    s.select_view(v.V)
    cone.draw(s)
    opengles.glFinish()  
    openegl.eglSwapBuffers(egl.display, egl.surface)

while 1:
    if m.finished:
         break
    draw(s)
    
m.stop()
