# Copyright (c) 2012 Peter de Rivaz
#
# This file automatically extracts useful information from the .h header files.
import re
def extract(c_header_name,py_name):
    """Extracts useful information from a .h file into a .py file"""
    with open(py_name,'w') as py:
        with open(c_header_name) as c:
            for line in c.readlines():
                A=line.split()
                if len(A)<3: continue
                if A[0]!='#define': continue
                if A[2][0:2]!= '0x': continue
                print >>py,A[1],'=',A[2]
            

extract('EGL\egl.h','egl.py')
extract('GLES2\gl2.h','gl2.py')
extract('GLES2\gl2ext.h','gl2ext.py')
extract('GLES\gl.h','gl.py')
extract('GLES\glext.h','glext.py')
