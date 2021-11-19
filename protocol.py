from bitcoin.messages import *
import struct

PROTOVER = 70016

def version_pkt(server_ip, port, height):
    msg = msg_version()
    msg.nVersion = PROTOVER
    msg.addrTo.nServices = 0
    msg.addrTo.ip = server_ip
    msg.addrTo.port = port
    msg.addrFrom.ip = '0.0.0.0'
    msg.addrFrom.port = 0
    msg.nNonce = 0
    msg.addrFrom.nServices = 1033
    msg.nStartingHeight = height
    msg.strSubVer = b'/Satoshi:22.99.0/'
    # print(msg)

    return msg.to_bytes()

def getaddr_pkt():
    msg = msg_getaddr()

    return msg.to_bytes()

def verack_pkt():
    msg = msg_verack()

    return msg.to_bytes()

def pong_pkt(nonce):
    msg = msg_pong()
    msg.protover = PROTOVER
    msg.nonce = struct.unpack('<Q',nonce)[0]

    return msg.to_bytes()