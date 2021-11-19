import ipaddress
from socket import *
from utils import *


def processing_addr(raw):
    flag = 0
    addr_list = []
    if raw == None:
        return []
    count = raw[0]
    pointer = 1
    # print('count:%d' %(count))
    if count == 0xfd:
        count = int.from_bytes(raw[1:3], byteorder='little', signed=False)
        pointer += 2
    while count > 0:
        count = count - 1
        pointer += 12
        addr_raw = raw[pointer:pointer+16]
        # print(addr_raw)
        if int.from_bytes(addr_raw[0:10], byteorder='little', signed=False) == 0:
            if len(addr_raw[12:16]) > 0:
                addr = str(ipaddress.IPv4Address(addr_raw[12:16]))
                type = 'ipv4'
            else:
                continue
        else:
            addr = str(ipaddress.IPv6Address(addr_raw))
            type = 'ipv6'
        pointer += 16
        port = int.from_bytes(raw[pointer:pointer+2], byteorder='big', signed=False)
        addr_list.append({'addr':addr, 'port':port, 'type':type})
        pointer = pointer + 2

    return addr_list

def connect_node(addr, port, type, height, timeout):
    # print([addr, port, type])
    if type == 'ipv4':
        sock = socket(AF_INET, SOCK_STREAM)
    elif type == 'ipv6':
        sock = socket(AF_INET6, SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((addr, port))
        print('%sTCP连接成功' %addr)
    except Exception as e:
        if e.errno != 115:
            print("%sTCP连接无法建立，错误信息:%s" %(addr, e))
            sock.close()
            return None
 
    sock.setblocking(False)
    return sock

def get_transaction(raw):
    tx_list = []
    count = raw[0]
    pointer = 1
    while count > 0:
        inv_type = pointer
        pointer += 1
        if inv_type == 1 or inv_type == 5:
            tx_hash = raw[pointer:pointer+32]
            if inv_type == 1:
                type = 'txid'
            else:
                type = 'wtxid'
            tx_list.append({'hash':tx_hash, 'type':type})
        pointer += 32

    return tx_list

def processing_inv(raw, recv_time, addr):
    count = raw[0]
    inv_list =[]
    pointer = 1
    while count > 0:
        type = raw[pointer]
        pointer += 4
        if type == 1 or type == 5:
            inv_hash = raw[pointer:pointer+32]
            inv_hash = reversed_str(inv_hash.hex())
            if type == 1:
                inv_type = 'txid'
            else:
                inv_type = 'wtxid'
            inv_list.append({'hash':inv_hash, 'type':inv_type, 'time':recv_time, 'addr':addr})
            pointer += 32
        count += -1
    
    return inv_list

