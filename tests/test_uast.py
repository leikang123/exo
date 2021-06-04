from __future__ import annotations
import sys
from SYS_ATL import proc, instr, Procedure, DRAM
sys.path.append(sys.path[0]+"/..")

# Merge this file to frontend?

def gen_conv1d():
    @instr("TEST", _testing="UAST")
    def conv1d(n : size, m : size, r: size,
               x : R[n], w : R[m], res : R[r] ):
        for i in par(0,r):
            res[i] = 0.0
        for i in par(0,r):
            for j in par(0,n):
                if i <= j < i + m:
                    res[i] += x[j]*w[i-j+m-1]

    return conv1d

def test_conv1d():
    conv1d = gen_conv1d()
    assert type(conv1d) is Procedure
    print(conv1d)

def gen_alloc_nest():
    @instr("TEST", _testing="UAST")
    def alloc_nest(n : size, m : size,
                   x : R[n,m], y: R[n,m] @ DRAM, res : R[n,m] @ DRAM):
        for i in par(0,n):
            rloc : R[m] @DRAM
            xloc : R[m] @DRAM
            yloc : R[m] @DRAM
            for j in par(0,m):
                xloc[j] = x[i,j]
            for j in par(0,m):
                yloc[j] = y[i,j]
            for j in par(0,m):
                rloc[j] = xloc[j] + yloc[j]
            for j in par(0,m):
                res[i,j] = rloc[j]

    return alloc_nest

def test_alloc_nest():
    alloc = gen_alloc_nest()
    assert type(alloc) is Procedure
    print(alloc)
