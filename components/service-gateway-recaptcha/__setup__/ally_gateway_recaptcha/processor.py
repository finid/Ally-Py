'''
Created on Jan 5, 2012

@package: gateway service reCAPTCHA
@copyright: 2012 Sourcefabric o.p.s.
@license http://www.gnu.org/licenses/gpl - 3.0.txt
@author: Gabriel Nistor

Provides the configurations for delivering files from the local file system.
'''

from ..ally_gateway.processor import assemblyGateway, \
    gatewayAuthorizedRepository, assemblyRESTRequest, updateAssemblyGateway, \
    cleanup_interval, gatewaySelector
from ally.container import ioc
from ally.container.error import ConfigError
from ally.design.processor.assembly import Assembly
from ally.design.processor.handler import Handler
from ally.gateway.http.impl.processor.captcha_validator import \
    GatewayCaptchaValidationHandler
from ally.gateway.http.impl.processor.repository_captcha import \
    GatewayCaptchaRepositoryHandler
from ally.http.impl.processor.forward import ForwardHTTPHandler

# --------------------------------------------------------------------

@ioc.config
def gateway_captcha_uri() -> str:
    ''' The gateway URI to fetch the Gateway objects from'''
    raise ConfigError('There is no gateway URI provided')

@ioc.config
def recaptcha_external_host() -> str:
    ''' The reCAPTCHA external host name, something like 'www.google.com' '''
    return 'www.google.com'

@ioc.config
def recaptcha_external_port():
    ''' The reCAPTCHA external server port'''
    return 80

@ioc.config
def recaptcha_service_uri() -> str:
    ''' The URI to use for validating the reCAPTCHA'''
    return 'recaptcha/api/verify'

@ioc.config
def recaptcha_private_key() -> str:
    ''' The reCAPTCHA private key'''
    return '6Ld6XOISAAAAAG10g88X_x5J0AJUGWZWK1HDvtsC'

# --------------------------------------------------------------------
# Creating the processors used in handling the request

@ioc.entity
def gatewayCaptchaRepository() -> Handler:
    b = GatewayCaptchaRepositoryHandler()
    b.uri = gateway_captcha_uri()
    b.cleanupInterval = cleanup_interval()
    b.assembly = assemblyRESTRequest()
    return b

@ioc.entity
def gatewayCaptchaValidation() -> Handler:
    b = GatewayCaptchaValidationHandler()
    b.assembly = assemblyReCaptchaForward()
    b.uriVerify = recaptcha_service_uri()
    b.privateKey = recaptcha_private_key()
    return b

@ioc.entity
def recaptchaForward() -> Handler:
    b = ForwardHTTPHandler()
    b.externalHost = recaptcha_external_host()
    b.externalPort = recaptcha_external_port()
    return b

# --------------------------------------------------------------------

@ioc.entity
def assemblyReCaptchaForward() -> Assembly:
    '''
    The assembly containing the handlers that will be used for forwarding the reCAPTCHA validation.
    '''
    return Assembly('reCAPTCHA forward')

# --------------------------------------------------------------------
    
@ioc.after(updateAssemblyGateway)
def updateAssemblyGatewayForCaptcha():
    assemblyGateway().add(gatewayCaptchaRepository(), after=gatewayAuthorizedRepository())
    assemblyGateway().add(gatewayCaptchaValidation(), after=gatewaySelector())

@ioc.after(assemblyReCaptchaForward)
def updateAssemblyReCaptchaForward():
    assemblyReCaptchaForward().add(recaptchaForward())
