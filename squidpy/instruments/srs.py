from squidpy.instrument import Instrument
import visa

class SR830(Instrument):
    '''
    Instrument driver for SR830
    '''
    def __init__(self, gpib_address='', name='SR830'):
        self._units = {'amplitude': 'V', 'frequency': 'Hz'}
        self._visa_handle = visa.ResourceManager().open_resource(gpib_address)
        self._visa_handle.read_termination = '\n'
        self.time_constant_options = {
                "10 us": 0,
                "30 us": 1,
                "100 us": 2,
                "300 us": 3,
                "1 ms": 4,
                "3 ms": 5,
                "10 ms": 6,
                "30 ms": 7,
                "100 ms": 8,
                "300 ms": 9,
                "1 s": 10,
                "3 s": 11,
                "10 s": 12,
                "30 s": 13,
                "100 s": 14,
                "300 s": 15,
                "1 ks": 16,
                "3 ks": 17,
                "10 ks": 18,
                "30 ks": 19
            }
        self.sensitivity_options = [
        2e-9, 5e-9, 10e-9, 20e-9, 50e-9, 100e-9, 200e-9,
        500e-9, 1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6,
        200e-6, 500e-6, 1e-3, 2e-3, 5e-3, 10e-3, 20e-3,
        50e-3, 100e-3, 200e-3, 500e-3, 1]
        super(SR830, self).__init__(name)

    @property
    def sensitivity(self):
        '''Get the lockin sensitivity'''
        return self.sensitivity_options[int(self._visa_handle.ask('SENS?'))]

    @sensitivity.setter
    def sensitivity(self, value):
        '''Set the sensitivity'''
        self._visa_handle.write('SENS%d' %self.sensitivity_options.index(value))

    @property
    def amplitude(self):
        '''Get the output amplitude'''
        return self._visa_handle.ask('SLVL?')
    
    @amplitude.setter
    def amplitude(self, value):
        '''Set the amplitude.'''
        self._visa_handle.write('SLVL %s' %value)
    
    @property
    def frequency(self):
        return self._visa_handle.ask('FREQ?')

    @frequency.setter
    def frequency(self, value):
        self._visa_handle.write('FREQ %s' %value)

    @property
    def X(self):
        return float(self._visa_handle.ask('OUTP?1'))

    @property
    def Y(self):
        return float(self._visa_handle.ask('OUTP?2'))

    @property
    def R(self):
        return float(self._visa_handle.ask('OUTP?3'))

    @property
    def theta(self):
        return float(self._visa_handle.ask('OUTP?4'))

    @property
    def time_constant(self):
        options = {self.time_constant_options[key]: key for key in self.time_constant_options.keys()}
        return options[int(self._visa_handle.ask('OFLT?'))]

    @time_constant.setter
    def time_constant(self, value):
        self._visa_handle.write('OFLT %s' %self.time_constant_options[value])
    
    def __del__(self):
        self._visa_handle.close()