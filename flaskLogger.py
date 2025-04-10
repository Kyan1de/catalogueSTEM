import manyterm
import logging

# used as a "stream" in the handler
class ioOverride:
    def __init__(self, term: manyterm.Terminal):
        self.terminal = term
    def write(self, s):
        self.terminal.print(s)
    def flush(self): pass # unused, here so python doesnt complain
    def read(self): pass # unused, here so python doesnt complain

# the handler
class myStreamHandler(logging.StreamHandler):
    def __init__(self, *args, **kwargs):
        # opens the new terminal
        self.flaskTerm = manyterm.Terminal()
        super().__init__(ioOverride(self.flaskTerm), **kwargs)