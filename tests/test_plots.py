import jax.numpy as jnp
import numpy as np
import pytest
from matplotlib import pyplot as plt

from dynamiqs import coherent, plot_wigner, plot_wigner_mosaic, todm
from dynamiqs.utils.wigners import _diag_element

# TODO : add comparison with analytical wigner for coherent states and cat states


class TestPlots:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.psis = [coherent(10, x) for x in np.linspace(0, 1, 10)]
        self.rhos = list(map(todm, self.psis))

        self.psis = jnp.asarray(self.psis)
        self.rhos = jnp.asarray(self.rhos)

    @pytest.fixture(autouse=True)
    def _teardown(self):
        # once the test is finished, pytest will go back here and run the code after
        # the yield statement
        yield
        plt.close('all')

    def test_plot_wigner_psi(self):
        plot_wigner(self.psis[0])

    def test_plot_wigner_psis(self):
        plot_wigner_mosaic(self.psis)

    def test_plot_wigner_rho(self):
        plot_wigner(self.rhos[0])

    def test_plot_wigner_rhos(self):
        plot_wigner_mosaic(self.rhos)

    def test_diag_element(self):
        mat = jnp.arange(25).reshape(5, 5)
        for diag in range(-4, 5):
            diag_len = 5 - abs(diag)
            for element in range(-diag_len + 1, diag_len):
                x = _diag_element(mat, diag, element)
                y = np.diag(mat, diag)[element]
                err_msg = (
                    f'Failed for diag = {diag}, element = {element}, expected "{y}",'
                    f' got "{x}"'
                )
                assert x == y, err_msg
