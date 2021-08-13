from __future__ import annotations
import ctypes
from ctypes import *
import os
import sys
import subprocess
import numpy as np
import scipy.stats as st
import pytest
sys.path.append(sys.path[0]+"/..")
from SYS_ATL import proc, Procedure, DRAM, config, instr
from SYS_ATL.libs.memories import GEMM_SCRATCH
sys.path.append(sys.path[0]+"/.")
from .helper import *

# ------- Configuration tests ---------

def new_config_f32():
    @config
    class ConfigAB:
        a : f32
        b : f32

    return ConfigAB

def test_basic_config():
    ConfigAB = new_config_f32()

    @proc
    def foo(x : f32):
        ConfigAB.a  = 32.0
        x           = ConfigAB.a

def test_config_write1():
    ConfigAB = new_config_f32()

    @proc
    def foo(n : size):
        for i in par(0, n):
            ConfigAB.a = 0.0

def test_config_write2():
    ConfigAB = new_config_f32()
    with pytest.raises(TypeError,
                       match='data race conflict with statement'):
        @proc
        def foo(n : size, A : f32[n]):
            a : f32
            for i in par(0, n):
                a = A[i]
                ConfigAB.a = a

@pytest.mark.skip()
def test_config_write3():
    ConfigAB = new_config_f32()

    # TODO: directly assigining A[i] here is an error, because
    # config value cannot be Read...
    @proc
    def foo(n : size, A : f32[n]):
        a : f32
        for i in par(0, n):
            a = A[i]
            ConfigAB.a = a

def test_config_write4():
    ConfigAB = new_config_f32()

    with pytest.raises(TypeError,
                       match="expected 'index' or 'size'"):
        @proc
        def foo():
            assert ConfigAB.a == 0
            pass
                
def test_config_write5():
    ConfigAB = new_config_f32()

    @proc
    def foo(n : size):
        a : f32
        for i in par(0, n):
            a = ConfigAB.a

@pytest.mark.skip() # This should work
def test_config_write6():
    ConfigAB = new_config_f32()

    @proc
    def foo(n : size):
        a : f32
        for i in par(0, n):
            ConfigAB.a = 3.0
            a = ConfigAB.a


def new_config_ld():
    @config
    class ConfigLoad:
        scale : f32
        src_stride : stride

    return ConfigLoad

@pytest.mark.skip()
def test_ld():
    ConfigLoad = new_config_ld()

    _gemm_config_ld_i8   = ("gemmini_extended3_config_ld({src_stride}, "+
                            "{scale}[0], 0, 0);\n")
    @instr(_gemm_config_ld_i8)
    def config_ld_i8(
        scale : f32,
        src_stride : stride
    ):
        ConfigLoad.scale = scale
        ConfigLoad.src_stride = src_stride


    # TODO: How to readon that this ConfigLoad.scale is same as scale in
    # ld_i8?? We need to be able to unify those..
    _gemm_do_ld_i8   = ("gemmini_extended_mvin( {src}.data, "+
                                  "((uint64_t) {dst}.data), {m}, {n} );")
    @instr(_gemm_do_ld_i8)
    def do_ld_i8(
        n     : size,
        m     : size,
        src   : [i8][n, m] @ DRAM,
        dst   : [i8][n, 16] @ GEMM_SCRATCH,
    ):
        assert n <= 16
        assert m <= 16
        assert stride(src, 1) == 1
        assert stride(src, 0) == ConfigLoad.src_stride
        assert stride(dst, 0) == 16
        assert stride(dst, 1) == 1

        for i in par(0, n):
            for j in par(0, m):
                tmp : f32
                tmp      = src[i,j]
                tmp      = tmp * ConfigLoad.scale
                dst[i,j] = tmp #no clamping


    _gemm_ld_i8   = ("gemmini_extended3_config_ld({stride(src, 0)}, "+
                     "{scale}[0], 0, 0);\n"+
                     "gemmini_extended_mvin( {src}.data, "+
                                  "((uint64_t) {dst}.data), {m}, {n} );")
    @instr(_gemm_ld_i8)
    def ld_i8(
        n     : size,
        m     : size,
        scale : f32,
        src   : [i8][n, m] @ DRAM,
        dst   : [i8][n, 16] @ GEMM_SCRATCH,
    ):
        assert n <= 16
        assert m <= 16
        assert stride(src, 1) == 1
        assert stride(dst, 0) == 16
        assert stride(dst, 1) == 1

        for i in par(0, n):
            for j in par(0, m):
                tmp : f32
                tmp      = src[i,j]
                tmp      = tmp * scale
                dst[i,j] = tmp #no clamping

    @proc
    def ld_i8_v2(
        n     : size,
        m     : size,
        scale : f32,
        src   : [i8][n, m] @ DRAM,
        dst   : [i8][n, 16] @ GEMM_SCRATCH,
    ):
        assert n <= 16
        assert m <= 16
        assert stride(src, 1) == 1
        assert stride(dst, 0) == 16
        assert stride(dst, 1) == 1
        # TODO: This assert is not assumed??
        #assert stride(src, 0) == ConfigLoad.src_stride

        config_ld_i8(scale, stride(src, 0))
        do_ld_i8(n, m, src, dst)





"""

def test_config_write3():
    ConfigAB = new_config_f32()
    @proc
    def foo(n : size):
        for i in par(0, n):
            ConfigAB.a = 3.0
            ConfigAB.b = ConfigAB.a



# This is fine
def test_read_write2():
    @proc
    def foo(n : size, A : i8[n]):
        a : i8
        a = 4.0
        for i in par(0, n):
            a    = 0.0
            A[i] = a

    foo.check_effects()



def new_CONFIG_2f32():



@proc
def test_make_config(n: size, dst: R[n] @ DRAM, src: R[n] @ DRAM):
    for i in par(0, (n + 7) / 8):
        if n - 8 * i >= 8:
            pass
        else:
            for j in par(0, n - 8 * i):
                dst[8 * i + j] = src[8 * i + j]



@instr("write_config({a}, {b})")
def set_real_config( a : f32, b : f32):
    REAL_CONFIG.a = a
    REAL_CONFIG.b = b

# st_config_ex
@proc
def set_config_a( a : f32 ):
    DUMMY_CONFIG.a = a
    set_real_config(DUMMY_CONFIG.a, DUMMY_CONFIG.b )

# matmul_config_ex
@proc
def set_config_b( b : f32 ):
    DUMMY_CONFIG.b = b
    set_real_config(DUMMY_CONFIG.a, DUMMY_CONFIG.b )

@instr("mvin...")
def st_i8_v2( ..., stride : stride, ...)
    set_config_a(stride)
    do_st_i8(...)
"""
