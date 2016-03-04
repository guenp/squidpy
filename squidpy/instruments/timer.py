import numpy, time
from squidpy.instrument import Instrument

class Timer(Instrument):
    '''
    Timer instrument for keeping track of time.
    '''
    def __init__(self, name='timer'):
        self._tstart = 0
        self._time = 0
        self._units = {'time': 's'}
        super(Timer, self).__init__(name)
        
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