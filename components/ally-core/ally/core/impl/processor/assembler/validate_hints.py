'''
Created on Jun 5, 2013

@package: ally core
@copyright: 2011 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Gabriel Nistor

Provides the validation for call and model hints.
'''

from ally.api.operator.type import TypeModel
from ally.api.type import Call
from ally.design.processor.attribute import requires
from ally.design.processor.context import Context
from ally.design.processor.handler import HandlerProcessor
from ally.support.util_sys import locationStack
from collections import Callable

# --------------------------------------------------------------------

class Register(Context):
    '''
    The register context.
    '''
    # ---------------------------------------------------------------- Required
    suggest = requires(Callable)
    invokers = requires(list)
    relations = requires(dict)
    hintsCall = requires(dict)
    hintsModel = requires(dict)
    
class Invoker(Context):
    '''
    The invoker context.
    '''
    # ---------------------------------------------------------------- Required
    call = requires(Call)
    location = requires(str)
    
# --------------------------------------------------------------------

class ValidateHintsHandler(HandlerProcessor):
    '''
    Implementation for a processor that provides the validation for call and model hints.
    '''
    
    def __init__(self):
        super().__init__(Invoker=Invoker)

    def process(self, chain, register:Register, **keyargs):
        '''
        @see: HandlerProcessor.process
        
        Process the hints.
        '''
        assert isinstance(register, Register), 'Invalid register %s' % register
        assert callable(register.suggest), 'Invalid suggest %s' % register.suggest
        
        reported = set()
        if register.invokers:
            if register.hintsCall is None: hintsCall = {}
            else: hintsCall = register.hintsCall

            present = False
            for invoker in register.invokers:
                assert isinstance(invoker, Invoker), 'Invalid invoker %s' % invoker
                if not invoker.call: continue
                assert isinstance(invoker.call, Call), 'Invalid call %s' % invoker.call
                
                unknown = []
                for hname in invoker.call.hints:
                    if hname not in hintsCall: unknown.append('\'%s\'' % hname)
                if unknown:
                    if invoker.location not in reported:
                        register.suggest('Unknown hints %s, at:%s', ', '.join(unknown), invoker.location)
                        reported.add(invoker.location)
                    present = True
            
            if present:
                available = []
                for hname in sorted(hintsCall):
                    available.append('\t%s: %s' % (hname, hintsCall[hname]))
                register.suggest('The available call hints are:\n%s', '\n'.join(available))
        
        if register.relations:
            if register.hintsModel is None: hintsModel = {}
            else: hintsModel = register.hintsModel 

            present = False
            for model in register.relations:
                assert isinstance(model, TypeModel), 'Invalid model %s' % model
                
                unknown = []
                for hname in model.hints:
                    if hname not in hintsModel: unknown.append('\'%s\'' % hname)
                if unknown:
                    location = locationStack(model.clazz)
                    if location not in reported:
                        register.suggest('Unknown hints %s, at:%s', ', '.join(unknown), location)
                        reported.add(location)
                    present = True
            
            if present:
                available = []
                for hname in sorted(hintsModel):
                    available.append('\t%s: %s' % (hname, hintsModel[hname]))
                register.suggest('The available model hints are:\n%s', '\n'.join(available))
                
