import jax
import jax.numpy as jnp
import pytest

import dynamiqs as dq


@pytest.mark.parametrize('cartesian_batching', [True, False])
def test_batching(cartesian_batching):
    n = 8
    nt = 11
    nH = 3
    npsi0 = 4 if cartesian_batching else nH
    nEs = 5

    options = dq.options.Options(cartesian_batching=cartesian_batching)

    # create random objects
    k1, k2, k3 = jax.random.split(jax.random.PRNGKey(42), 3)
    H = dq.rand_herm(k1, (nH, n, n))
    exp_ops = dq.rand_complex(k2, (nEs, n, n))
    psi0 = dq.rand_ket(k3, (npsi0, n, 1))
    tsave = jnp.linspace(0, 0.01, nt)

    # no batching
    result = dq.sesolve(H[0], psi0[0], tsave, exp_ops=exp_ops, options=options)
    assert result.states.shape == (nt, n, 1)
    assert result.expects.shape == (nEs, nt)

    # H batched
    result = dq.sesolve(H, psi0[0], tsave, exp_ops=exp_ops, options=options)
    assert result.states.shape == (nH, nt, n, 1)
    assert result.expects.shape == (nH, nEs, nt)

    # psi0 batched
    result = dq.sesolve(H[0], psi0, tsave, exp_ops=exp_ops, options=options)
    assert result.states.shape == (npsi0, nt, n, 1)
    assert result.expects.shape == (npsi0, nEs, nt)

    # H and psi0 batched
    result = dq.sesolve(H, psi0, tsave, exp_ops=exp_ops, options=options)
    if cartesian_batching:
        assert result.states.shape == (nH, npsi0, nt, n, 1)
        assert result.expects.shape == (nH, npsi0, nEs, nt)
    else:
        assert result.states.shape == (nH, nt, n, 1)
        assert result.expects.shape == (nH, nEs, nt)
