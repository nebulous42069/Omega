from urllib.parse import parse_qsl

class Params:
    def __init__(self, paramstring):
        self.params = dict(parse_qsl(paramstring))
        
    
    def get_params(self):
        return self.params
    
    def get_mode(self):
        try: return int(self.params['mode'])
        except KeyError: return None
        except TypeError: return None
