from IPython import display
import pylab as pl
import time
import asyncio
import re
from multiprocessing import Pipe, Process

class LivePlotter(Process):
    '''
    Class for live plotting. Send new datapoints (based on pd.Dataframe) through a pipe to update the graph.
    Notes: Not executed in a process for now - need to figure out how to make output appear in the ipynb.
    '''
    def __init__(self, title, param_dict, pipe, timeout = 1):
        super(LivePlotter, self).__init__()
        self.title = title
        self.lines = []
        self.labels = None
        self.fig = None
        self.pipe = pipe
        self.daemon = True
        self.timeout = timeout
        units_dict = {key.name:param_dict[key] for key in param_dict}
        self.units_dict = units_dict
        
    def plot_loop(self):
        t = time.time()
        plot_created = False
        while True:
            if not self.pipe.poll(timeout=self.timeout):
                break
            else:
                # get the last value from the queue
                while self.pipe.poll():
                    msg = self.pipe.recv()
                    if msg is None:
                        self.update_plot(data)
                    data = msg
                t = time.time()
                if data is None:
                    break
                elif plot_created:
                    self.update_plot(data)
                else:
                    self.create_plot(data)
                    plot_created = True
        self.clear_output()
        return True

    def run(self):
        self.plot_loop()
    
    def add_line(self, x, y, *args):
        self.lines.append({'x': x, 'y': y, 'plotargs': args})
        if self.labels == None:
            xins, xparam = re.split('\.',x)
            yins, yparam = re.split('\.',y)
            self.labels = {'x': '%s (%s)' %(xparam, self.units_dict[xins][xparam]), 'y': '%s (%s)' %(yparam, self.units_dict[yins][xparam])}
    
    def create_plot(self, data):
        #print('create plot')
        self.fig = pl.figure()
        pl.title(self.title)
        for xname, yname, plotargs in [(line['x'],line['y'],line['plotargs']) for line in self.lines]:
            pl.plot(data[xname], data[yname], *plotargs)
        pl.xlabel(self.labels['x']), pl.ylabel(self.labels['y'])
        
    def update_plot(self, data):
        #print('update plot')
        loop = asyncio.get_event_loop()
        tasks = []
        for xname, yname, n in [(line['x'],line['y'],self.lines.index(line)) for line in self.lines]:
            tasks.append(asyncio.ensure_future(self.update_line(data, self.fig.axes[0], self.fig.axes[0].get_lines()[n], xname, yname)))
        loop.run_until_complete(asyncio.wait(tasks))
    
    @asyncio.coroutine
    def update_line(self, data, ax, hl, xname, yname):
        hl.set_xdata(data[xname])
        hl.set_ydata(data[yname])
        ax.relim()
        ax.autoscale()
        pl.plt.draw()
        display.clear_output(wait=True)
        display.display(pl.gcf())
    
    def clear_output(self):
        display.clear_output(wait=True)