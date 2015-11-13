import numpy, time
from squidpy.instrument import Instrument

class Mock(Instrument):
    '''
    Mock instrument for testing squidpy.
    '''
    def __init__(self, name='mock'):
        self.tstart = 0
        self._voltage = 10
        self._time = 0
        self._wave = self.wave
        self.units = {'voltage': 'V',
                      'time': 's',
                      'wave': 'a.u.'}
        super(Mock, self).__init__(name)
        
    @property
    def time(self):
        """Get elapsed time"""
        if self.tstart==0:
            self.tstart = time.time()
        self._time = time.time()-self.tstart
        return self._time
    
    @time.setter
    def time(self, value):
        """
        Wait for the timer to reach the specified time.
        If value = 0, reset.
        """
        if value==0:
            self.tstart = 0
        else:
            while self.time < value:
                time.sleep(0.001)
        return True

    @property
    def wave(self):
        """Get wave."""
        time.sleep(0.1)
        return float(numpy.sin(self.time))

    @property
    def voltage(self):
        """Get the voltage."""
        time.sleep(0.1)
        return self._voltage
    
        def __getitem__(self, keys):
            return keys
    
    @voltage.setter
    def voltage(self, value):
        """Set the voltage."""
        time.sleep(0.1)
        self._voltage = value