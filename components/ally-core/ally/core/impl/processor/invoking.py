'''
Created on Jun 30, 2011

@package: ally core
@copyright: 2011 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Gabriel Nistor

Provides the invoking handler.
'''

from ally.api.config import GET, INSERT, UPDATE, DELETE
from ally.api.operator.type import TypeModelProperty, TypeOptionProperty
from ally.api.type import Input
from ally.core.spec.codes import INPUT_ERROR, INSERT_ERROR, INSERT_SUCCESS, \
    UPDATE_SUCCESS, UPDATE_ERROR, DELETE_SUCCESS, DELETE_ERROR, Coded
from ally.core.spec.resources import Invoker
from ally.core.spec.transform.render import Object, List, Value
from ally.design.processor.attribute import requires, defines
from ally.design.processor.context import Context
from ally.design.processor.handler import HandlerProcessor
from ally.exception import DevelError, InputError, Ref
import logging

# --------------------------------------------------------------------

log = logging.getLogger(__name__)

# --------------------------------------------------------------------

class Request(Context):
    '''
    The request context.
    '''
    # ---------------------------------------------------------------- Required
    invoker = requires(Invoker)
    arguments = requires(dict)

class Response(Coded):
    '''
    The response context.
    '''
    # ---------------------------------------------------------------- Defined
    errorDetails = defines(Object)
    obj = defines(object, doc='''
    @rtype: object
    The response object.
    ''')

# --------------------------------------------------------------------

class InvokingHandler(HandlerProcessor):
    '''
    Implementation for a processor that makes the actual call to the request method corresponding invoke. The invoking will
    use all the obtained arguments from the previous processors and perform specific actions based on the requested method.
    In GET case it will provide to the request the invoke returned object as to be rendered to the response, in DELETE case
    it will stop the execution chain and send as a response a success code.
    '''

    def __init__(self):
        '''
        Construct the handler.
        '''
        super().__init__()

        self.invokeCallBack = {
                               GET: self.afterGet,
                               INSERT: self.afterInsert,
                               UPDATE: self.afterUpdate,
                               DELETE: self.afterDelete
                               }

    def process(self, chain, request:Request, response:Response, **keyargs):
        '''
        @see: HandlerProcessor.process
        
        Invoke the request invoker.
        '''
        assert isinstance(request, Request), 'Invalid request %s' % request
        assert isinstance(response, Response), 'Invalid response %s' % response
        if response.isSuccess is False: return  # Skip in case the response is in error

        assert isinstance(request.invoker, Invoker), 'Invalid invoker %s' % request.invoker

        callBack = self.invokeCallBack.get(request.invoker.method)
        assert callBack is not None, \
        'Method cannot be processed for invoker \'%s\', something is wrong in the setups' % request.invoker.name
        assert isinstance(request.arguments, dict), 'Invalid arguments %s' % request.arguments

        args, keyargs = [], {}
        for inp in request.invoker.inputs:
            assert isinstance(inp, Input), 'Invalid input %s' % inp
            
            if inp.name in request.arguments:
                if isinstance(inp.type, TypeOptionProperty): keyargs[inp.name] = request.arguments[inp.name]
                else: args.append(request.arguments[inp.name])
            elif isinstance(inp.type, TypeOptionProperty):
                if inp.hasDefault: keyargs[inp.name] = inp.default
            elif inp.hasDefault: args.append(inp.default)
            else:
                raise DevelError('No value for mandatory input \'%s\' for invoker \'%s\'' % (inp.name, request.invoker.name))
        try:
            value = request.invoker.invoke(*args, **keyargs)
            assert log.debug('Successful on calling invoker \'%s\' with arguments %s and key arguments', request.invoker,
                             args, keyargs) or True

            callBack(request.invoker, value, response)
        except InputError as e:
            assert isinstance(e, InputError)
            INPUT_ERROR.set(response)
            response.errorDetails = self.processInputError(e)
            assert log.debug('User input exception: %s', e, exc_info=True) or True

    def processInputError(self, e):
        '''
        Process the input error into an error object.
        
        @return: Object
            The object containing the details of the input error.
        '''
        assert isinstance(e, InputError), 'Invalid input error %s' % e

        messages, names, models, properties = [], [], {}, {}
        for msg in e.message:
            assert isinstance(msg, Ref)
            if not msg.model:
                messages.append(Value('message', msg.message))
            elif not msg.property:
                messagesModel = models.get(msg.model)
                if not messagesModel: messagesModel = models[msg.model] = []
                messagesModel.append(Value('message', msg.message))
                if msg.model not in names: names.append(msg.model)
            else:
                propertiesModel = properties.get(msg.model)
                if not propertiesModel: propertiesModel = properties[msg.model] = []
                propertiesModel.append(Value(msg.property, msg.message))
                if msg.model not in names: names.append(msg.model)

        errors = []
        if messages: errors.append(List('error', *messages))
        for name in names:
            messagesModel, propertiesModel = models.get(name), properties.get(name)

            props = []
            if messagesModel: props.append(List('error', *messagesModel))
            if propertiesModel: props.extend(propertiesModel)

            errors.append(Object(name, *props))

        return Object('model', *errors)

    # ----------------------------------------------------------------

    def afterGet(self, invoker, value, response):
        '''
        Process the after get action on the value.
        
        @param invoker: Invoker
            The invoker used.
        @param value: object
            The value returned.
        @param response: Response
            The response to set the error if is the case.
        @return: boolean
            False if the invoking has failed, True for success.
        '''
        assert isinstance(invoker, Invoker), 'Invalid invoker %s' % invoker
        assert isinstance(response, Response), 'Invalid response %s' % response
        assert invoker.output.isValid(value), 'Invalid return value \'%s\' for invoker %s' % (value, invoker)
        
        response.obj = value

    def afterInsert(self, invoker, value, response):
        '''
        Process the after insert action on the value.
        
        @param invoker: Invoker
            The invoker used.
        @param value: object
            The value returned.
        @param response: Response
            The response to set the error if is the case.
        @return: boolean
            False if the invoking has failed, True for success.
        '''
        assert isinstance(invoker, Invoker), 'Invalid invoker %s' % invoker
        assert isinstance(response, Response), 'Invalid response %s' % response
        assert invoker.output.isValid(value), 'Invalid return value \'%s\' for invoker %s' % (value, invoker)

        if isinstance(invoker.output, TypeModelProperty) and \
        invoker.output.container.propertyId == invoker.output.property:
            if value is not None:
                response.obj = value
            else:
                INSERT_ERROR.set(response)
                assert log.debug('Cannot insert resource') or True
                return
        else:
            response.obj = value
        INSERT_SUCCESS.set(response)

    def afterUpdate(self, invoker, value, response):
        '''
        Process the after update action on the value.
        
        @param invoker: Invoker
            The invoker used.
        @param value: object
            The value returned.
        @param response: Response
            The response to set the error if is the case.
        @return: boolean
            False if the invoking has failed, True for success.
        '''
        assert isinstance(invoker, Invoker), 'Invalid invoker %s' % invoker
        assert isinstance(response, Response), 'Invalid response %s' % response
        assert invoker.output.isValid(value), 'Invalid return value \'%s\' for invoker %s' % (value, invoker)

        if invoker.output.isOf(None):
            UPDATE_SUCCESS.set(response)
            assert log.debug('Successful updated resource') or True
        elif invoker.output.isOf(bool):
            if value == True:
                UPDATE_SUCCESS.set(response)
                assert log.debug('Successful updated resource') or True
            else:
                UPDATE_ERROR.set(response)
                assert log.debug('Cannot update resource') or True
        else:
            # If an entity is returned than we will render that.
            UPDATE_SUCCESS.set(response)
            response.obj = value

    def afterDelete(self, invoker, value, response):
        '''
        Process the after delete action on the value.
        
        @param invoker: Invoker
            The invoker used.
        @param value: object
            The value returned.
        @param response: Response
            The response to set the error if is the case.
        @return: boolean
            False if the invoking has failed, True for success.
        '''
        assert isinstance(invoker, Invoker), 'Invalid invoker %s' % invoker
        assert isinstance(response, Response), 'Invalid response %s' % response
        assert invoker.output.isValid(value), 'Invalid return value \'%s\' for invoker %s' % (value, invoker)

        if invoker.output.isOf(bool):
            if value == True:
                DELETE_SUCCESS.set(response)
                assert log.debug('Successfully deleted resource') or True
            else:
                DELETE_ERROR.set(response)
                assert log.debug('Cannot deleted resource') or True
        else:
            # If an entity is returned than we will render that.
            DELETE_SUCCESS.set(response)
            response.obj = value
