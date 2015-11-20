from squidpy.instrument import Instrument
import visa

class Keithley2182A(Instrument):
    '''
    Instrument driver for Keithley 2182A Nanovoltmeter
    '''
    def __init__(self, name='keithleynano', gpib_address=''):
        rm = visa.ResourceManager()
        self._visa_handle = rm.open_resource(gpib_address)
        self._visa_handle.read_termination = '\n'
        self._units = {'voltage': 'V', 'range': 'V'}
        super(Keithley2182A, self).__init__(name)
        self._visa_handle.write(':CONF:VOLT:DC')

    @property
    def voltage(self):
        '''Get input voltage'''
        return float(self._visa_handle.ask(':READ?'))

    @property
    def nplc(self):
        return float(self._visa_handle.ask(':SENS:VOLT:DC:NPLC?'))

    @nplc.setter
    def nplc(self, value):
        self._visa_handle.write(':SENS:VOLT:DC:NPLC %s' %value)

    @property
    def range(self):
        return float(self._visa_handle.ask(':SENS:VOLT:DC:RANG?'))

    @range.setter
    def range(self, value):
        self._visa_handle.write(':SENS:VOLT:DC:RANG %s' %value)

    @property
    def autorange(self):
        return {0:'off', 1:'on'}[int(self._visa_handle.ask(':SENS:VOLT:RANG:AUTO?'))]

    @autorange.setter
    def autorange(self, value):
        status = 'ON' if (value==True or (value==1) or (value=='on')) else 'OFF'
        self._visa_handle.write('SENS:VOLT:RANG:AUTO %s' %status)

    def __del__(self):
        self._visa_handle.close()
    
class Keithley6220(Instrument):
    '''
    Instrument driver for Keithley 6220 DC current source
    '''
    def __init__(self, name='keithleynano', gpib_address=''):
        self._visa_handle = visa.ResourceManager().open_resource(gpib_address)
        self._visa_handle.read_termination = '\n'
        self._units = {'current': 'A', 'compliance': 'A'}
        super(Keithley6220, self).__init__(name)

    @property
    def current(self):
        return float(self._visa_handle.ask('SOUR:CURR?'))

    @current.setter
    def current(self, value):
        self._visa_handle.write('SOUR:CURR %s' %value)

    @property
    def compliance(self):
        return float(self._visa_handle.ask('SOUR:CURR:COMP?'))

    @compliance.setter
    def compliance(self, value):
        self._visa_handle.write('SOUR:CURR:COMP %s' %value)

    @property
    def output(self):
        return {0: 'off', 1:'on'}[int(self._visa_handle.ask('OUTP?'))]

    @output.setter
    def output(self, value):
        status = 'ON' if ((value==True) or (value==1) or (value=='on')) else 'OFF'
        self._visa_handle.write('OUTP %s' %status)
        
    def clear(self):
        '''Reset the device and set output off.'''
        self._visa_handle.write('CLE')

    def linear_sweep(self, start, stop, step, delay, count):
        '''Start a linear sweep: (start, stop, step, delay, count)'''
        self._visa_handle.write('SOUR:SWE:SPAC LIN')
        self._visa_handle.write('SOUR:CURR:STAR %s' %start)
        self._visa_handle.write('SOUR:CURR:STOP %s' %stop)
        self._visa_handle.write('SOUR:CURR:STEP %s' %step)
        self._visa_handle.write('SOUR:DEL %s' %delay)
        self._visa_handle.write('SOUR:SWE:COUN %s' %count)
        self._visa_handle.write('SOUR:SWE:CAB OFF')
        self._visa_handle.write('SOUR:SWE:ARM')
        self._visa_handle.write('INIT')

    def __del__(self):
        self._visa_handle.close()

class Keithley2400(Instrument):
    '''
    Instrument driver for Keithley 2400 Source Meter
    '''
    def __init__(self, name='keithley', gpib_address=''):
        self._units = {'current': 'A',
                      'voltage': 'V'}
        self._visa_handle = visa.ResourceManager().open_resource(gpib_address)
        self._visa_handle.read_termination = '\n'
        super(Keithley2400, self).__init__(name)
        
    @property
    def current(self):
        '''Get the current reading.'''
        return float(self._visa_handle.ask(':READ?').split(',')[1])
    
    @property
    def voltage(self):
        '''Get the output voltage'''
        return float(self._visa_handle.ask(':SOUR:VOLT:LEV:AMPL?'))
    
    @voltage.setter
    def voltage(self, value):
        '''Set the voltage.'''
        self._visa_handle.write(':SOUR:VOLT:LEV %s' %value)
    
    @property
    def mode(self):
        '''Get the source function.'''
        options = {
                "VOLT": "voltage",
                "CURR": "current",
                "MEM": "memory"}
        return options[self._visa_handle.ask(':SOUR:FUNC:MODE?')]
    
    @mode.setter
    def mode(self, value):
        '''Set the source function'''
        options = {
                "voltage": "VOLT",
                "current": "CURR",
                "memory": "MEM"}
        self._visa_handle.write(':SOUR:FUNC:MODE %s' %options[value])
    
    def __del__(self):
        self._visa_handle.close()