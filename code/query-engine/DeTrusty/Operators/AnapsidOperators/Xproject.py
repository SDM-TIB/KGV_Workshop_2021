"""
Created on Jul 10, 2011

Implements the Xproject operator.
The intermediate results are represented in a queue.

@author: Maribel Acosta Deibe
"""

from multiprocessing import Queue
from DeTrusty.Wrapper.valWrapper.Mapping import Mapping


class Xproject(object):

    def __init__(self, vars):
        self.input = Queue()
        self.qresults = Queue()
        self.vars = vars

    def execute(self, left, dummy, out, processqueue=Queue()):
        # Executes the Xproject.
        self.left = left
        self.qresults = out
        tuple = self.left.get(True)
        while not (tuple == "EOF"):
            res = {}
            if len(self.vars) == 0:
                if not type(tuple) == Mapping:
                    self.qresults.put(dict(tuple))
                else:
                    self.qresults.put(tuple)
            else:
                if not isinstance(tuple, Mapping):
                    for var in self.vars:
                        var = var.name[1:]
                        aux = tuple.get(var, '')
                        res.update({var: aux})
                    self.qresults.put(res)
                else:
                    tuple = tuple.project(self.vars)
                    self.qresults.put(tuple)
            tuple = self.left.get(True)

        # Put EOF in queue and exit.
        self.qresults.put("EOF")
        return
