'''
Created on Mar 15, 2013

@package: ally core http
@copyright: 2011 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Gabriel Nistor

Provides the path support.
'''

from ally.api.operator.type import TypeModel, TypeProperty
from ally.container.ioc import injected
from ally.core.spec.transform import ITransfrom
from ally.design.processor.attribute import requires, defines
from ally.design.processor.context import Context
from ally.design.processor.handler import HandlerProcessor

# --------------------------------------------------------------------

class Node(Context):
    '''
    The node context.
    '''
    # ---------------------------------------------------------------- Required
    invokersGet = requires(dict)
    
class Invoker(Context):
    '''
    The invoker context.
    '''
    # ---------------------------------------------------------------- Required
    path = requires(list)
 
class Element(Context):
    '''
    The element context.
    '''
    # ---------------------------------------------------------------- Required
    node = requires(Context)
    property = requires(TypeProperty)

class Create(Context):
    '''
    The create item encoder context.
    '''
    # ---------------------------------------------------------------- Required
    encoder = requires(ITransfrom)
       
class Support(Context):
    '''
    The support context.
    '''
    # ---------------------------------------------------------------- Defined
    nodeValues = defines(dict, doc='''
    @rtype: dictionary{Context: object}
    The values used in constructing the paths indexed by corresponding node.
    ''')
    
# --------------------------------------------------------------------

@injected
class PathUpdaterSupportEncode(HandlerProcessor):
    '''
    Implementation for a handler that provides the models paths update when in a collection.
    '''
    
    def __init__(self):
        super().__init__(Invoker=Invoker, Element=Element, Support=Support)
        
    def process(self, chain, create:Create, node:Node, **keyargs):
        '''
        @see: HandlerProcessor.process
        
        Create the update model path encoder.
        '''
        assert isinstance(create, Create), 'Invalid create %s' % create
        assert isinstance(node, Node), 'Invalid node %s' % node
        
        if create.encoder is None: return 
        # There is no encoder to provide path update for.
        if not node.invokersGet: return
        # No get invokers to support.
        
        if isinstance(create.objType, TypeModel):
            assert isinstance(create.objType, TypeModel)
            properties = create.objType.properties.values()
        elif isinstance(create.objType, TypeProperty):
            properties = (create.objType,)
        else: return  # The type is not for a path updater, nothing to do, just move along
        assert isinstance(node.invokersGet, dict), 'Invalid get invokers %s' % node.invokersGet
        
        elements = []
        for prop in properties:
            invoker = node.invokersGet.get(prop)
            if not invoker: continue
            assert isinstance(invoker, Invoker), 'Invalid invoker %s' % invoker
            
            for el in reversed(invoker.path):
                assert isinstance(el, Element), 'Invalid element %s' % el
                if el.property == prop:
                    elements.append(el)
                    break
        
        if elements:
            create.encoder = EncoderPathUpdater(create.encoder, elements, isinstance(create.objType, TypeModel))
        
# --------------------------------------------------------------------

class EncoderPathUpdater(ITransfrom):
    '''
    Implementation for a @see: ITransfrom that updates the path before encoding .
    '''
    
    def __init__(self, encoder, elements, isModel):
        '''
        Construct the path updater.
        '''
        assert isinstance(encoder, ITransfrom), 'Invalid property encoder %s' % encoder
        assert isinstance(elements, list), 'Invalid elements %s' % elements
        assert isinstance(isModel, bool), 'Invalid is model flag %s' % isModel
        
        self.encoder = encoder
        self.elements = elements
        self.isModel = isModel
        
    def transform(self, value, target, support):
        '''
        @see: ITransfrom.transform
        '''
        assert isinstance(support, Support), 'Invalid support %s' % support
        if support.nodeValues is None: support.nodeValues = {}

        for el in self.elements:
            assert isinstance(el, Element), 'Invalid element %s' % el
            assert isinstance(el.property, TypeProperty), 'Invalid property %s' % el.property
            if self.isModel: support.nodeValues[el.node] = getattr(value, el.property.name)
            else: support.nodeValues[el.node] = value
        
        self.encoder.transform(value, target, support)
