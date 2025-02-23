# Module for defining "primitive" operations executable by the nvFuser. This
# list exists to decouple main set of primitives from the ones that provide a
# lowering of the op to nvFuser’s Python interface. Mostly torch.ops.nvprims is
# a subset of the primitives in torch.ops.prims, but some additional primitives
# can be added in the future for the corresponding higher-level torch/aten
# functions.

from typing import Any, Dict, Optional

import torch

from torch._prims_common import (
    DimsSequenceType,
    ELEMENTWISE_TYPE_PROMOTION_KIND,
    getnvFuserDtype,
    ShapeType,
    TensorLikeType,
)

from torch._prims_common.wrappers import (
    backwards_not_supported,
    elementwise_type_promotion_wrapper,
)

nvprim_namespace = "nvprims"
nvprim = torch.library.Library(nvprim_namespace, "DEF")
nvprim_impl = torch.library.Library(
    nvprim_namespace, "IMPL", "CompositeExplicitAutograd"
)
nvprim_implicit_impl = torch.library.Library(
    nvprim_namespace, "IMPL", "CompositeImplicitAutograd"
)
nvprim_autograd_impl = torch.library.Library(nvprim_namespace, "IMPL", "Autograd")
nvprim_meta_impl = torch.library.Library(nvprim_namespace, "IMPL", "Meta")

nvprim_names = [
    "abs",
    "acos",
    "asin",
    "atan",
    "atanh",
    "cos",
    "cosh",
    "bitwise_not",
    "ceil",
    "erf",
    "erfc",
    "exp",
    "expm1",
    "floor",
    "imag",
    "isfinite",
    "lgamma",
    "log",
    "log1p",
    "log2",
    "log10",
    "real",
    "reciprocal",
    "neg",
    "round",
    "rsqrt",
    "sign",
    "sin",
    "sinh",
    "sqrt",
    "tan",
    "tanh",
    "trunc",
    "add",
    "atan2",
    "bitwise_and",
    "bitwise_or",
    "bitwise_xor",
    "div",
    "eq",
    "fmod",
    "ge",
    "gt",
    "le",
    "lt",
    "mul",
    "ne",
    "pow",
    "remainder",
    "sub",
    "broadcast_in_dim",
    "where",
    "convert_element_type",
    "sum",
    "var",
    "amax",
    "amin",
]

_nvfuser_impls: Dict[str, Any] = {}

_nvfuser_unary_ops = {
    "abs",
    "acos",
    "asin",
    "atan",
    "atanh",
    "cos",
    "cosh",
    "bitwise_not",
    "ceil",
    "erf",
    "erfc",
    "exp",
    "expm1",
    "floor",
    "imag",
    "isfinite",
    "lgamma",
    "log",
    "log1p",
    "log2",
    "log10",
    "reciprocal",
    "neg",
    "real",
    "round",
    "rsqrt",
    "sign",
    "sin",
    "sinh",
    "sqrt",
    "tan",
    "tanh",
    "trunc",
}


def _assert_nvfuser_op_exists(fname: str):
    try:
        from torch._C._nvfuser import FusionDefinition as fd  # type: ignore[import]

        assert getattr(fd.Operators, fname)
    except ImportError:
        # Not all PyTorch builds have nvfuser
        pass


for fname in _nvfuser_unary_ops:
    exec(
        f"""
# Ensure that the nvfuser implementation exists
_assert_nvfuser_op_exists("{fname}")

def _{fname}_nvfuser(fd, a):
    return fd.ops.{fname}(a)  # type: ignore[attr-defined]

_nvfuser_impls["{fname}"] = _{fname}_nvfuser
"""
    )

_nvfuser_binary_ops = {
    "add",
    "atan2",
    "bitwise_and",
    "bitwise_or",
    "bitwise_xor",
    "div",
    "eq",
    "fmod",
    "ge",
    "gt",
    "le",
    "lt",
    "mul",
    "ne",
    "pow",
    "remainder",
    "sub",
}

for fname in _nvfuser_binary_ops:
    exec(
        f"""
# Ensure that the nvfuser implementation exists
_assert_nvfuser_op_exists("{fname}")

def _{fname}_nvfuser(fd, a, b):
    return fd.ops.{fname}(a, b)  # type: ignore[attr-defined]

_nvfuser_impls["{fname}"] = _{fname}_nvfuser
"""
    )

_nvfuser_ternary_ops = {
    "where",
}

for fname in _nvfuser_ternary_ops:
    exec(
        f"""
# Ensure that the nvfuser implementation exists
_assert_nvfuser_op_exists("{fname}")

def _{fname}_nvfuser(fd, a, b, c):
    return fd.ops.{fname}(a, b, c)  # type: ignore[attr-defined]

_nvfuser_impls["{fname}"] = _{fname}_nvfuser
"""
    )


def _broadcast_in_dim_nvfuser(
    fd: Any,
    a: TensorLikeType,
    shape: ShapeType,
    broadcast_dimensions: ShapeType,
):
    return fd.ops.broadcast_in_dim(a, shape, broadcast_dimensions)  # type: ignore[attr-defined]


def _convert_element_type_nvfuser(fd: Any, a: TensorLikeType, dtype: torch.dtype):
    nvfuser_dtype = getnvFuserDtype(dtype)
    return fd.ops.cast(a, nvfuser_dtype)  # type: ignore[attr-defined]


def _sum_nvfuser(
    fd: Any,
    a: TensorLikeType,
    dims: DimsSequenceType,
):
    keep_dims = False
    output_dtype = torch._C._nvfuser.DataType.Null
    return fd.ops.sum(a, dims, keep_dims, output_dtype)


def _var_nvfuser(
    fd: Any,
    a: TensorLikeType,
    dims: DimsSequenceType,
    *,
    correction: int,
):
    keep_dims = False
    return fd.ops.var(a, dims, correction, keep_dims)


def _var_mean_nvfuser(
    fd: Any,
    a: TensorLikeType,
    dims: DimsSequenceType,
    unbiased: Optional[bool] = None,
    keepdim: bool = False,
    *,
    correction: int,
):
    # Unbiased arg shouldn't be set when this function is called
    assert unbiased is None
    # Ignore keepdim arg, because currently it's automatically converted into nvfuser's symbolic scalar
    # keepdim is handled by the reference implementation
    keepdim = False
    return fd.ops.var_mean(a, dims, correction, keepdim)


def _amax_nvfuser(
    fd: Any,
    a: TensorLikeType,
    dims: DimsSequenceType,
):
    keep_dims = False
    return fd.ops.max(a, dims, keep_dims)


def _amin_nvfuser(
    fd: Any,
    a: TensorLikeType,
    dims: DimsSequenceType,
):
    keep_dims = False
    return fd.ops.min(a, dims, keep_dims)


_nvfuser_impls["broadcast_in_dim"] = _broadcast_in_dim_nvfuser
_nvfuser_impls["convert_element_type"] = _convert_element_type_nvfuser
_nvfuser_impls["sum"] = _sum_nvfuser
_nvfuser_impls["var"] = _var_nvfuser
_nvfuser_impls["var_mean"] = _var_mean_nvfuser
_nvfuser_impls["amax"] = _amax_nvfuser
_nvfuser_impls["amin"] = _amin_nvfuser


def register_var_mean():
    """This function is used to register the var_mean function in torch.ops.nvprims module."""
    name = "var_mean.main"

    # This overload must be default for correct dispatching of var_mean(Tensor, bool)
    nvprim.define("var_mean(Tensor inp, bool unbiased) -> (Tensor, Tensor)")

    # This signature tries to combine several overloads of the torch.var_mean function into one overload.
    nvprim.define(
        f"{name}(Tensor inp, int[1]? dim=None, bool? unbiased=None, bool keepdim=False, *, int? correction=None)"
        + " -> (Tensor, Tensor)"
    )

    # This function is used for device="meta" Tensors.
    def _meta_var_mean(inp, dim=None, unbiased=None, keepdim=False, *, correction=None):
        if torch._prims_common.is_complex_dtype(inp.dtype):
            output_dtype = torch._prims_common.corresponding_real_dtype(inp.dtype)
        else:
            output_dtype = inp.dtype
        var = torch._prims._reduction_meta(inp, dim, output_dtype=output_dtype)
        mean = torch._prims._reduction_meta(inp, dim, output_dtype=inp.dtype)
        if keepdim:
            output_shape = [
                inp.shape[i] if i not in dim else 1 for i in range(inp.ndim)
            ]
            broadcast_dims = [i for i in range(inp.ndim) if i not in dim]
            var = torch.ops.nvprims.broadcast_in_dim(var, output_shape, broadcast_dims)
            mean = torch.ops.nvprims.broadcast_in_dim(
                mean, output_shape, broadcast_dims
            )
        return (var, mean)

    # This function is used under _AutoDispatchBelowAutograd context
    def _prim_impl(inp, dim=None, unbiased=None, keepdim=False, *, correction=None):
        correction = torch._prims_common.set_correction(unbiased, correction)
        return torch.var_mean(inp, dim, correction=correction, keepdim=keepdim)

    nvprim_impl.impl(name, _prim_impl)
    nvprim_meta_impl.impl(name, _meta_var_mean)

    prim_packet = torch.ops.nvprims.var_mean
    prim = prim_packet.main

    def _unbiased_overload_impl(inp, unbiased):
        return prim(inp, dim=None, unbiased=unbiased)

    nvprim_implicit_impl.impl("var_mean", _unbiased_overload_impl)

    @elementwise_type_promotion_wrapper(
        type_promoting_args=("a",),
        type_promotion_kind=ELEMENTWISE_TYPE_PROMOTION_KIND.COMPLEX_TO_FLOAT,
    )
    def _var_mean_ref(a, dim=None, unbiased=None, keepdim=False, *, correction=None):
        correction = torch._prims_common.set_correction(unbiased, correction)
        # reduces over all dimensions if dim=() is passed
        if dim == () or dim == []:
            dim = None
        dim = torch._prims_common.reduction_dims(a.shape, dim)

        # For complex tensors eager computes the variance as the sum of variances of
        # the real and imaginary parts
        # TODO: Creating a complex tensor from real and imaginary parts is not supported
        if torch._prims_common.is_complex_dtype(a.dtype):
            raise NotImplementedError("Complex tensors are not supported")

        var_mean = prim(a, dim, correction=correction)

        if keepdim:
            output_shape = [a.shape[i] if i not in dim else 1 for i in range(a.ndim)]
            broadcast_dims = [i for i in range(a.ndim) if i not in dim]
            var, mean = var_mean
            var = torch.ops.nvprims.broadcast_in_dim(var, output_shape, broadcast_dims)
            mean = torch.ops.nvprims.broadcast_in_dim(
                mean, output_shape, broadcast_dims
            )
            var_mean = (var, mean)
        return var_mean

    def _var_mean_autograd(
        a, dim=None, unbiased=None, keepdim=False, *, correction=None
    ):
        # This wrapper is needed to convert prims calls inside
        # elementwise_type_promotion_wrapper to nvprims calls
        from torch._prims.context import NvfuserPrimsMode

        with NvfuserPrimsMode():
            return backwards_not_supported(_var_mean_ref)(
                a, dim, unbiased, keepdim, correction=correction
            )

    nvprim_autograd_impl.impl(name, _var_mean_autograd)

    for p in (prim_packet, prim):
        p.__doc__ = "Computes the variance and mean of x over the list of dimensions specified in the dim argument"
        p.impl_nvfuser = _nvfuser_impls["var_mean"]
        p.return_type = torch._prims_common.RETURN_TYPE.NEW  # type: ignore[attr-defined]


def register_nvprims():
    """Registers all nvFuser primitives in the torch.ops.nvprims module."""
    register_var_mean()
    for name in nvprim_names:
        main_prim = getattr(torch.ops.prims, name)

        nvprim.define(main_prim.schema)
        nvprim_impl.impl(name, main_prim.prim_impl)
        nvprim_meta_impl.impl(name, main_prim.prim_meta_impl)

        prim_packet = getattr(torch.ops.nvprims, name)
        prim = prim_packet.default

        nvprim_autograd_impl.impl(name, backwards_not_supported(prim))

        for p in (prim_packet, prim):
            p.__doc__ = main_prim.__doc__
            p.impl_nvfuser = _nvfuser_impls[name]
            p.return_type = main_prim.return_type  # type: ignore[attr-defined]
