import numpy, time

class Instrument():
    def __init__(self):
        self.name = ''
        self.gpib_address = ''
        
    def _repr_html_(self):
        html = [self.__doc__]
        html.append("<table width=100%>")
        for key in vars(self).keys():
            if key[0] == '_':
                html.append("<tr>")
                html.append("<td>{0}</td>".format(key[1:]))
                html.append("<td>{0}</td>".format(getattr(self,key[1:])))
                html.append("</tr>")
        html.append("</table>")
        return ''.join(html)
    
class Timer():
    def __init__(self):
        self.tstart = 0
        self.name = 'time'
    def get(self):
        if self.tstart==0:
            self.tstart = time.time()
        return time.time()-self.tstart
    def reset(self,tstart=0):
        self.tstart=tstart
    def set(self, *args):
        None

class Mock(Instrument):
    '''
    Mock instrument for testing squidpy
    '''
    def __init__(self):
        super(Mock, self).__init__()
        self.timer = Timer()
        self._voltage = 10
        self._time = 0
        self._wave = self.wave
        
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