from squidpy.instrument import Instrument
import visa

class Yokogawa7651(Instrument):
    '''
    Instrument driver for Keithley 2400 Source Meter
    '''
    def __init__(self, gpib_address='', name='yokogawa'):
        self._units = {'voltage': 'V'}
        self._visa_handle = visa.ResourceManager().open_resource(gpib_address)
        self._voltage = 0
        self._output = 0
        super(Yokogawa7651, self).__init__(name)
        
    @property
    def voltage(self):
        '''Get the output voltage'''
        return self._voltage
    
    @voltage.setter
    def voltage(self, value):
        '''Set the voltage.'''
        self._voltage = value
        self._visa_handle.write('SA%s;E;' %value)
    
    @property
    def output(self):
        return {1: 'on', 0: 'off'}[self._output]

    @output.setter
    def output(self, value):
        status = 1 if ((value==True) or (value=='ON') or (value=='on')) else 0
        self._output = status
        self._visa_handle.write('O%s;E;' %status)
    
    def __del__(self):
        self._visa_handle.close()