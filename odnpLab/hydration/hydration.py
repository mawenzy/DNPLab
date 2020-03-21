""" Hydration module
class               description
------------------  ------------------------------------------------------------
HydrationParameter          Experiment options, including field, spin label concentrations
Results             Hydration results

function            description
------------------  ------------------------------------------------------------
interpolateT1       # input should be odnpData object, adds to this the interpolated T1p
_calcODNP            # input should be odnpData object, HydrationParameter object which
                    should contain 'field', 'slC', 'T100', bulk values, choice
                    of smax model, output should be Results object
getTcorr            # returns correlation time tcorr
"""

import numpy as np
from scipy import interpolate
from scipy import optimize
from odnpLab.hydration.hydration_parameter import HydrationParameter
from odnpLab.parameter import AttrDict


# WorkInProgress: it depends on how eventually the odnpData object is going to store the
# T1p, T1_power, Enhancements, Enhancement_power.
# TODO: figure out the interface of hydration module to odnpImport module


class HydrationResults(AttrDict):
    """Class for handling hydration results"""
    pass


class HydrationCalculator:
    """"""
    def __init__(self, T1: np.array, T1_power: np.array, E: np.array, E_power: np.array, hp: HydrationParameter):
        """
        :param T1: np.array of T1
        :param T1_power: np.array of power in Watt unit, same length as T1
        :param E: np.array of enhancement
        :param E_power: np.array of power in Watt unit, same length as E
        :param hp: HydrationParameter
        """
        super().__init__()

        if any([x.ndim > 1 for x in [T1, T1_power, E, E_power]]):
            raise ValueError('T1, T1_power, E and E_power must be 1 dimension')
        if T1.size != T1_power.size:
            raise ValueError('T1 and T1_power must have same length')
        if E.size != E_power.size:
            raise ValueError('E and E_power must have same length')

        self.T1, self.T1_power, self.E, self.E_power = T1, T1_power, E, E_power

        self.hp = hp

        self.T1fit = None
        self.results = None

        self._setT1p()
        self._calcODNP()

    def _setT1p(self):
        """
        set T1fit to an np.array of T1 at given POWER
            points inside the data range will be interpolated
            points outside the data range will be extrapolated
        """
        T1p, T1power = self.T1, self.T1_power
        power = self.E_power
        T10, T100, slC = self.hp.T10, self.hp.T100, self.hp.slC

        t1_fitopt = self.hp.fitopt

        if t1_fitopt=='2ord': # 2nd order fit, Franck and Han MIE (Eq. 22) and (Eq. 23)

            delT1w=T1p[-1]-T1p[0]  #Fixme: This requires T1p to be ascending, any better way?
            T1w=T100
            macroC=slC

            kHH = ((1./T10) - (1./(T1w))) / (macroC/1e6)
            krp=((1./T1p)-(1./(T1w + delT1w * T1power))-(kHH*(macroC/1e6))) / (slC/1e6)

            p = np.polyfit(T1power, krp, 2)
            flinear = np.polyval(p, power)

            intT1 = 1./(((slC/1e6) * flinear)+(1./(T1w + delT1w * power))+(kHH * (macroC/1e6)))

        elif t1_fitopt=='linear': # linear fit, Franck et al. PNMRS (Eq. 39)

            linearT1=1./((1./T1p)-(1./T10)+(1./T100))

            p = np.polyfit(T1power, linearT1, 1)
            flinear = np.polyval(p, power)

            intT1=flinear/(1.+(flinear/T10)-(flinear/T100))

        else:
            raise Exception('NotImplemented T1 fitopt')

        self.T1fit = intT1

    def _calcODNP(self):
        """ returns a HydrationResults object that contains all calculated ODNP values

        Following: J.M. Franck et al. / Progress in Nuclear Magnetic Resonance Spectroscopy 74 (2013) 33–56
        equations are labeled (#) for where they appear in the paper, sections are specified in some cases

        :param hdata: HydrationCalculator object that contains Enhancement, T1 and power
        :param expopts: np.array of T1, should be same length as Ep
        :return:
            HydrationResults, object that contains all relevant hydration values
        """
        # Ep is the array of enhancements
        # T1p is the array of T1s after interpolated to match the enhancement
        # array.
        Ep, T1p, power = self.E, self.T1fit, self.E_power

        # field and spin label concentration are defined in Hydration Parameter
        field, slC = self.hp.field, self.hp.slC

        T10 = self.hp.T10  # this is the T1 with spin label but at 0 mw power, unit is sec
        T100 = self.hp.T100  # this is the T1 without spin label and without mw power, unit is sec

        if self.hp.smaxMod == 'tethered':
            # Option 1, tether spin label
            s_max = 1  # (section 2.2) maximal saturation factor

        else:
            # Option 2, free spin probe
            s_max = 1-(2/(3+(3*(slC*1e-6*198.7)))) # from:
            # M.T. Türke, M. Bennati, Phys. Chem. Chem. Phys. 13 (2011) 3630. &
            # J. Hyde, J. Chien, J. Freed, J. Chem. Phys. 48 (1968) 4211.

        omega_e = (1.76085963023e5 * 1e-6) * (field / 1000)
        # gamma_e in MHz/T, convert to 1/ps for the tcorr unit later, then correct by field in T.
        # gamma_e is from NIST. The field cancels in the following wRatio but you
        # need these individually for the spectral density functions later.

        omega_H = (267.52218744 * 1e-6) * (field / 1000)
        # gamma_H in MHz/T, convert to 1/ps for the tcorr unit later, then correct by field in T.
        # gamma_H is from NIST. The field cancels in the following wRatio but you
        # need these individually for the spectral density functions later.

        wRatio = ((omega_e / (2 * 3.14159)) / (omega_H / (2 * 3.14159)))
        # (Eq. 4-6) ratio of omega_e and omega_H, divide by (2*pi) to get angular
        # frequency units in order to correspond to S_0/I_0, this is also ~= to the
        # ratio of the resonance frequencies for the experiment, i.e. MW freq/RF freq

        ksig_sp = (1 - Ep) / (slC * wRatio * T1p)
        # (Eq. 41) this calculates the array of k_sigma*s(p) from the enhancement array,
        # dividing by the T1p array for the "corrected" analysis

        ksig_smax , p_12 = self.getksigsmax(ksig_sp, power)
        # fit to the right side of Eq. 42 to get (k_sigma*smax) and half of the power at s_max, called p_12 here

        #################
        # TODO: plot: 'Data', {power, ksig_sp}, and the 'Corrected', {power, ksigsp_fit},
        #  and 'Uncorrected', {power, ksig_sp_uncorr} that are calculated below to assess
        #  the quality of fit as well as compare "corrected" to "uncorrected" analyses to assess heating.

        ksigsp_fit = (ksig_smax * power) / (p_12 + power)
        # (Eq. 42) calculate the "corrected" k_sigma*s(p) array using the fit parameters,
        # this can be used to plot over the data ksig_sp array to assess the quality of fit.
        # This would correspond to the corrected curves in Figure 9

        ksig_sp_uncorr = (1 - Ep) / (slC * wRatio * T10)
        # (Eq. 44) the "uncorrected" model, this can also be plotted with the corrected
        # curve to determine the severity of heating effects, as in Figure 9.
        # Notice the division by T10 instead of the T1p array
        #################

        k_sigma = ksig_smax / s_max
        # (Eq. 43) this divides by the s_max to isolate k_sigma, the "cross" relaxivity, unit is s^-1 M^-1

        ksig_bulk = self.hp.ksig_bulk  # unit is s^-1 M^-1
        # The only place I can find this is Franck, JM, et. al.; "Anomalously Rapid
        # Hydration Water Diffusion Dynamics Near DNA Surfaces" J. Am. Chem. Soc.
        # 2015, 137, 12013−12023. Figure 3 caption

        k_rho = ((1/T10) - (1/T100)) / slC  # (Eq. 36) "self" relaxivity, unit is s^-1 M^-1

        ksi = k_sigma / k_rho  # (Eq. 3) this is the coupling factor, unitless

        tcorr = self.getTcorr(ksi, omega_e, omega_H)
        # (Eq. 21-23) this calls the fit to the spectral density functions. The fit
        # optimizes the value of tcorr in the calculation of ksi, the correct tcorr
        # is the one for which the calculation of ksi from the spectral density
        # functions matches the ksi found experimentally. tcorr unit is ps

        tcorr_bulk = self.hp.tcorr_bulk  # (section 2.5), "corrected" bulk tcorr, unit is ps

        dH2O = self.hp.dH2O
        # (Eq. 19-20) bulk water diffusivity, unit is d^2/s where d is distance in
        # meters. *didnt use m to avoid confusion with mass

        dSL = self.hp.dSL
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

        k_low_bulk = self.hp.k_low_bulk  # unit is s^-1 M^-1
        # The only place I can find this is Franck, JM, et. al.; "Anomalously Rapid
        # Hydration Water Diffusion Dynamics Near DNA Surfaces" J. Am. Chem. Soc.
        # 2015, 137, 12013−12023. Figure 3 caption

        # this list should be in the Results object,
        # should also include flags, exceptions, etc. related to calculations
        self.results = HydrationResults({
            'k_sigma_array' : ksig_smax / s_max,
            'k_sigma': k_sigma,
            'ksigma_kbulk_invratio' : 1/(k_sigma/ksig_bulk),
            'k_rho'  : k_rho,
            'k_low'  : k_low,
            'klow_klow_bulk_ratio': k_low / k_low_bulk,
            'ksi'    : ksi,
            'tcorr'  : tcorr,
            'tcorr_tcorr_bulk_ratio': tcorr / tcorr_bulk,
            'dLocal' : dLocal
        })

    @staticmethod
    def getTcorr(ksi: float, omega_e: float, omega_H: float):
        """
        returns correlation time tcorr in pico second

        :param ksi: float of epsilon
        :param omega_e: float
        :param omega_H: float
        :return:
            float tcorr
        """

        def get_ksi(tcorr: float, omega_e: float, omega_H: float):
            """
            returns ksi for any given tcorr

            :param tcorr: float  # TODO: unit?
            :param omega_e: float
            :param omega_H: float
            :return:
                float ksi
            """

            # Using Barnes et al. JACS (2017)

            zdiff = (omega_e - omega_H) * tcorr
            zsum  = (omega_e + omega_H) * tcorr
            zH    = omega_H * tcorr

            # (Eq. 2)
            Jzdiff = (1 + (((5*np.sqrt(2))/8) * np.sqrt(zdiff)) + (zdiff/4)) / (1 + np.sqrt(2*zdiff) + zdiff + ((np.sqrt(2)/3) * (zdiff**(3/2))) + ((16/81) * (zdiff**2)) + (((4*np.sqrt(2))/81) * (zdiff**(5/2))) + ((zdiff**3)/81))

            Jzsum  = (1 + (((5*np.sqrt(2))/8) * np.sqrt(zsum)) + (zsum/4)) / (1 + np.sqrt(2*zsum) + zsum + ((np.sqrt(2)/3) * (zsum**(3/2))) + ((16/81) * (zsum**2)) + (((4*np.sqrt(2))/81) * (zsum**(5/2))) + ((zsum**3)/81))

            JzH    = (1 + (((5*np.sqrt(2))/8) * np.sqrt(zH)) + (zH/4)) / (1 + np.sqrt(2*zH) + zH + ((np.sqrt(2)/3) * (zH**(3/2))) + ((16/81) * (zH**2)) + (((4*np.sqrt(2))/81) * (zH**(5/2))) + ((zH**3)/81))

            option = 0

            if option==0: # don't include J_Rot

                Jdiff = Jzdiff
                Jsum = Jzsum
                JH = JzH

            if option==1: # include J_Rot, (Eq. 6) from Barnes et al. JACS (2017)

                percentBound = 0
                tauRot = 1 # in ns

                Jdiff = (1 - (percentBound/100)) * Jzdiff + ((percentBound/100) * ((tauRot*1000) / (1 - (1j*(omega_e - omega_H) * (tauRot*1000)))))

                Jsum  = (1 - (percentBound/100)) * Jzsum + ((percentBound/100) * ((tauRot*1000) / (1 - (1j*(omega_e + omega_H) * (tauRot*1000)))))

                JH    = (1 - (percentBound/100)) * JzH + ((percentBound/100) * ((tauRot*1000) / (1 - (1j*omega_H * (tauRot*1000)))))

            # (Eq. 23) calculation of ksi from the spectral density functions
            ksi_tcorr = ((6 * np.real(Jdiff)) - np.real(Jsum)) / ((6 * np.real(Jdiff)) + (3 * np.real(JH)) + np.real(Jsum))

            return ksi_tcorr

        # root finding
        # see https://docs.scipy.org/doc/scipy/reference/optimize.html
        result = optimize.root_scalar(
            lambda tcorr: get_ksi(tcorr, omega_e=omega_e, omega_H=omega_H) - ksi,
            method='brentq',
            bracket=[1, 1e5])

        assert result.converged
        return result.root

    @staticmethod
    def getksigsmax(ksig_sp: float, power: float):
        """
        Get ksig_smax and p_12
        :param ksig_sp: float of array of (k_sigma * s(p))
        :param power: float of power array
        :return:
            float tuple. ksig_smax, p_12
        """
        def residual(x, p: np.array, ksig_sp: np.array):
            """
            residual function for ksigs_p for any given ksig_smax and p_12
            :param x: parameters. p = [ksig_smax, p_12]
            :param p: float of power array
            :param ksig_sp: float of array of (k_sigma * s(p))
            :return:
                residuals
            """
            ksig_smax, p_12 = x[0], x[1]

            # Again using: J.M. Franck et al. / Progress in Nuclear Magnetic Resonance Spectroscopy 74 (2013) 33–56

            # Right side of Eq. 42. This function should fit to ksig_sp
            ksigsp_fit = (ksig_smax * p) / (p_12 + p)

            return ksigsp_fit - ksig_sp

        # least-squares fitting. I like this one because it can calculate a jacobian that we can use to get an estimate of the error in k_sigma.
        # see https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html#scipy.optimize.least_squares
        result = optimize.least_squares(fun=residual,
                                         x0=[75, (max(power) / 2)],
                                         args=(power, ksig_sp),
                                         jac='3-point', method='lm')

        assert result.success
        return result.x