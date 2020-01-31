# hydration function(s)
# goal: take odnpImport and output tcorr and many observables

import numpy as np
from scipy import interpolate
from scipy import optimize

# Define constants


def getT1p(T1: np.array, power: np.array): # input should be odnpData object, adds to this the interpolated T1p
    """
    returns a function to calculate T1 at arbitrary power

    :param T1: np.array of T1
    :param power: np.array of power in Watt unit, same length as T1
    :return
        a function that takes power and returns T1.
        points inside the data range will be linearly interpolated
        points outside the data range will be extrapolated
    """
    assert len(T1) == len(power)
    return interpolate.interp1d(power, T1,
                                kind='linear',
                                fill_value='extrapolate')


def calcODNP(Ep: np.array, T1p: np.array): # input should be odnpData object, ExpOptions object which should contain 'field', 'slC', 'T100', bulk values, choice of smax model, output should be Results object
    """
    returns all calculated values

    :param Ep: np.array of enhancements
    :param T1p: np.array of T1, should be same length as Ep
    :return:
        dictionary of the following parameters:
            'k_sigma': k_sigma,
            'k_rho'  : k_rho,
            'ksi'    : ksi,
            'tcorr'  : tcorr,
            'dLocal' : dLocal,
            'k_low'  : k_low
    """
    # Following: J.M. Franck et al. / Progress in Nuclear Magnetic Resonance Spectroscopy 74 (2013) 33–56
    # equations are labeled (#) for where they appear in the paper, sections are specified in some cases
    
    field = 348.5  # static magnetic field in mT, needed to find omega_e and _H

    slC = 200e-6
    # (Eq. 1-2) unit is M, spin label concentration for scaling relaxations to
    # get "relaxivities"
    
    # TODO: define "if" statement for chosing smax option based on smax model choice in ExpOptions object
    # Option 1, tether spin label
    s_max = 1  # (section 2.2) maximal saturation factor
    
    # Option 2, free spin probe
    s_max = 1-(2/(3+(3*(slC*1e-6*198.7)))) # from:
    # M.T. Türke, M. Bennati, Phys. Chem. Chem. Phys. 13 (2011) 3630. &
    # J. Hyde, J. Chien, J. Freed, J. Chem. Phys. 48 (1968) 4211.

    omega_e = (1.76085963023e5 * 1e-6) * (field / 1000) # gamma_e in MHz/T, convert to 1/ps for the tcorr unit later, then correct by field in T.
    # gamma_e is from NIST. The field cancels in the following wRatio but you need these individually for the spectral density functions later.

    omega_H = (267.52218744 * 1e-6) * (field / 1000) # gamma_H in MHz/T, convert to 1/ps for the tcorr unit later, then correct by field in T.
    # gamma_H is from NIST. The field cancels in the following wRatio but you need these individually for the spectral density functions later.

    wRatio = ((omega_e / (2 * 3.14159)) / (omega_H / (2 * 3.14159)))  # (Eq. 4-6) ratio of omega_e and omega_H, divide by (2*pi) to get angular frequency units in order to correspond to S_0/I_0, this is also ~= to the ratio of the resonance frequencies for the experiment, i.e. MW freq/RF freq

    # Ep will be the series of enhancements
    # T1p will be the series of T1s after interpolated to match the enhancement
    # series. Power not needed anymore, it is only used to line up and
    # interpolate the T1s to the Enhancements

    ksig_smax = (1 - Ep) / (slC * wRatio * T1p)
    # (Eq. 42) this calculates the series of k_sigma*s(p) which approximates to
    # k_sigma*s_max

    k_sigma = max(ksig_smax) / s_max
    # (Eq. 43) this takes the maximum of the k_sigma*s(p) series and divides by
    # the s_max to isolate k_sigma, unit is s^-1 M^-1

    ksig_bulk = 95.4  # unit is s^-1 M^-1
    # The only place I can find this is Franck, JM, et. al.; "Anomalously Rapid
    # Hydration Water Diffusion Dynamics Near DNA Surfaces" J. Am. Chem. Soc.
    # 2015, 137, 12013−12023. Figure 3 caption

    T10 = 1.33  # this is the T1 with spin label but at 0 mw power, unit is sec
    T100 = 2.5  # this is the T1 without spin label and without mw power, unit is sec
    k_rho = ((1/T10) - (1/T100)) / slC  # (Eq. 36) "self" relaxivity, unit is s^-1 M^-1

    ksi = k_sigma / k_rho  # (Eq. 3) this is the coupling factor, unitless

    tcorr = getTcorr(ksi, omega_e, omega_H)
    # (Eq. 21-23) this calls the fit to the spectral density functions. The fit
    # optimizes the value of tcorr in the calculation of ksi, the correct tcorr
    # is the one for which the calculation of ksi from the spectral density
    # functions matches the ksi found experimentally. tcorr unit is ps

    tcorr_bulk = 54  # (section 2.5), "corrected" bulk tcorr, unit is ps

    dH2O = 2.3e-9
    # (Eq. 19-20) bulk water diffusivity, unit is d^2/s where d is distance in
    # meters. *didnt use m to avoid confusion with mass

    dSL = 4.1e-10
    # (Eq. 19-20) spin label diffusivity, unit is d^2/s where d is distance in
    # meters. *didnt use m to avoid confusion with mass

    dLocal = (tcorr_bulk / tcorr) * (dH2O + dSL)
    # (Eq. 19-20) local diffusivity, i.e. diffusivity of the water near the spin label

    ############################################################################
    # This is defined in its most compact form in:
    # Frank, JM and Han, SI;  Chapter Five - Overhauser Dynamic Nuclear Polarization
    # for the Study of Hydration Dynamics, Explained. Methods in Enzymology, Volume 615, 2019
    #
    # But also explained well in:
    # Franck, JM, et. al.; "Anomalously Rapid Hydration Water Diffusion Dynamics
    # Near DNA Surfaces" J. Am. Chem. Soc. 2015, 137, 12013−12023.

    k_low = ((5 * k_rho) - (7 * k_sigma)) / 3
    # section 6, (Eq. 13). this describes the relatively slowly diffusing water
    # near the spin label, sometimes called "bound" water
    ############################################################################

    k_low_bulk = 366  # unit is s^-1 M^-1
    # The only place I can find this is Franck, JM, et. al.; "Anomalously Rapid
    # Hydration Water Diffusion Dynamics Near DNA Surfaces" J. Am. Chem. Soc.
    # 2015, 137, 12013−12023. Figure 3 caption
    
    # this list should be in the Results object,
    # should also include flags, exceptions, etc. related to calculations
    return {
        'k_sigma_array' : ksig_smax / smax,
        'k_sigma': k_sigma,
        'ksigma_kbulk_invratio' : 1/(k_sigma/ksig_bulk),
        'k_rho'  : k_rho,
        'k_low'  : k_low,
        'klow_klow_bulk_ratio': k_low / k_low_bulk,
        'ksi'    : ksi,
        'tcorr'  : tcorr,
        'tcorr_tcorr_bulk_ratio': tcorr / tcorr_bulk,
        'dLocal' : dLocal
    }


def getTcorr(ksi: float, omega_e: float, omega_H: float):
    """
    returns correlation time tcorr

    :param ksi: float of epsilon
    :param omega_e: float
    :param omega_H: float
    :return:
        float tcorr
    """

    def get_ksi(tcorr: float, omega_e: float, omega_H: float):
        """
        returns ksi for any given tcorr

        :param tcorr: float
        :param omega_e: float
        :param omega_H: float
        :return:
            float ksi
        """

        # Again using: J.M. Franck et al. / Progress in Nuclear Magnetic Resonance Spectroscopy 74 (2013) 33–56

        # (Eq. 22), difference, sum and H terms for "z"
        zdiff = np.sqrt(1j * (omega_e - omega_H) * tcorr)
        zsum  = np.sqrt(1j * (omega_e + omega_H) * tcorr)
        zH    = np.sqrt(1j * omega_H * tcorr)

        # (Eq. 21) the three forms of the FFHS spectral density function corresponding to the three "z" terms above
        Jdiff = np.real((1 + (zdiff / 4)) / (1 + zdiff + ((4 * (zdiff ** 2)) / 9) + ((zdiff ** 3) / 9)))
        Jsum  = np.real((1 + (zsum  / 4)) / (1 + zsum  + ((4 * (zsum ** 2)) / 9)  + ((zsum ** 3) / 9)))
        JH    = np.real((1 + (zH    / 4)) / (1 + zH    + ((4 * (zH ** 2)) / 9)    + ((zH ** 3) / 9)))
        
        # (Eq. 23) calculation of ksi from the spectral density functions
        ksi_tcorr = ((6 * Jdiff) - Jsum) / ((6 * Jdiff) + (3 * JH) + Jsum)

        return ksi_tcorr

    # root finding
    # see https://docs.scipy.org/doc/scipy/reference/optimize.html
    results = optimize.root_scalar(
        lambda tcorr: ((get_ksi(tcorr, omega_e=omega_e, omega_H=omega_H) - ksi) ** 2),
        method='newton',
        x0=500)

    assert results.converged
    return results.root