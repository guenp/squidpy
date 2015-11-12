from squidpy.instrument import Instrument
import visa

class Keithley2400(Instrument):
    '''
    Instrument driver for Keithley 2400 Source Meter
    '''
    def __init__(self, name='keithley', gpib_address=''):
        self.units = {'current': 'A',
                      'voltage': 'V'}
        self.visa_handle = visa.ResourceManager().open_resource(gpib_address)
        self.visa_handle.read_termination = '\n'
        super(Keithley2400, self).__init__(name)
        
    @property
    def current(self):
        '''Get the current reading.'''
        return float(self.visa_handle.ask(':READ?').split(',')[1])
    
    @property
    def voltage(self):
        '''Get the output voltage'''
        return float(self.visa_handle.ask(':SOUR:VOLT:LEV:AMPL?'))
    
    @voltage.setter
    def voltage(self, value):
        '''Set the voltage.'''
        self.visa_handle.write(':SOUR:VOLT:LEV %s' %value)
    
    @property
    def mode(self):
        '''Get the source function.'''
        options = {
                "VOLT": "voltage",
                "CURR": "current",
                "MEM": "memory"}
        return options[self.visa_handle.ask(':SOUR:FUNC:MODE?')]
    
    @mode.setter
    def mode(self, value):
        '''Set the source function'''
        options = {
                "voltage": "VOLT",
                "current": "CURR",
                "memory": "MEM"}
        self.visa_handle.write(':SOUR:FUNC:MODE %s' %options[value])
        