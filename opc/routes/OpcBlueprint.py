import logging

from flask import Blueprint, request

from services.OpcRequestService import OpcRequestService

opcBp = Blueprint('opcBp', __name__, url_prefix='/opc')

logger = logging.getLogger()

@opcBp.route('/connect', methods=['POST'])
def connect():
    OpcRequestService.handleConnectRequest(request)
    pass

@opcBp.route('/browse', methods=['GET'])
def browse():
    OpcRequestService.handleBrowseRequest(request)
    pass

@opcBp.route('/read', methods=['POST'])
def syncRead():
    OpcRequestService.handleSyncRead(request)
    pass

@opcBp.route('/write', methods=['POST'])
def syncWrite():
    OpcRequestService.handleSyncWrite(request)
    pass

@opcBp.route('/subscribe', methods=['POST'])
def subscribe():
    OpcRequestService.handleSubscribe(request)
    pass

@opcBp.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    OpcRequestService.handleUnsubscribe(request)
    pass

@opcBp.route('/status', methods=['GET'])
def status():
    OpcRequestService.getActiveClients(request)
    pass

@opcBp.route('/health', methods=['GET'])
def health():
    pass