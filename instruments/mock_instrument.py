import numpy, time
from squidpy.instrument import Instrument

class Mock(Instrument):
    '''
    Mock instrument for testing squidpy.
    '''
    def __init__(self, wait=.1, name='mock'):
        self._wait = wait
        self._tstart = 0
        self._voltage = 10
        self._output_voltage = 0
        self._time = 0
        self._wave = self.wave
        self._units = {'voltage': 'V',
                      'output_voltage': 'V',
                      'time': 's',
                      'wave': 'a.u.'}
        super(Mock, self).__init__(name)
        
    @property
    def time(self):
        """Get elapsed time"""
        if self._tstart==0:
            self._tstart = time.time()
        self._time = time.time()-self._tstart
        return self._time
    
    @time.setter
    def time(self, value):
        """
        Wait for the timer to reach the specified time.
        If value = 0, reset.
        """
        if value==0:
            self._tstart = 0
        else:
            while self.time < value:
                time.sleep(0.001)
        return True

    def reset_time(self):
        '''Reset the timer to 0 s.'''
        self.time = 0
        self.time

    @property
    def wave(self):
        """Get wave."""
        return float(numpy.sin(self.time))

    @property
    def voltage(self):
        """Get the voltage."""
        time.sleep(self._wait)
        return self._voltage
    
        def __getitem__(self, keys):
            return keys
    
    @property
    def output_voltage(self):
        return self._output_voltage
    
    @output_voltage.setter
    def output_voltage(self, value):
        """Set the voltage."""
        time.sleep(self._wait)
        self._output_voltage = value