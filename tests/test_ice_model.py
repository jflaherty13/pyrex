"""File containing tests of pyrex ice_model module"""

import pytest

from pyrex.ice_model import AntarcticIce, ArasimIce

import numpy as np


# Data from https://icecube.wisc.edu/~mnewcomb/radio/index/
MN_indices = [
    (-3,   1.35), (-8,   1.38), (-12,  1.45), # (-18,  1.52),
    (-22,  1.46), # (-28,  1.54),
    (-35,  1.50), (-45,  1.57), (-55,  1.52), (-65,  1.56), (-75,  1.56),
    (-85,  1.63), (-95,  1.68), (-105, 1.73), (-115, 1.72), (-125, 1.72),
    (-135, 1.75), (-145, 1.77), (-1000, 1.78)
]

# Data from internal calculation
# (i.e. just to confirm no change to code behavior)
other_indices = [
    (1,    1),      (-500, 1.7794), (-450, 1.7789), (-400, 1.7778),
    (-350, 1.7758), (-300, 1.7718), (-250, 1.7641), (-200, 1.7493)
]

# Data from https://icecube.wisc.edu/~mnewcomb/radio/temp/
KW_amanda_temps = [
    (-818.6,  -48.00), (-828.6,  -47.90), (-908.6,  -47.50), (-1008.6, -46.60),
    (-1034.6, -46.30), (-1234.6, -44.39), (-1321.6, -43.19), (-1450.6, -41.58),
    (-1479.6, -41.08), (-1515.6, -40.48), (-1512.6, -40.58), (-1518.6, -40.58),
    (-1522.6, -40.38), (-1522.6, -40.28), (-1522.6, -40.38), (-1522.6, -40.48),
    (-1536.6, -40.08), (-1537.6, -40.28), (-1542.6, -40.18), (-1548.6, -40.08),
    (-1553.6, -40.08), (-1555.6, -40.08), (-1584.6, -39.58), (-1606.6, -39.38),
    (-1664.6, -38.18), (-1689.6, -37.77), (-1689.6, -37.77), (-1689.6, -37.77),
    (-1690.6, -37.77), (-1704.6, -37.47), (-1733.6, -36.97), (-1735.6, -36.87),
    (-1764.6, -36.27), (-1766.6, -36.27), (-1766.6, -36.27), (-1769.6, -36.27),
    (-1786.6, -36.07), (-1829.6, -34.77), (-1835.6, -34.97), (-1864.6, -34.37),
    (-1933.6, -32.86), (-1935.6, -32.86), (-1956.6, -32.26), (-1958.6, -32.16),
    (-1964.6, -32.16), (-1970.6, -31.86), (-1972.6, -31.96), (-1981.6, -31.46),
    (-1986.6, -31.56), (-2005.6, -30.96), (-2005.6, -30.96), (-2020.6, -30.46),
    (-2027.6, -30.66), (-2044.6, -29.95), (-2050.6, -29.95), (-2156.6, -27.15),
    (-2170.6, -26.95), (-2330.6, -22.34), (-2353.6, -21.23)
]

# Data from https://icecube.wisc.edu/~mnewcomb/radio/temp/
KW_icecube_temps = [
    (0.0, -51.0), # (-1908.38, -37.91),
    (-2078.58, -28.76), (-2214.75, -25.09), (-2350.92, -20.93),
    # (-1923.70, -30.24),
    (-2161.99, -26.51), (-2298.15, -22.42), (-2434.32, -17.89),
    # (-1923.97, -32.22),
    (-2196.30, -25.79), (-2332.47, -21.55), (-2434.59, -18.23),
    # (-1934.05, -31.56),
    (-2172.34, -26.26), (-2444.67, -17.69)
]

# Data from internal calculation
# (i.e. just to confirm no change to code behavior)
attenuations = {
    (-100, 1e3):  160759,   (-200, 1e3):  155437,   (-300, 1e3):  149911,
    (-400, 1e3):  144029,   (-500, 1e3):  137673,   (-600, 1e3):  130761,
    (-700, 1e3):  123254,   (-800, 1e3):  115157,   (-900, 1e3):  106521,
    (-1000,1e3):  97443,
    (-100, 1e6):  14571,    (-200, 1e6):  14112,    (-300, 1e6):  13636,
    (-400, 1e6):  13130,    (-500, 1e6):  12585,    (-600, 1e6):  11993,
    (-700, 1e6):  11352,    (-800, 1e6):  10661,    (-900, 1e6):  9927,
    (-1000,1e6):  9156,
    (-100, 1e9):  1321,     (-200, 1e9):  1281,     (-300, 1e9):  1240,
    (-400, 1e9):  1197,     (-500, 1e9):  1150,     (-600, 1e9):  1100,
    (-700, 1e9):  1046,     (-800, 1e9):  987,      (-900, 1e9):  925,
    (-1000,1e9):  860,
    (-100, 1e12): 0.966e-3, (-200, 1e12): 1.067e-3, (-300, 1e12): 1.186e-3,
    (-400, 1e12): 1.332e-3, (-500, 1e12): 1.516e-3, (-600, 1e12): 1.753e-3,
    (-700, 1e12): 2.067e-3, (-800, 1e12): 2.489e-3, (-900, 1e12): 3.065e-3,
    (-1000,1e12): 3.865e-3
}


@pytest.fixture
def antarctic_ice():
    """Fixture for forming basic AntarcticIce object"""
    return AntarcticIce()


class TestAntarcticIce:
    """Tests for AntarcticIce class"""
    def test_parameters(self, antarctic_ice):
        """Tests the parameters of the ice"""
        assert antarctic_ice.k == 0.43
        assert antarctic_ice.a == 0.0132
        assert antarctic_ice.n0 == 1.78
        assert antarctic_ice.valid_range == (-2850, 0)

    @pytest.mark.parametrize("depth, index", other_indices)
    def test_index(self, antarctic_ice, depth, index):
        """Tests the index of refraction in the ice at different depths.
        Make sure indices match expected within 1%."""
        assert antarctic_ice.index(depth) == pytest.approx(index, rel=0.01)

    @pytest.mark.parametrize("depth, index", MN_indices)
    def test_index_MN(self, antarctic_ice, depth, index):
        """Tests the index of refraction in the ice at different depths
        (within 5%) according to Matt Newcomb's table here:
        http://icecube.wisc.edu/~mnewcomb/radio/index/"""
        assert antarctic_ice.index(depth) == pytest.approx(index, rel=0.05)

    def test_index_match(self, antarctic_ice):
        """Tests the index of refraction in the ice calculated for many depths
        at once matches the individual calculation."""
        depths = -1*np.linspace(-100, 1000, 12)
        indices = np.zeros(len(depths))
        for i, d in enumerate(depths):
            indices[i] = antarctic_ice.index(d)
        assert np.array_equal(antarctic_ice.index(depths), indices)

    def test_depth_with_index(self, antarctic_ice):
        """Tests the depth_with_index method properly inverts the index method
        (beneath/at surface only)."""
        depths = -1*np.linspace(0, 1000, 11)
        for depth, index in zip(depths, antarctic_ice.index(depths)):
            assert antarctic_ice.depth_with_index(index) == pytest.approx(depth)
        assert antarctic_ice.depth_with_index(1) == 0

    @pytest.mark.parametrize("depth, temp", KW_amanda_temps+KW_icecube_temps)
    def test_temperature(self, antarctic_ice, depth, temp):
        """Tests the temperature in the ice at different depths
        (within 3%) according to Kurt Woschnagg's data here:
        http://icecube.wisc.edu/~mnewcomb/radio/temp/"""
        assert antarctic_ice.temperature(depth) == pytest.approx(temp+273.15, rel=0.03)

    @pytest.mark.parametrize("depth", list(-1*np.linspace(100,1000,10)))
    @pytest.mark.parametrize("freq", list(np.logspace(3,12,4)))
    def test_attenuation_length(self, antarctic_ice, depth, freq):
        """Tests the attenuation length in the ice at different depths and
        frequencies. Make sure attenuations match expected within 1%."""
        assert(antarctic_ice.attenuation_length(depth, freq) == 
               pytest.approx(attenuations[(depth,freq)], rel=0.01))

    @pytest.mark.parametrize("depth", list(-1*np.linspace(100,1000,10)))
    def test_attenuation_length_freq_match(self, antarctic_ice, depth):
        """Tests the attenuation length in the ice calculated for many freqs
        at once matches the individual calculation."""
        freq = np.logspace(3, 12, 4)
        a_lens = [antarctic_ice.attenuation_length(depth, f) for f in freq]
        assert np.array_equal(antarctic_ice.attenuation_length(depth, freq),
                              a_lens)

    @pytest.mark.parametrize("freq", list(np.logspace(3,12,4)))
    def test_attenuation_length_depth_match(self, antarctic_ice, freq):
        """Tests the attenuation length in the ice calculated for many depths
        at once matches the individual calculation."""
        depth = -1*np.linspace(100,1000,10)
        a_lens = [antarctic_ice.attenuation_length(d, freq) for d in depth]
        assert np.array_equal(antarctic_ice.attenuation_length(depth, freq),
                              a_lens)

    def test_attenuation_length_both_match(self, antarctic_ice):
        """Tests the attenuation length in the ice calculated for many depths
        and freqs at once matches the individual calculation."""
        depth = -1*np.linspace(100,1000,10)
        freq = np.logspace(3, 12, 4)
        a_lens = np.zeros((len(depth),len(freq)))
        for i, d in enumerate(depth):
            for j, f in enumerate(freq):
                a_lens[i,j] = antarctic_ice.attenuation_length(d, f)
        assert np.array_equal(antarctic_ice.attenuation_length(depth, freq),
                              a_lens)




# Data from internal calculation
# (i.e. just to confirm no change to code behavior)
arasim_attenuations = {
    (-100, 1e3):  1773, (-200, 1e3):  1530, (-300, 1e3):  1474,
    (-400, 1e3):  1440, (-500, 1e3):  1401, (-600, 1e3):  1351,
    (-700, 1e3):  1292, (-800, 1e3):  1232, (-900, 1e3):  1168,
    (-1000,1e3):  1093,
    (-100, 1e6):  1773, (-200, 1e6):  1530, (-300, 1e6):  1474,
    (-400, 1e6):  1440, (-500, 1e6):  1401, (-600, 1e6):  1351,
    (-700, 1e6):  1292, (-800, 1e6):  1232, (-900, 1e6):  1168,
    (-1000,1e6):  1093,
    (-100, 1e9):  1773, (-200, 1e9):  1530, (-300, 1e9):  1474,
    (-400, 1e9):  1440, (-500, 1e9):  1401, (-600, 1e9):  1351,
    (-700, 1e9):  1292, (-800, 1e9):  1232, (-900, 1e9):  1168,
    (-1000,1e9):  1093,
    (-100, 1e12): 1773, (-200, 1e12): 1530, (-300, 1e12): 1474,
    (-400, 1e12): 1440, (-500, 1e12): 1401, (-600, 1e12): 1351,
    (-700, 1e12): 1292, (-800, 1e12): 1232, (-900, 1e12): 1168,
    (-1000,1e12): 1093
}


@pytest.fixture
def arasim_ice():
    """Fixture for forming basic ArasimIce object"""
    return ArasimIce()

class TestArasimIce:
    """Tests for ArasimIce class"""
    def test_parameters(self, arasim_ice):
        """Tests the parameters of the ice"""
        assert arasim_ice.k == 0.43
        assert arasim_ice.a == 0.0132
        assert arasim_ice.n0 == 1.78

    @pytest.mark.parametrize("depth, index", other_indices)
    def test_index(self, arasim_ice, depth, index):
        """Tests the index of refraction in the ice at different depths.
        Make sure indices match expected within 1%."""
        assert arasim_ice.index(depth) == pytest.approx(index, rel=0.01)

    def test_index_match(self, arasim_ice):
        """Tests the index of refraction in the ice calculated for many depths
        at once matches the individual calculation."""
        depths = -1*np.linspace(-100, 1000, 12)
        indices = np.zeros(len(depths))
        for i, d in enumerate(depths):
            indices[i] = arasim_ice.index(d)
        assert np.array_equal(arasim_ice.index(depths), indices)

    def test_depth_with_index(self, arasim_ice):
        """Tests the depth_with_index method properly inverts the index method
        (beneath/at surface only)."""
        depths = -1*np.linspace(0, 1000, 11)
        for depth, index in zip(depths, arasim_ice.index(depths)):
            assert arasim_ice.depth_with_index(index) == pytest.approx(depth)
        assert arasim_ice.depth_with_index(1) == 0

    @pytest.mark.parametrize("depth, temp", KW_amanda_temps+KW_icecube_temps)
    def test_temperature(self, arasim_ice, depth, temp):
        """Tests the temperature in the ice at different depths
        (within 3%) according to Kurt Woschnagg's data here:
        http://icecube.wisc.edu/~mnewcomb/radio/temp/"""
        assert arasim_ice.temperature(depth) == pytest.approx(temp+273.15, rel=0.03)

    @pytest.mark.parametrize("depth", list(-1*np.linspace(100,1000,10)))
    @pytest.mark.parametrize("freq", list(np.logspace(3,12,4)))
    def test_attenuation_length(self, arasim_ice, depth, freq):
        """Tests the attenuation length in the ice at different depths and
        frequencies. Make sure attenuations match expected within 1%."""
        assert(arasim_ice.attenuation_length(depth, freq) == 
               pytest.approx(arasim_attenuations[(depth,freq)], rel=0.01))

    @pytest.mark.parametrize("depth", list(-1*np.linspace(100,1000,10)))
    def test_attenuation_length_freq_match(self, arasim_ice, depth):
        """Tests the attenuation length in the ice calculated for many freqs
        at once matches the individual calculation."""
        freq = np.logspace(3, 12, 4)
        a_lens = [arasim_ice.attenuation_length(depth, f) for f in freq]
        assert np.array_equal(arasim_ice.attenuation_length(depth, freq),
                              a_lens)

    @pytest.mark.parametrize("freq", list(np.logspace(3,12,4)))
    def test_attenuation_length_depth_match(self, arasim_ice, freq):
        """Tests the attenuation length in the ice calculated for many depths
        at once matches the individual calculation."""
        depth = -1*np.linspace(100,1000,10)
        a_lens = [arasim_ice.attenuation_length(d, freq) for d in depth]
        assert np.array_equal(arasim_ice.attenuation_length(depth, freq),
                              a_lens)

    def test_attenuation_length_both_match(self, arasim_ice):
        """Tests the attenuation length in the ice calculated for many depths
        and freqs at once matches the individual calculation."""
        depth = -1*np.linspace(100,1000,10)
        freq = np.logspace(3, 12, 4)
        a_lens = np.zeros((len(depth),len(freq)))
        for i, d in enumerate(depth):
            for j, f in enumerate(freq):
                a_lens[i,j] = arasim_ice.attenuation_length(d, f)
        assert np.array_equal(arasim_ice.attenuation_length(depth, freq),
                              a_lens)
    