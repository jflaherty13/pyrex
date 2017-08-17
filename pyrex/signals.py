"""Module containing classes for digital signal processing"""


import numpy as np
import scipy.signal
import scipy.fftpack

class Signal:
    """Base class for signals. Takes arrays of times and values
    (values array forced to size of times array by zero padding or slicing).
    Supports adding between signals with the same time values,
    resampling the signal, and calculating the signal's envelope."""
    def __init__(self, times, values):
        self.times = np.array(times)
        len_diff = len(times)-len(values)
        if len_diff>0:
            self.values = np.concatenate((values, np.zeros(len_diff)))
        else:
            self.values = np.array(values[:len(times)])

    def __add__(self, other):
        """Adds two signals by adding their values at each time."""
        if not(isinstance(other, Signal)):
            raise TypeError("Can't add object with type"
                            +str(type(other))+" to a signal")
        if not(np.array_equal(self.times, other.times)):
            raise ValueError("Can't add signals with different times")

        return Signal(self.times,self.values+other.values)

    def __radd__(self, other):
        """Allows for adding Signal object to 0.
        Useful when using sum() on a set of signals."""
        if other!=0:
            raise TypeError("unsupported operand type(s) for +: '"+
                            +str(type(other))+"' and 'Signal'")

        return self

    @property
    def dt(self):
        """Returns the spacing of the time array, or None if invalid."""
        try:
            return self.times[1]-self.times[0]
        except IndexError:
            return None

    @property
    def envelope(self):
        """Calculates envelope of the signal by Hilbert transform."""
        analytic_signal = scipy.signal.hilbert(self.values)
        return np.abs(analytic_signal)

    def resample(self, n):
        """Resamples the signal into n points in the same time range."""
        if n==len(self.times):
            return

        self.times = np.linspace(self.times[0], self.times[-1], n)
        self.values = scipy.signal.resample(self.values, n)


    @property
    def spectrum(self):
        """Returns the FFT spectrum of the signal."""
        return scipy.fftpack.fft(self.values)

    @property
    def frequencies(self):
        """Returns the FFT frequencies of the signal."""
        return scipy.fftpack.fftfreq(n=len(self.values), d=self.dt)

    def filter_frequencies(self, freq_response):
        """Applies the given frequency response function to the signal."""
        filtered_spectrum = self.spectrum
        for i, f in enumerate(self.frequencies):
            filtered_spectrum[i] *= freq_response(f)
        self.values = scipy.fftpack.ifft(filtered_spectrum)



class EmptySignal(Signal):
    """Class for signal with no amplitude (all values = 0)"""
    def __init__(self, times):
        super().__init__(times, np.zeros(len(times)))


class FunctionSignal(Signal):
    """Class for signals generated by a function"""
    def __init__(self, times, function):
        self.function = function
        values = []
        for t in times:
            values.append(self.function(t))
        super().__init__(times, values)



class SlowAskaryanSignal(Signal):
    """Askaryan pulse binned to times from neutrino with given energy (TeV)
    observed at angle theta (radians). Optional parameters are the index of
    refraction n, and pulse offset to start time t0 (s). Returned signal
    values are electric fields (V/m).\n
    Note that the amplitude of the pulse goes as 1/R, where R is the distance
    from source to observer. R is assumed to be 1 meter so that dividing by a
    different value produces the proper result."""
    def __init__(self, times, energy, theta, n=1.78, t0=0):
        # Calculation of pulse based on https://arxiv.org/pdf/1106.6283v3.pdf
        # Vector potential is given by:
        #   A(theta,t) = integral(Q(z) * RAC(t-z(1-n*cos(theta))/c))
        #                * sin(theta) / sin(theta_c) / R / integral(Q(z))
        self.energy = energy
        self.vector_potential = np.zeros(len(times))

        # Conversion factor for z in RAC
        z_to_t = (1 - n*np.cos(theta))/3e8

        # Integrals of z go from z_min to z_max with n_z steps
        z_min = 0
        z_max = 2.5*self.max_length()
        n_z = 1000
        z_vals, dz = np.linspace(z_min, z_max, n_z, endpoint=False, retstep=True)

        # Q(z) is the same for every time
        Q = np.zeros(n_z)
        for i, z in enumerate(z_vals):
            Q[i] = self.charge_profile(z)

        # Calculate RAC and integral(Q*RAC) at each time
        for i, t in enumerate(times):
            RA_C = np.zeros(n_z)
            for j, z in enumerate(z_vals):
                RA_C[j] = self.RAC(t - t0 - z*z_to_t)
            self.vector_potential[i] = np.trapz(Q*RA_C, dx=dz)

        # Calculate LQ_tot (the excess longitudinal charge along the shower)
        LQ_tot = np.trapz(Q, dx=dz)

        # Calculate sin(theta_c) = sqrt(1-cos^2(theta_c)) = sqrt(1-1/n^2)
        sin_theta_c = np.sqrt(1 - 1/n**2)

        # Scale the integral by the necessary factors
        self.vector_potential *= np.sin(theta) / sin_theta_c / LQ_tot

        # Calculate electric field by taking derivative of vector potential
        dt = times[1] - times[0]
        values = -np.diff(self.vector_potential) / dt

        super().__init__(times, values)


    def RAC(self, time):
        """Calculates R * vector potential at the Cherenkov angle in Vs
        at the given time (s)."""
        # Get absolute value of time in nanoseconds
        ta = np.abs(time) * 1e9
        if time>=0:
            return (-4.5e-14 * self.energy
                    * (np.exp(-ta/0.057) + (1+2.87*ta)**-3))
        else:
            return (-4.5e-14 * self.energy
                    * (np.exp(-ta/0.030) + (1+3.05*ta)**-3.5))

    def charge_profile(self, z, density=0.92, crit_energy=7.86e-5,
                       rad_length=36.08):
        """Calculates the longitudinal charge profile in the EM shower at
        distance z (m) with parameters for the density (g/cm^3),
        critical energy (TeV), and electron radiation length (g/cm^2) in ice."""
        if z<=0 or self.energy<=crit_energy:
            return 0

        # Depth calculated by "integrating" the density along the shower path
        # (in g/cm^2)
        x = 100 * z * density
        x_ratio = x / rad_length
        e_ratio = self.energy / crit_energy

        # Shower age
        s = 3 * x_ratio / (x_ratio + 2*np.log(e_ratio))

        # Number of particles
        N = (0.31 * np.exp(x_ratio * (1 - 1.5*np.log(s)))
             / np.sqrt(np.log(e_ratio)))

        return N * 1.602e-19

    def max_length(self, density=0.92, crit_energy=7.86e-5, rad_length=36.08):
        """Calculates the maximum length (m) of an EM shower
        with parameters for the density (g/cm^3), critical energy (TeV), and
        electron radiation length (g/cm^2) in ice."""
        # Maximum depth in g/cm^2
        x_max = rad_length * np.log(self.energy / crit_energy) / np.log(2)

        return 0.01 * x_max / density


class FastAskaryanSignal(Signal):
    """Askaryan pulse binned to times from neutrino with given energy (TeV)
    observed at angle theta (radians). Optional parameters are the index of
    refraction n, and pulse offset to start time t0 (s). Returned signal
    values are electric fields (V/m).\n
    Note that the amplitude of the pulse goes as 1/R, where R is the distance
    from source to observer. R is assumed to be 1 meter so that dividing by a
    different value produces the proper result."""
    def __init__(self, times, energy, theta, n=1.78, t0=0):
        # Calculation of pulse based on https://arxiv.org/pdf/1106.6283v3.pdf
        # Vector potential is given by:
        #   A(theta,t) = convolution(Q(z(1-n*cos(theta))/c)),
        #                            RAC(z(1-n*cos(theta))/c))
        #                * sin(theta) / sin(theta_c) / R / integral(Q(z))
        #                * c / (1-n*cos(theta))
        self.energy = energy

        # Conversion factor from z to t for RAC:
        # (1-n*cos(theta)) / c
        z_to_t = (1 - n*np.cos(theta))/3e8

        # Calculate the time step and the corresponding z-step
        dt = times[1] - times[0]
        dz = np.abs(dt / z_to_t)

        # Create the charge-profile array up to 2.5 times the nominal
        # maximum shower length (to reduce errors)
        z_max = 2.5*self.max_length()
        n_Q = int(z_max/dz)
        z_Q_vals = np.arange(n_Q) * dz
        Q = np.zeros(n_Q)
        for i, z in enumerate(z_Q_vals):
            Q[i] = self.charge_profile(z)

        # Calculate RAC at a specific number of z values (n_RAC) determined so
        # that the full convolution will have the same size as the times array
        n_RAC = len(times) + 1 - n_Q
        z_RAC_vals = np.arange(n_RAC) * dz
        RA_C = np.zeros(n_RAC)
        for i, z in enumerate(z_RAC_vals):
            RA_C[i] = self.RAC(t0 + z*z_to_t)

        # Convolve Q and RAC to get (unnormalized) vector potential A
        A = scipy.signal.convolve(Q, RA_C, mode='full')

        # Calculate LQ_tot (the excess longitudinal charge along the shower)
        LQ_tot = np.trapz(Q, dx=dz)

        # Calculate sin(theta_c) = sqrt(1-cos^2(theta_c)) = sqrt(1-1/n^2)
        sin_theta_c = np.sqrt(1 - 1/n**2)

        # Scale the integral by the necessary factors
        A *= np.sin(theta) / sin_theta_c / LQ_tot / z_to_t

        # Not sure why, but multiplying A by -dt is necessary to fix
        # normalization and dependence of amplitude on time spacing.
        # Since E = -dA/dt = np.diff(A) / -dt, we can skip multiplying
        # and later dividing by dt to save a little computational effort
        # (at the risk of more cognitive effort when deciphering the code)
        # So, to clarify, the above statement should have "* -dt" at the end
        # to be the true value of A, and the below would then have "/ -dt"

        # Calculate electric field by taking derivative of vector potential
        values = np.diff(A)

        # Note that although len(values) = len(times)-1 (because of np.diff),
        # the Signal class is desinged to handle this by zero-padding the values
        super().__init__(times, values)


    @property
    def vector_potential(self):
        """Recover the vector_potential from the electric field.
        Mostly just for testing purposes."""
        return np.cumsum(np.concatenate(([0],self.values)))[:-1] * -self.dt


    def RAC(self, time):
        """Calculates R * vector potential (A) at the Cherenkov angle in Vs
        at the given time (s)."""
        # Get absolute value of time in nanoseconds
        ta = np.abs(time) * 1e9
        if time>=0:
            return (-4.5e-14 * self.energy
                    * (np.exp(-ta/0.057) + (1+2.87*ta)**-3))
        else:
            return (-4.5e-14 * self.energy
                    * (np.exp(-ta/0.030) + (1+3.05*ta)**-3.5))

    def charge_profile(self, z, density=0.92, crit_energy=7.86e-5,
                       rad_length=36.08):
        """Calculates the longitudinal charge profile in the EM shower at
        distance z (m) with parameters for the density (g/cm^3),
        critical energy (TeV), and electron radiation length (g/cm^2) in ice."""
        if z<=0 or self.energy<=crit_energy:
            return 0

        # Depth calculated by "integrating" the density along the shower path
        # (in g/cm^2)
        x = 100 * z * density
        x_ratio = x / rad_length
        e_ratio = self.energy / crit_energy

        # Shower age
        s = 3 * x_ratio / (x_ratio + 2*np.log(e_ratio))

        # Number of particles
        N = (0.31 * np.exp(x_ratio * (1 - 1.5*np.log(s)))
             / np.sqrt(np.log(e_ratio)))

        return N * 1.602e-19

    def max_length(self, density=0.92, crit_energy=7.86e-5, rad_length=36.08):
        """Calculates the maximum length (m) of an EM shower
        with parameters for the density (g/cm^3), critical energy (TeV), and
        electron radiation length (g/cm^2) in ice."""
        # Maximum depth in g/cm^2
        x_max = rad_length * np.log(self.energy / crit_energy) / np.log(2)

        return 0.01 * x_max / density


# FastAskaryanSignal result now matches SlowAskaryanSignal.
# In fact, FastAskaryanSignal performs much better:
#   Runs about 1000x faster
#   Causal, whereas SlowAskaryanSignal pulse seems to be backwards in time
#   Smooth pulse; no artifacts from integration errors
AskaryanSignal = FastAskaryanSignal



class GaussianNoise(FunctionSignal):
    """Gaussian noise signal with standard deviation sigma"""
    def __init__(self, times, sigma):
        self.sigma = sigma
        super().__init__(times, lambda t: np.random.normal(0,self.sigma))


class ThermalNoise(Signal):
    """Thermal Rayleigh noise at a given temperature (K) and resistance (ohms)
    in the frequency band f_band=[f_min,f_max] (Hz). Optional parameters are
    f_amplitude (default 1) which can be a number or a function designating the
    amplitudes at each frequency, and n_freqs which is the number of frequencies
    to use (in f_band) for the calculation (default is based on the FFT bin size
    of given times array). Returned signal values are voltages (V)."""
    def __init__(self, times, temperature, resistance, f_band,
                 f_amplitude=1, n_freqs=0):
        # Calculation based on Rician (Rayleigh) noise model for ANITA:
        # https://www.phys.hawaii.edu/elog/anita_notes/060228_110754/noise_simulation.ps

        self.f_min, self.f_max = f_band
        # If number of frequencies is unspecified (or invalid),
        # determine based on the FFT bin size of the times array
        if n_freqs<1:
            n_freqs = (self.f_max - self.f_min) * (times[-1] - times[0])
            # Broken out into steps to ease understanding:
            #   duration = times[-1] - times[0]
            #   f_bin_size = 1 / duration
            #   n_freqs = (self.f_max - self.f_min) / f_bin_size

        # If number of frequencies is still zero (e.g. len(times)==1),
        # force it to 1
        if n_freqs<1:
            n_freqs = 1

        self.freqs = np.linspace(self.f_min, self.f_max, n_freqs,
                                 endpoint=False)

        # Allow f_amplitude to be either a function or a single value
        if callable(f_amplitude):
            self.amps = [f_amplitude(f) for f in self.freqs]
        else:
            self.amps = np.full(len(self.freqs), f_amplitude, dtype="float64")

        self.phases = np.random.rand(len(self.freqs)) * 2*np.pi

        # Set the time-domain signal by adding sinusoidal signals of each
        # frequency with the corresponding phase
        values = np.zeros(len(times))
        for freq, amp, phase in zip(self.freqs, self.amps, self.phases):
            # Skip zero-frequency component if it exists
            if freq==0:
                continue
            values += amp * np.cos(2*np.pi*freq * times + phase)

        # Normalization calculated by guess-and-check, but seems to work fine
        # normalization = np.sqrt(2/len(self.freqs))
        values *= np.sqrt(2/len(self.freqs))

        # So far, the units of the values are V/V_rms, so multiply by the
        # rms voltage: sqrt(4 * kB * T * R * bandwidth)
        values *= np.sqrt(4 * 1.38e-23 * temperature * resistance
                          * (self.f_max - self.f_min))

        super().__init__(times, values)
