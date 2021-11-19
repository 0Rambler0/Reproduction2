import time
from select import *
from socket import *
from io import BytesIO
from protocol import *
from net import *


#定义peer状态
INIT = 0
WAIT_VERSION = 1
WAIT_VERACK = 2
WAIT_ADDR = 3
RECONNECT = 4
COLLECT = 5
EXIT = 6

TIMEOUT = 0.15

class peer():
    def __init__(self, addr, port, type, sock_list, block_height, collect_node_flag, timeout, logger):
        self.addr = addr
        self.port = port
        self.addr_type = type
        self.logger = logger
        self.known_addr = None
        self.timeout = timeout
        self.block_height = block_height
        self.complete_flag = 0
        self.collect_flag = 0
        self.exit_flag = 0
        self.collect_node_flag = collect_node_flag
        self.peer_count = 0
        self.peer_list = []
        self.inv_list = []
        self.addr_msg_list = []
        self.connection_list = []
        self.reconnect_count = 0
        code = 0
        for sock in sock_list:
            self.connection_list.append({'code':code, 'sock':sock, 'state':INIT, 'state_time':time.time()})
            code += 1

    def get_msg(self, sock):
        start_time = time.time()
        epl = epoll()
        epl.register(sock.fileno(), EPOLLIN)
        event = epl.poll(timeout=TIMEOUT)
        if len(event) > 0:
            try:
                head = sock.recv(4+12+4+4)
            except Exception as e:
                epl.close()
                return ['error', e]
        else:
            head = 0
        if head:
            f = BytesIO(head)
            head_str = f.read(4+12+4+4)
            cmd = head[4:4+12].split(b"\x00", 1)[0]
            payload_len = int.from_bytes(head[16:16+4], byteorder='little', signed=False)
            event = epl.poll(timeout=TIMEOUT)
            if len(event) > 0:
                try:
                    payload = sock.recv(payload_len)
                except Exception as e:
                    epl.close()
                    return ['error', e]
                while len(payload) < payload_len:
                    event = epl.poll(timeout=TIMEOUT)
                    if len(event) > 0:
                        try:
                            temp = sock.recv(payload_len - len(payload))
                        except Exception as e:
                            epl.close()
                            return ['error', e]
                        payload += temp
                    if time.time() - start_time > 5:
                        return ['error', 'timeout']
                # print('报文长度字段%s,实际接收长度%s' %(payload_len, len(payload)))
                if len(payload) == 0:
                    payload = None
                msg = {'cmd':cmd, 'head':head, 'payload_len':payload_len, 'payload':payload}
            else:
                msg = None
        else:
            msg = None
        epl.close()

        return ['success', msg]
    
    def send_msg(self, sock, type, data=None):
        if type == 'version':
            msg = version_pkt(self.addr, self.port, self.block_height)
        elif type == 'verack':
            msg = verack_pkt()
        elif type == 'getaddr':
            msg = getaddr_pkt()
        elif type == 'pong':
            msg = pong_pkt(data)
        try:
            num = sock.send(msg)
        except Exception as e:
            # print('向%s发送%s消息失败，错误信息%s:' %(self.addr, type, e))
            self.logger.error('向%s发送%s消息失败，错误信息%s:' %(self.addr, type, e))
            sock.close()
            num = None
        
        return num
    
    def update_state(self):
        if len(self.connection_list) <= 0:
            self.exit_flag = 1
            return
        for connection in self.connection_list:
            if connection['state'] == INIT:
                num = self.send_msg(connection['sock'], 'version')
                if num == None:
                    connection['state'] = EXIT
                    # print('%s状态更新，新状态:%d' %(self.addr, self.state))
                    self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                    continue
                else:
                    connection['state'] = WAIT_VERSION
                    connection['state_time'] = time.time()
                    # print('%s状态更新，新状态:%d' %(self.addr, self.state))
                    self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
            elif connection['state'] == WAIT_VERSION:
                # print('%s状态持续时间：%f' %(self.addr, time.time() - self.state_time))
                if time.time() - connection['state_time'] > self.timeout:
                    # print('%s等待verison消息超时，连接失败' %(self.addr))
                    self.logger.error('%s的连接%d等待verison消息超时，连接失败' %(self.addr, connection['code']))
                    connection['state'] = EXIT
                    connection['state_time'] = time.time()
                    # print('%s状态更新，新状态:%d' %(self.addr, self.state))
                    self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                    continue

                msg = self.get_msg(connection['sock'])
                if msg[0] == 'error':
                    connection['state'] = EXIT
                    connection['state_time'] = time.time()
                    self.logger.error('%s的连接%d接收信息失败，错误信息%s' %(self.addr, connection['code'], msg[1]))
                    self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                    continue
                elif msg[1] == None:
                    # print('%s本轮未接收到消息' %(self.addr))
                    continue
                elif msg[1]['cmd'] == b'version':
                    num = self.send_msg(connection['sock'], 'verack')
                    if num == None:
                        connection['state'] = EXIT
                        connection['state_time'] = time.time()
                        # print('%s状态更新，新状态:%d' %(self.addr, self.state))
                        self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                        continue
                    connection['state'] = WAIT_VERACK
                    connection['state_time'] = time.time()
                    # print('%s状态更新，新状态:%d' %(self.addr, self.state))
                    self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                    continue
            elif connection['state'] == WAIT_VERACK:
                # print('%s状态持续时间：%f' %(self.addr, time.time() - self.state_time))
                if time.time() - connection['state_time'] > self.timeout:
                    # print('%s等待verack消息超时，连接失败' %(self.addr))
                    self.logger.error('%s的连接%d等待verack消息超时，连接失败' %(self.addr, connection['code']))
                    connection['state'] = EXIT
                    connection['state_time'] = time.time()
                    # print('%s状态更新，新状态:%d' %(self.addr, self.state))
                    self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                    continue
                msg = self.get_msg(connection['sock'])
                if msg[0] == 'error':
                    connection['state'] = EXIT
                    connection['state_time'] = time.time()
                    self.logger.error('%s的连接%d接收信息失败，错误信息:%s' %(self.addr, connection['code'], msg[1]))
                    self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                    continue
                if msg[1] == None:
                    # print('%s本轮未接收到消息' %(self.addr))
                    continue
                if msg[1]['cmd'] == b'verack':
                    if self.collect_node_flag:
                        connection['state'] = COLLECT
                        connection['state_time'] = time.time()
                    else:
                        num = self.send_msg(connection['sock'], 'getaddr')
                        if num == None:
                            connection['state'] = EXIT
                            connection['state_time'] = time.time()
                            self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                            continue
                        connection['state'] = WAIT_ADDR
                        connection['state_time'] = time.time()
                        # print('%s状态更新，新状态:%d' %(self.addr, self.state))
                        self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                    continue
            elif connection['state'] == WAIT_ADDR:
                # print('%s状态持续时间：%f' %(self.addr, time.time() - self.state_time))
                if time.time() - connection['state_time'] > self.timeout:
                    if self.peer_count == 0:
                        # print('%s未收到addr消息' %(self.addr))
                        self.logger.info('%s的连接%d未收到addr消息' %(self.addr, connection['code']))
                    connection['state'] = COLLECT
                    connection['state_time'] = time.time()
                    # print('%s状态更新，新状态:%d' %(self.addr, self.state))
                    self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                    continue
                msg = self.get_msg(connection['sock'])
                if msg[0] == 'error':
                    connection['state'] = EXIT
                    connection['state_time'] = time.time()
                    self.logger.error('%s的连接%d接收信息失败，错误信息:%s' %(self.addr, connection['code'], msg[1]))
                    self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                    continue
                i = 0
                while i < 3:
                    i += 1
                    if msg[1] == None:
                        # print('%s获取地址信息失败' %(self.addr))
                        continue
                    if msg[0] == 'error':
                        connection['state'] = EXIT
                        connection['state_time'] = time.time()
                        self.logger.error('%s的连接%d接收信息失败,错误信息:%s' %(self.addr, connection['code'], msg[1]))
                        self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                        break
                    if msg[1]['cmd'] == b'addr':
                        temp = processing_addr(msg[1]['payload'])
                        for addr in temp:
                            if addr not in self.peer_list:
                                self.peer_list.append(addr)
                        self.addr_msg_list.append({'time':time.time(), 'addr_list':temp})
                        self.peer_count = len(self.peer_list)
                        # print('\033[32m从%s共获得%d条地址信息\033[0m' %(self.addr, self.peer_count))
                        if self.peer_count == 1:
                            connection['state_time'] = time.time()
                        elif self.peer_count > 1:
                            connection['state'] = COLLECT
                            connection['state_time'] = time.time()
                            # print('%s状态更新，新状态:%d' %(self.addr, self.state))
                            self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                        continue
                    if msg[1]['cmd'] == 'ping':
                        num = self.send_msg(connection['sock'], type='pong', data=msg[1]['payload'])
                        if num == None:
                            connection['state'] = EXIT
                            connection['state_time'] = time.time()
                            self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                            continue
                    msg = self.get_msg(connection['sock'])
                    if msg[0] == 'error':
                        connection['state'] = EXIT
                        connection['state_time'] = time.time()
                        self.logger.error('%s的连接%d接收信息失败，错误信息:%s' %(self.addr, connection['code'], msg[1]))
                        self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                        continue
                self.logger.info('从%s的连接%d共获得%d条地址信息' %(self.addr, connection['code'], self.peer_count))
            elif connection['state'] == COLLECT:
                if self.collect_flag:
                    msg = self.get_msg(connection['sock'])
                    if msg[0] == 'error':
                        connection['state'] = RECONNECT
                        connection['state_time'] = time.time()
                        self.reconnect_count += 1
                        self.logger.error('%s的连接%d接收信息失败，错误信息:%s' %(self.addr, connection['code'], msg[1]))
                        self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                        continue
                    recv_time = time.time()
                    if msg[1] == None:
                        # print('%s本轮未接收到消息' %(self.addr))
                        continue
                    if msg[1]['cmd'] == b'inv':
                        addr = self.addr + ':' + str(self.port)
                        temp = processing_inv(msg[1]['payload'], recv_time, addr)
                        for inv in temp:
                            tx_hash = inv['hash']
                            flag = 1
                            for inv1 in self.inv_list:
                                if tx_hash == inv1['hash']:
                                    flag = 0
                            if flag:
                                self.inv_list.append(inv)
                        continue
                    if msg[1]['cmd'] == b'ping':
                        num = self.send_msg(connection['sock'], type='pong', data=msg[1]['payload'])
                        if num == None:
                            connection['state'] = RECONNECT
                            connection['state_time'] = time.time()
                            self.reconnect_count += 1
                            self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                            continue
                    if msg[1]['cmd'] == b'addr':
                        temp = processing_addr(msg[1]['payload'])
                        self.addr_msg_list.append({'time':time.time(), 'addr_list':temp})
                else:
                    msg = self.get_msg(connection['sock'])
                    if msg[0] == 'error':
                        connection['state'] = RECONNECT
                        connection['state_time'] = time.time()
                        self.reconnect_count += 1
                        self.logger.error('%s的连接%d接收信息失败，错误信息:%s' %(self.addr, connection['code'], msg[1]))
                        self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                        continue
                    if msg[1] == None:
                        continue
                    if msg[1]['cmd'] == 'ping':
                        num = self.send_msg(connection['sock'], type='pong', data=msg[1]['payload'])
                        if num == None:
                            connection['state'] = RECONNECT
                            connection['state_time'] = time.time()
                            self.reconnect_count += 1
                            self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
                    if msg[1]['cmd'] == b'addr':
                        temp = processing_addr(msg[1]['payload'])
                        self.addr_msg_list.append({'time':time.time(), 'addr_list':temp})
                    continue
            elif connection['state'] == EXIT:
                try:
                    connection['sock'].close()
                except:
                    pass
                if connection in self.connection_list:
                    self.connection_list.remove(connection)
                continue
            elif connection['state'] == RECONNECT:
                connection['sock'].close()
                if self.reconnect_count > 4:
                    connection['state'] = EXIT
                    connection['state_time'] = time.time()
                    continue
                connection['sock'] = connect_node(self.addr, self.port, self.addr_type, self.block_height, 0.5)
                if connection['sock'] == None:
                    connection['state'] = EXIT
                    connection['state_time'] = time.time()
                else:
                    connection['state'] = INIT
                    connection['state_time'] = time.time()
                continue
            elif connection['state'] > EXIT or connection['state'] < INIT:
                self.logger.error('%s的连接%d状态异常，当前状态为:%d' %(self.addr, connection['code'], connection['state']))
                connection['state'] = EXIT
                connection['state_time'] = time.time()
                self.logger.info('%s的连接%d状态更新，新状态:%d' %(self.addr, connection['code'] , connection['state']))
    
    def return_inv(self):
        temp_list = self.inv_list
        self.inv_list = []

        return temp_list
    
    def return_peer(self):
        for addr in self.peer_list:
            if addr['addr'] == self.addr:
                self.peer_list.remove(addr)
        temp = self.peer_list
        self.peer_list = []
        return temp
    
    def return_addr_msg(self):
        temp_list = self.addr_msg_list
        self.addr_msg_list = []

        return temp_list

    def start_collect(self):
        self.collect_flag = 1

    def check_complete(self):
        i = 0
        for connection in self.connection_list:
            if connection['state'] == COLLECT:
                i += 1
        if i == len(self.connection_list):
            return True
        else:
            return False