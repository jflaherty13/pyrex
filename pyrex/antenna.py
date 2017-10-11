"""Module containing antenna class capable of receiving signals"""

import numpy as np
import scipy.fftpack
import scipy.signal
from pyrex.internal_functions import normalize
from pyrex.signals import Signal, ThermalNoise, ValueTypes
from pyrex.ice_model import IceModel


class Antenna:
    """Base class for an antenna with a given position (m), temperature (K),
    allowable frequency range (Hz), total resistance (ohm) used for Johnson
    noise, and whether or not to include noise in the antenna's waveforms.
    Defines default trigger, frequency response, and signal reception functions
    that can be overwritten in base classes to customize the antenna."""
    def __init__(self, position, z_axis=[0,0,1], x_axis=[1,0,0],
                 antenna_factor=1, efficiency=1, freq_range=None,
                 noise_rms=None, temperature=None, resistance=None, noisy=True):
        self.position = position
        self.z_axis = normalize(z_axis)
        self.x_axis = normalize(x_axis)
        self.antenna_factor = antenna_factor
        self.efficiency = efficiency
        self.freq_range = freq_range
        self.noise_rms = noise_rms
        self.temperature = temperature
        self.resistance = resistance
        self.noisy = noisy

        self.signals = []
        self._noises = []
        self._triggers = []

    @property
    def is_hit(self):
        """Test for whether the antenna has received a signal."""
        return len(self.waveforms)>0

    def clear(self):
        """Reset the antenna to a state of having received no signals."""
        self.signals.clear()
        self._noises.clear()
        self._triggers.clear()

    @property
    def waveforms(self):
        """Signal + noise (if noisy) at each triggered antenna hit."""
        # Process any unprocessed triggers
        all_waves = self.all_waveforms
        while len(self._triggers)<len(all_waves):
            waveform = all_waves[len(self._triggers)]
            self._triggers.append(self.trigger(waveform))

        return [wave for wave, triggered in zip(all_waves, self._triggers)
                if triggered]

    @property
    def all_waveforms(self):
        """Signal + noise (if noisy) at all antenna hits, even those that
        didn't trigger."""
        if not(self.noisy):
            return self.signals

        # Generate noise as necessary
        while len(self._noises)<len(self.signals):
            self._noises.append(
                self.make_noise(self.signals[len(self._noises)].times)
            )

        return [s + n for s, n in zip(self.signals, self._noises)]


    def make_noise(self, times):
        """Returns the noise signal generated by the antenna over
        the given array of times. Used to add noise to signal for production
        of the antenna's waveforms."""
        if self.freq_range is None:
            raise ValueError("A frequency range is required to generate"
                             +" antenna noise")
        elif (self.noise_rms is None and
              (self.temperature is None or self.resistance is None)):
            raise ValueError("A noise rms value (or temperature and resistance"
                             +" are required to generate antenna noise")
        elif self.noise_rms is None:
            return ThermalNoise(times, f_band=self.freq_range,
                                temperature=self.temperature,
                                resistance=self.resistance)
        else:
            return ThermalNoise(times, f_band=self.freq_range,
                                rms_voltage=self.noise_rms)


    def trigger(self, signal):
        """Function to determine whether or not the antenna is triggered by
        the given Signal object."""
        return True

    def _convert_to_antenna_coordinates(self, point):
        # Matrix multiplication using antenna axes as rows in transformation
        # matrix to transform point into antenna coordinates
        y_axis = np.cross(self.z_axis, self.x_axis)
        transformation = np.array([self.x_axis, y_axis, self.z_axis])
        x, y, z = np.dot(transformation, point)
        # Convert to spherical coordinates
        r = np.sqrt(x**2 + y**2 + z**2)
        if r==0:
            return 0, 0, 0
        theta = np.arccos(z/r)
        phi = np.arctan2(y, x)
        return r, theta, phi

    def directional_gain(self, theta, phi):
        """Function to calculate the directive electric field gain of the
        antenna at given angles theta (polar) and phi (azimuthal)
        relative to the antenna's orientation."""
        return 1

    def polarization_gain(self, polarization):
        """Function to calculate the electric field gain due to polarization
        for a given polarization direction."""
        return 1

    def response(self, frequencies):
        """Function to return the frequency response of the antenna at the
        given frequencies (Hz). This function should return the response as
        imaginary numbers, where the real part is the amplitude response and
        the imaginary part is the phase response."""
        return np.ones(len(frequencies))

    def receive(self, signal, origin=None, polarization=None):
        """Process incoming signal according to the filter function and
        store it to the signals list. Subclasses may extend this fuction,
        but should end with super().receive(signal)."""
        copy = Signal(signal.times, signal.values)
        copy.filter_frequencies(self.response)

        if origin is None:
            d_gain = 1
        else:
            # Calculate theta and phi relative to the orientation
            r, theta, phi = self._convert_to_antenna_coordinates(origin)
            d_gain = self.directional_gain(theta=theta, phi=phi)

        if polarization is None:
            p_gain = 1
        else:
            p_gain = self.polarization_gain(normalize(polarization))

        signal_factor = d_gain * p_gain * self.efficiency

        if signal.value_type==ValueTypes.voltage:
            pass
        elif signal.value_type==ValueTypes.field:
            signal_factor /= self.antenna_factor
        else:
            raise ValueError("Signal's value type must be either "
                             +"voltage or field.")

        copy.values *= signal_factor
        self.signals.append(copy)



class DipoleAntenna(Antenna):
    """Antenna with a given name, position (m), center frequency (Hz),
    bandwidth (Hz), resistance (ohm), effective height (m), polarization
    direction, and trigger threshold (V)."""
    def __init__(self, name, position, center_frequency, bandwidth, resistance,
                 orientation=[0,0,1], trigger_threshold=0,
                 effective_height=None, noisy=True):
        self.name = name
        self.threshold = trigger_threshold
        if effective_height is None:
            # Calculate length of half-wave dipole
            self.effective_height = 3e8 / center_frequency / 2
        else:
            self.effective_height = effective_height

        # Get the critical frequencies in Hz
        f_low = center_frequency - bandwidth/2
        f_high = center_frequency + bandwidth/2

        # Get arbitrary x-axis orthogonal to orientation
        tmp_vector = np.zeros(3)
        while np.array_equal(np.cross(orientation, tmp_vector), (0,0,0)):
            tmp_vector = np.random.rand(3)
        ortho = np.cross(orientation, tmp_vector)
        # Note: ortho is not normalized, but will be normalized by Antenna's init

        super().__init__(position=position, z_axis=orientation, x_axis=ortho,
                         antenna_factor=1/self.effective_height,
                         temperature=IceModel.temperature(position[2]),
                         freq_range=(f_low, f_high), resistance=resistance,
                         noisy=noisy)

        # Build scipy butterworth filter to speed up response function
        b, a  = scipy.signal.butter(1, 2*np.pi*np.array(self.freq_range),
                                    btype='bandpass', analog=True)
        self.filter_coeffs = (b, a)


    def trigger(self, signal):
        """Trigger on the signal if the maximum signal value is above the
        given threshold."""
        return max(np.abs(signal.values)) > self.threshold

    def response(self, frequencies):
        """Butterworth filter response for the antenna's frequency range."""
        angular_freqs = np.array(frequencies) * 2*np.pi
        w, h = scipy.signal.freqs(self.filter_coeffs[0], self.filter_coeffs[1],
                                  angular_freqs)
        return h

    def directional_gain(self, theta, phi):
        """Power gain of dipole antenna goes as sin(theta)^2, so electric field
        gain goes as sin(theta)."""
        return np.sin(theta)

    def polarization_gain(self, polarization):
        """Polarization gain is simply the dot product of the polarization
        with the antenna's z-axis."""
        return np.vdot(self.z_axis, polarization)
