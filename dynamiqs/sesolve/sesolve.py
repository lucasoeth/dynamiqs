from __future__ import annotations

from functools import partial

import jax
import jax.numpy as jnp
from jax import Array
from jaxtyping import ArrayLike

from .._utils import cdtype
from ..core._utils import _astimearray, compute_vmap, get_solver_class
from ..gradient import Gradient
from ..options import Options
from ..result import Result
from ..solver import Dopri5, Dopri8, Euler, Propagator, Solver, Tsit5
from ..time_array import TimeArray
from .sediffrax import SEDopri5, SEDopri8, SEEuler, SETsit5
from .sepropagator import SEPropagator


def sesolve(
    H: ArrayLike | TimeArray,
    psi0: ArrayLike,
    tsave: ArrayLike,
    *,
    exp_ops: list[ArrayLike] | None = None,
    solver: Solver = Tsit5(),  # noqa: B008
    gradient: Gradient | None = None,
    options: Options = Options(),  # noqa: B008
) -> Result:
    r"""Solve the Schrödinger equation.

    This function computes the evolution of the state vector $\ket{\psi(t)}$ at time
    $t$, starting from an initial state $\ket{\psi_0}$, according to the Schrödinger
    equation ($\hbar=1$)
    $$
        \frac{\dd\ket{\psi(t)}}{\dt} = -i H(t) \ket{\psi(t)},
    $$
    where $H(t)$ is the system's Hamiltonian at time $t$.

    Quote: Time-dependent Hamiltonian
        If the Hamiltonian depends on time, it can be converted to a time-array using
        [`dq.constant()`](/python_api/time_array/constant.html),
        [`dq.pwc()`](/python_api/time_array/pwc.html),
        [`dq.modulated()`](/python_api/time_array/modulated.html), or
        [`dq.timecallable()`](/python_api/time_array/timecallable.html).

    Quote: Running multiple simulations concurrently
        Both the Hamiltonian `H` and the initial state `psi0` can be batched to
        solve multiple Schrödinger equations concurrently. All other arguments are
        common to every batch.

    Args:
        H _(array-like or time-array of shape (bH?, n, n))_: Hamiltonian.
        psi0 _(array-like of shape (bpsi?, n, 1))_: Initial state.
        tsave _(array-like of shape (nt,))_: Times at which the states and expectation
            values are saved. The equation is solved from `tsave[0]` to `tsave[-1]`, or
            from `t0` to `tsave[-1]` if `t0` is specified in `options`.
        exp_ops _(list of array-like, of shape (nE, n, n), optional)_: List of
            operators for which the expectation value is computed.
        solver: Solver for the integration. Defaults to
            [`dq.solver.Tsit5()`](/python_api/solver/Tsit5.html).
        gradient: Algorithm used to compute the gradient.
        options: Generic options, see [`dq.Options`](/python_api/options/Options.html).

    Returns:
        [`dq.Result`](/python_api/result/Result.html) object holding the result of the
            Schrödinger equation integration. It has the following attributes:

            - **states** _(array of shape (bH?, bpsi?, nt, n, 1))_ -- Saved states.
            - **expects** _(array of shape (bH?, bpsi?, nE, nt), optional)_ -- Saved
                expectation values.
            - **extra** _(PyTree, optional)_ -- Extra data saved with `save_extra()` if
                specified in `options`.
            - **infos** _(PyTree, optional)_ -- Solver-dependent information on the
                resolution.
            - **tsave** _(array of shape (nt,))_ -- Times for which results were saved.
            - **solver** _(Solver)_ -- Solver used.
            - **gradient** _(Gradient)_ -- Gradient used.
            - **options** _(Options)_ -- Options used.
    """
    # === convert arguments
    H = _astimearray(H)
    psi0 = jnp.asarray(psi0, dtype=cdtype())
    tsave = jnp.asarray(tsave)
    exp_ops = jnp.asarray(exp_ops, dtype=cdtype()) if exp_ops is not None else None

    # we implement the jitted vmap in another function to pre-convert QuTiP objects
    # (which are not JIT-compatible) to JAX arrays
    return _vmap_sesolve(H, psi0, tsave, exp_ops, solver, gradient, options)


@partial(jax.jit, static_argnames=('solver', 'gradient', 'options'))
def _vmap_sesolve(
    H: TimeArray,
    psi0: Array,
    tsave: Array,
    exp_ops: Array | None,
    solver: Solver,
    gradient: Gradient | None,
    options: Options,
) -> Result:
    # === vectorize function
    # we vectorize over H and psi0, all other arguments are not vectorized
    is_batched = (H.ndim > 2, psi0.ndim > 2, False, False, False, False, False)
    # the result is vectorized over `saved`
    out_axes = Result(None, None, None, None, 0, 0)
    f = compute_vmap(_sesolve, options.cartesian_batching, is_batched, out_axes)

    # === apply vectorized function
    return f(H, psi0, tsave, exp_ops, solver, gradient, options)


def _sesolve(
    H: TimeArray,
    psi0: Array,
    tsave: Array,
    exp_ops: Array | None,
    solver: Solver,
    gradient: Gradient | None,
    options: Options,
) -> Result:
    # === select solver class
    solvers = {
        Euler: SEEuler,
        Dopri5: SEDopri5,
        Dopri8: SEDopri8,
        Tsit5: SETsit5,
        Propagator: SEPropagator,
    }
    solver_class = get_solver_class(solvers, solver)

    # === check gradient is supported
    solver.assert_supports_gradient(gradient)

    # === init solver
    solver = solver_class(tsave, psi0, H, exp_ops, solver, gradient, options)

    # === run solver
    result = solver.run()

    # === return result
    return result  # noqa: RET504
