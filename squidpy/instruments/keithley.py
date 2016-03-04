from squidpy.instrument import Instrument
import visa


class Keithley2182A(Instrument):
    '''
    Instrument driver for Keithley 2182A Nanovoltmeter
    '''
    def __init__(self, gpib_address='', name='keithleynano'):
        rm = visa.ResourceManager()
        self._visa_handle = rm.open_resource(gpib_address)
        self._visa_handle.read_termination = '\n'
        self._units = {'voltage': 'V', 'range': 'V'}
        super(Keithley2182A, self).__init__(name)
        self._visa_handle.write(':CONF:VOLT:DC')
        self._visa_handle.write('*RST')

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
    def __init__(self, gpib_address='',  name='currentsource'):
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
    def __init__(self, gpib_address='', name='sourcemeter'):
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
    def voltage_in(self):
        '''Get the current reading.'''
        return float(self._visa_handle.ask(':READ?').split(',')[0])
    
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

    @property
    def output(self):
        return {0: 'off', 1:'on'}[int(self._visa_handle.ask('OUTP?'))]

    @output.setter
    def output(self, value):
        status = 'ON' if ((value==True) or (value==1) or (value=='on')) else 'OFF'
        self._visa_handle.write('OUTP %s' %status)
    
    def __del__(self):
        self._visa_handle.close()

class Keithley7001(Instrument):
    '''
    Instrument driver for Keithley 7001 Switch system
    '''
    def __init__(self, gpib_address='',  name='keithleyswitch'):
        self._visa_handle = visa.ResourceManager().open_resource(gpib_address)
        self._visa_handle.read_termination = '\n'
        self._configs = {}
        super(Keithley7001, self).__init__(name)

    def open_all(self):
        self._visa_handle.write('OPEN ALL')

    def close(self, chanlist):
        self._visa_handle.write(':CLOSE (@%s)' %chanlist)

    def add_config(self, name, chanlist):
        self._configs.update({name: chanlist})

    def activate_config(self, chanlist):
        self.open_all()
        self.close(chanlist)

    @property
    def configs(self):
        return self._configs

class Keithley2600(Instrument):
    '''
    Instrument driver for Keithley 2600-model Source Meter (tested with 2636A)
    '''
    def __init__(self, gpib_address='', name='sourcemeter'):
        self._units = {'current': 'A','voltage': 'V'}
        self._visa_handle = visa.ResourceManager().open_resource(gpib_address)
        self._visa_handle.read_termination = '\n'
        super(Keithley2600, self).__init__(name)
        
    @property
    def currentA(self):
        '''Get the current reading for channel A.'''
        return float(self._visa_handle.query('print(smua.measure.i())'))
    @property
    def currentB(self):
        '''Get the current reading for channel B.'''
        return float(self._visa_handle.query('print(smub.measure.i())'))
    @currentA.setter
    def currentA(self, value):
        '''Set the source current for channel A.'''
        self._visa_handle.write('smua.source.func=smua.OUTPUT_DCAMPS;smua.source.leveli=%s' % value)
    @currentB.setter
    def currentB(self, value):
        '''Set the source current for channel B.'''
        self._visa_handle.write('smub.source.func=smub.OUTPUT_DCAMPS;smub.source.leveli=%s' % value)

    @property
    def voltageA(self):
        '''Get the voltage reading for channel A'''
        return float(self._visa_handle.query('print(smua.measure.v())'))
    @property
    def voltageB(self):
        '''Get the voltage reading for channel B'''
        return float(self._visa_handle.query('print(smub.measure.v())'))
    @voltageA.setter
    def voltageA(self, value):
        '''Set the source voltage for channel A.'''
        self._visa_handle.write('smua.source.func=smua.OUTPUT_DCVOLTS;smua.source.levelv=%s' % value)
    @voltageB.setter
    def voltageB(self, value):
        '''Set the source voltage for channel B.'''
        self._visa_handle.write('smub.source.func=smub.OUTPUT_DCVOLTS;smub.source.levelv=%s' % value)

    @property
    def modeA(self):
        '''Get the source function for channel A.'''
        return self._visa_handle.query('print(smuA.source.func())')
    @property
    def modeB(self):
        '''Get the source function for channel B.'''
        return self._visa_handle.query('print(smuB.source.func())')
    @modeA.setter
    def modeA(self, value):
        '''Set the source function ('voltage' or 'current') for channel A'''
        value={'voltage':'OUTPUT_DCVOLTS','current':'OUTPUT_DCAMPS'}[value]
        self._visa_handle.write('smua.source.func=smua.%s' % value)
    @modeB.setter
    def modeB(self, value):
        '''Set the source function ('voltage' or 'current') for channel B'''
        value={'voltage':'OUTPUT_DCVOLTS','current':'OUTPUT_DCAMPS'}[value]
        self._visa_handle.write('smub.source.func=smub.%s' % value)

    @property
    def outputA(self):
        '''Gets the source output ('on'/'off'/'highz') for channel A'''
        return {0: 'off', 1:'on', 2: 'highz'}[int(float(self._visa_handle.query('print(smua.source.output)')))]
    @property
    def outputB(self):
        '''Gets the source output ('on'/'off'/'highz')  for channel B'''
        return {0: 'off', 1:'on', 2: 'highz'}[int(float(self._visa_handle.query('print(smub.source.output)')))]
    @outputA.setter
    def outputA(self, value):
        '''Sets the source output ('on'/'off'/'highz') for channel A'''
        status = 'ON' if ((value==True) or (value==1) or (value=='on')) else 'OFF'
        self._visa_handle.write('smua.source.output= smua.OUTPUT_%s' %status)
    @outputB.setter
    def outputB(self, value):
        '''Sets the source output ('on'/'off'/'highz') for channel B'''
        status = 'ON' if ((value==True) or (value==1) or (value=='on')) else 'OFF'
        self._visa_handle.write('smub.source.output= smub.OUTPUT_%s' %status)

    @property
    def voltagelimitA(self,value):
        '''Get the output voltage compliance limit for channel A'''
        return float(self._visa_handle.query('print(smua.source.limitv'))
    @property
    def voltagelimitB(self,value):
        '''Get the output voltage compliance limit for channel B'''
        return float(self._visa_handle.query('print(smub.source.limitv'))
    @voltagelimitA.setter
    def voltagelimitA(self,value):
        '''Get the output voltage compliance limit for channel A'''
        return self._visa_handle.write('smua.source.limitv=%s' %value)
    @voltagelimitB.setter
    def voltagelimitB(self,value):
        '''Get the output voltage compliance limit for channel B'''
        return self._visa_handle.write('smub.source.limitv=%s' %value)


    @property
    def currentlimitA(self,value):
        '''Get the output current compliance limit for channel A'''
        return float(self._visa_handle.query('print(smua.source.limiti'))
    @property
    def currentlimitB(self,value):
        '''Get the output current compliance limit for channel B'''
        return float(self._visa_handle.query('print(smub.source.limiti'))
    @currentlimitA.setter
    def currentlimitA(self,value):
        '''Get the output current compliance limit for channel A'''
        return self._visa_handle.write('smua.source.limiti=%s' %value)
    @currentlimitB.setter
    def currentlimitB(self,value):
        '''Get the output current compliance limit for channel B'''
        return self._visa_handle.write('smub.source.limiti=%s' %value)

    def resetA(self):
        '''Resets the A channel'''
        self._visa_handle.write('smua.reset()')
    def resetB(self):
        '''Resets the B channel'''
        self._visa_handle.write('smub.reset()')
    
    def __del__(self):
        self._visa_handle.close()