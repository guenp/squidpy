import pandas as pd

def create_stamp():
    from datetime import datetime
    import time
    return datetime.fromtimestamp(time.time()).strftime('%Y%m%d_%H%M%S')

class Data(pd.DataFrame):
    '''
    Data class for storing & plotting data
    '''
    def __init__(self, title='', params=[]):
        super(Data, self).__init__()
        self.title = title
        self.stamp = create_stamp()
        self.params = params
    
    def add_dp(self, dp):
        df = self.append(dp, ignore_index = True)
        super(Data, self).__init__(df)
    
    def get_dp(self):
        return {key: getattr(self.params[key][0],self.params[key][1]) for key in self.params}
    
    def measure(self):
        dp = self.get_dp()
        self.add_dp(dp)
        