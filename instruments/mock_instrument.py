import numpy, time
from squidpy.instrument import Instrument, Timer

class Mock(Instrument):
    '''
    Mock instrument for testing squidpy.
    '''
    def __init__(self, name='mock'):
        self.timer = Timer()
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
        return self.timer.get()
    
    @time.setter
    def time(self, value):
        """Set the time"""
        self.timer.reset(value)

    @property
    def wave(self):
        """Get wave."""
        return float(numpy.sin(self.time))

    @property
    def voltage(self):
        """Get the voltage."""
        return self._voltage
    
    @voltage.setter
    def voltage(self, value):
        """Set the voltage."""
        self._voltage = value
        
    def reset_timer(self):
        self.timer.reset(time.time())