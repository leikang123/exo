from __future__ import annotations

import sys

sys.path.append(sys.path[0] + "/..")
from SYS_ATL import DRAM
from SYS_ATL.libs.memories import AVX2
from .x86 import loadu, storeu, mul

sys.path.append(sys.path[0] + "/.")
from .helper import *

import platform
import pytest
if platform.system() == 'Darwin':
    pytest.skip("skipping x86 tests on Apple machines for now",
                allow_module_level=True)

def test_avx2_memcpy():
    """
    Compute dst = src
    """

    @proc
    def memcpy_avx2(n: index, dst: R[n] @ DRAM, src: R[n] @ DRAM):  # pragma: no cover
        assert n > 0
        for i in par(0, (n + 7) / 8):
            if n - 8 * i >= 8:
                tmp: f32[8] @ AVX2
                loadu(tmp, src[8 * i:8 * i + 8])
                storeu(dst[8 * i:8 * i + 8], tmp)
            else:
                for j in par(0, n - 8 * i):
                    dst[8 * i + j] = src[8 * i + j]

    basename = test_avx2_memcpy.__name__

    with open(os.path.join(TMP_DIR, f'{basename}_pretty.atl'), 'w') as f:
        f.write(str(memcpy_avx2))

    memcpy_avx2.compile_c(TMP_DIR, basename)

    # TODO: -march=skylake here is a hack. Such flags should be somehow handled automatically.
    #       Maybe this should be inferred by the use of AVX2, but "skylake" isn't right anyway.
    #       We might need a first-class notion of a Target, which has certain memories available.
    #       Then we can say that e.g. Skylake-X has AVX2, AVX512, etc.
    library = generate_lib(basename, extra_flags="-march=skylake")

    for n in (7, 8, 9, 31, 32, 33, 127, 128, 129):
        inp = nparray([float(i) for i in range(n)])
        out = nparray([float(0) for _ in range(n)])
        library.memcpy_avx2(POINTER(c_int)(), n, cvt_c(out), cvt_c(inp))

        assert np.array_equal(inp, out)


def test_avx2_simple_math():
    """
    Compute x = x * y^2
    """

    @proc
    def simple_math_avx2(n: index, x: R[n] @ DRAM, y: R[n] @ DRAM):  # pragma: no cover
        assert n > 0
        assert n % 8 == 0
        for i in par(0, n / 8):
            xVec: f32[8] @ AVX2
            yVec: f32[8] @ AVX2
            loadu(xVec, x[8 * i:8 * i + 8])
            loadu(yVec, y[8 * i:8 * i + 8])
            mul(xVec, xVec, yVec)
            mul(xVec, xVec, yVec)
            storeu(x[8 * i:8 * i + 8], xVec)

    basename = test_avx2_simple_math.__name__

    with open(os.path.join(TMP_DIR, f'{basename}_pretty.atl'), 'w') as f:
        f.write(str(simple_math_avx2))

    simple_math_avx2.compile_c(TMP_DIR, basename)
    library = generate_lib(basename, extra_flags="-march=skylake")

    for n in (8, 16, 24, 32, 64, 128):
        x = nparray([float(i) for i in range(n)])
        y = nparray([float(3 * i) for i in range(n)])
        expected = x * y * y

        library.simple_math_avx2(POINTER(c_int)(), n, cvt_c(x), cvt_c(y))
        assert np.allclose(x, expected)


def test_avx2_simple_math_scheduling():
    """
    Compute x = x * y^2
    """

    @proc
    def simple_math_avx2_scheduling(n: index, x: R[n] @ DRAM, y: R[n] @ DRAM):  # pragma: no cover
        assert n > 0
        for i in par(0, n):
            # TODO: replace this with x[i] = x[i] * y[i] * y[i] and then use bind_expr
            x[i] += x[i] * y[i] * y[i]

    def pre_bake_staged_memory(_):
        @proc
        def simple_math_avx2_scheduling(n: index, x: R[n] @ DRAM, y: R[n] @ DRAM):
            assert n > 0
            for io in par(0, n / 8):
                yVec: f32[8] @ DRAM
                xVec: f32[8] @ DRAM
                for ii in par(0, 8):
                    yVec[ii] = y[8 * io + ii]
                for ii in par(0, 8):
                    xVec[ii] = x[8 * io + ii]
                for ii in par(0, 8):
                    xVec[ii] = xVec[ii] * yVec[ii]
                for ii_1 in par(0, 8):
                    xVec[ii_1] = xVec[ii_1] * yVec[ii_1]
                for ii in par(0, 8):
                    x[8 * io + ii] = xVec[ii]
            if n % 8 > 0:
                for ii_2 in par(0, n % 8):
                    x[ii_2 + n / 8 * 8] = x[ii_2 + n / 8 * 8] * y[ii_2 + n / 8 * 8]
                    x[ii_2 + n / 8 * 8] = x[ii_2 + n / 8 * 8] * y[ii_2 + n / 8 * 8]

        return simple_math_avx2_scheduling

    def pre_bake_cse(_):
        @proc
        def simple_math_avx2_scheduling(n: index, x: R[n] @ DRAM, y: R[n] @ DRAM):
            assert n > 0
            for io in par(0, n / 8):
                xy: R[8] @ AVX2
                xVec: R[8] @ AVX2
                loadu(xVec, x[8 * io + 0:8 * io + 8])
                yVec: R[8] @ AVX2
                loadu(yVec, y[8 * io + 0:8 * io + 8])
                mul(xy, xVec, yVec)
                for ii in par(0, 8):
                    x[8 * io + ii] += xy[ii] * yVec[ii]
            if n % 8 > 0:
                for ii_1 in par(0, n % 8):
                    x[ii_1 + n / 8 * 8] = x[ii_1 + n / 8 * 8] * y[ii_1 + n / 8 * 8] * y[ii_1 + n / 8 * 8]

        return simple_math_avx2_scheduling

    print()
    print()

    simple_math_avx2_scheduling = simple_math_avx2_scheduling.split('i', 8, ['io', 'ii'], tail='cut_and_guard')

    simple_math_avx2_scheduling = simple_math_avx2_scheduling.bind_expr('xy', 'x[_] * y[_]')
    simple_math_avx2_scheduling = simple_math_avx2_scheduling.lift_alloc('xy : _ #0')
    simple_math_avx2_scheduling = simple_math_avx2_scheduling.set_memory('xy', AVX2)

    simple_math_avx2_scheduling = simple_math_avx2_scheduling.bind_expr('xVec', 'x[_]')
    simple_math_avx2_scheduling = simple_math_avx2_scheduling.lift_alloc('xVec : _ #0')
    simple_math_avx2_scheduling = simple_math_avx2_scheduling.set_memory('xVec', AVX2)

    simple_math_avx2_scheduling = simple_math_avx2_scheduling.fission_after('xVec[_] = _')

    simple_math_avx2_scheduling = simple_math_avx2_scheduling.bind_expr('yVec', 'y[_]')
    simple_math_avx2_scheduling = simple_math_avx2_scheduling.lift_alloc('yVec : _ #0')
    simple_math_avx2_scheduling = simple_math_avx2_scheduling.set_memory('yVec', AVX2)

    simple_math_avx2_scheduling = simple_math_avx2_scheduling.fission_after('yVec[_] = _')

    simple_math_avx2_scheduling = simple_math_avx2_scheduling.fission_after('xy[_] = _')

    simple_math_avx2_scheduling = simple_math_avx2_scheduling.replace_all(loadu, 'for _ in _: _')

    # simple_math_avx2_scheduling = pre_bake_cse(simple_math_avx2_scheduling)

    print(simple_math_avx2_scheduling)
    print()

    # TODO: need a scheduling directive that stages memory.
    simple_math_avx2_scheduling = pre_bake_staged_memory(simple_math_avx2_scheduling)

    simple_math_avx2_scheduling = simple_math_avx2_scheduling.set_memory('xVec', AVX2)
    simple_math_avx2_scheduling = simple_math_avx2_scheduling.set_memory('yVec', AVX2)
    # TODO: add "replace all" or "replace many" directive
    simple_math_avx2_scheduling = simple_math_avx2_scheduling.replace(loadu, 'for ii in _: _ #0')
    simple_math_avx2_scheduling = simple_math_avx2_scheduling.replace(loadu, 'for ii in _: _ #0')
    simple_math_avx2_scheduling = simple_math_avx2_scheduling.replace(mul, 'for ii in _: _ #0')
    simple_math_avx2_scheduling = simple_math_avx2_scheduling.replace(mul, 'for ii_1 in _: _ #0')
    simple_math_avx2_scheduling = simple_math_avx2_scheduling.replace(storeu, 'for ii in _: _ #0')

    print(simple_math_avx2_scheduling)

    basename = test_avx2_simple_math_scheduling.__name__

    with open(os.path.join(TMP_DIR, f'{basename}_pretty.atl'), 'w') as f:
        f.write(str(simple_math_avx2_scheduling))

    simple_math_avx2_scheduling.compile_c(TMP_DIR, basename)
    library = generate_lib(basename, extra_flags="-march=skylake")

    for n in (8, 16, 24, 32, 64, 128):
        x = nparray([float(i) for i in range(n)])
        y = nparray([float(3 * i) for i in range(n)])
        expected = x * y * y

        library.simple_math_avx2_scheduling(POINTER(c_int)(), n, cvt_c(x), cvt_c(y))
        assert np.allclose(x, expected)


def test_avx2_sgemm_base():
    """
    compute C += A*B
    """

    @proc
    def sgemm_base(
        m: index,
        n: index,
        p: index,
        A: f32[m, p] @ DRAM,
        B: f32[p, n] @ DRAM,
        C: f32[m, n] @ DRAM,
    ):
        assert n > 0 and m > 0 and p > 0
        for i in par(0, m):
            for j in par(0, n):
                for k in par(0, p):
                    C[i, j] += A[i, k] * B[k, j]

    basename = test_avx2_sgemm_base.__name__

    with open(os.path.join(TMP_DIR, f'{basename}_pretty.atl'), 'w') as f:
        code = str(sgemm_base)
        print(f'\n\n{code}')
        f.write(code)

    sgemm_base.compile_c(TMP_DIR, basename)
