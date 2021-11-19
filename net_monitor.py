from peer import *
import threading
from config import parallel_connection_count, tcp_timeout

class Connection_Manager(threading.Thread):
    def __init__(self, code, addr_list, block_height, node_list, node_type, timeout, logger):
        threading.Thread.__init__(self)
        self.code = code
        self.logger = logger
        self.node_list = node_list
        self.block_height = block_height
        self.addr_list = addr_list
        self.node_type = node_type
        self.timeout = timeout
        self.complete_flag = 0
        self.end_flag = 0
    def run(self):
        self.logger.info('%d号连接线程启动' %self.code)
        count = 0
        total = len(self.addr_list)
        for addr in self.addr_list:
            temp_sock_list = []
            count += 1
            if count%50 == 0:
                percent = (count/total)*100
                self.logger.info('%d号线程当前连接进度:%f%%' %(self.code, percent))
            for i in range(0, parallel_connection_count):
                temp_sock = connect_node(addr['addr'], addr['port'], addr['type'], self.block_height, tcp_timeout)
                if temp_sock == None:
                    continue
                else:
                    temp_sock_list.append(temp_sock)
            if len(temp_sock_list) > 0:
                new_node = peer(addr['addr'], addr['port'], addr['type'], temp_sock_list, self.block_height, self.node_type, self.timeout, self.logger)
                self.node_list.append(new_node)
                # print('与%s成功建立TCP连接' %(addr['addr']))
                self.logger.info('与%s成功建立%d条TCP连接' %(addr['addr'], len(temp_sock_list)))
            else:
                continue
        self.complete_flag = 1
        self.logger.info('%d号线程连接任务完成,线程退出' %self.code)

def create_net(addr_list, block_height, node_list, node_type, timeout, logger):
    thread_num = int(len(addr_list)/1000) + 1
    code = 0
    thread_list = []
    pointer = 0
    while code < thread_num:
        temp_list = []
        if len(addr_list) - pointer > 500:
            for i in range(0, 500):
                temp_list.append(addr_list[pointer])
                pointer += 1
        else:
            for i in range(0, len(addr_list) - pointer):
                temp_list.append(addr_list[pointer])
                pointer += 1
        connection_manager = Connection_Manager(code, temp_list, block_height, node_list, node_type, timeout, logger)
        connection_manager.start()
        thread_list.append(connection_manager)
        code += 1
    start_time = time.time()
    while 1:
        flag = 1
        for thread in thread_list:
            if thread.complete_flag == 0:
                flag = 0
        if flag == 0:
            time.sleep(0.5)
            continue
        logger.info("本轮TCP连接建立完毕")
        complete_count = 0
        for node in node_list:
            node.update_state()
            if node.exit_flag == 1:
                node_list.remove(node)
                continue
            if node.check_complete():
                complete_count += 1
        if complete_count == len(node_list):
            logger.info('当前所有节点均进入COLLECT态')
            break
        spent_time = time.time() - start_time
        if spent_time > 900:
            logger.error('等待节点连接完成超时，create net强制退出')
            break
        

def create_net1(node_list, addr_list, block_height, node_type, timeout, logger):
    count = 0
    total = len(addr_list)
    for addr in addr_list:
        temp_sock_list = []
        count += 1
        if count%50 == 0:
            percent = (count/total)*100
            logger.info('当前连接进度:%f%%' %(percent))
        for i in range(0, parallel_connection_count):
            temp_sock = connect_node(addr['addr'], addr['port'], addr['type'], block_height, 1.5)
            if temp_sock == None:
                continue
            else:
                temp_sock_list.append(temp_sock)
        if len(temp_sock_list) > 0:
            new_node = peer(addr['addr'], addr['port'], addr['type'], temp_sock_list, block_height, node_type, timeout, logger)
            node_list.append(new_node)
            # print('与%s成功建立TCP连接' %(addr['addr']))
            logger.info('与%s成功建立%d条TCP连接' %(addr['addr'], len(temp_sock_list)))
        else:
            continue
    while 1:
        start_time = time.time()
        complete_count = 0
        for node in node_list:
            node.update_state()
            if node.exit_flag == 1:
                node_list.remove(node)
                continue
            if node.check_complete():
                complete_count += 1
        if complete_count == len(node_list):
            logger.info("所有节点已进入COLLECT状态")
            break
        if time.time() - start_time > 1800:
            logger.error('等待节点连接完成超时，create net强制退出')
            break


def monitor(node_list, timeout):
    start_time = time.time()
    tx_list = []
    addr_msg_list = []
    for node in node_list:
        node.start_collect()
    while 1:
        # print('当前捕获交易数量:%d' %(len(tx_list)))
        now_time = time.time()
        if now_time - start_time > timeout:
            for node in node_list:
                tx_list += node.return_inv()
                msg = node.return_addr_msg()
                if len(msg) > 0:
                    addr_msg_list.append({'addr':node.addr, 'msg':msg})
            break
    
    return tx_list, addr_msg_list

class Peer_Manager(threading.Thread):
    def __init__(self, node_list, logger):
        threading.Thread.__init__(self)
        self.logger = logger
        self.node_list = node_list
        self.complete_flag = 0
        self.end_flag = 0
    
    def run(self):
        self.logger.info('Peer Manager启动')
        loop_count = 0
        start_time = time.time()
        while 1:
            loop_count += 1
            count = 0
            flag = 0
            if len(self.node_list) <= 0:
                continue
            for node in self.node_list:
                # print('当前节点:%s 状态:%d' %(node.addr, node.state))
                node.update_state()
                # print('update结束')
                if node.check_complete():
                    count += 1
                if node.exit_flag == 1:
                    self.node_list.remove(node)
                    continue
                if time.time() - start_time > 20:
                    self.logger.info('当前节点数量:%d' %(len(self.node_list)))
                    start_time = time.time()
            if count == len(self.node_list):
                self.complete_flag = 1
            if self.end_flag == 1:
                for node in self.node_list:
                    for connection in node.connection_list:
                        connection['state'] = EXIT
                    node.update_state()
                self.logger.info('peer_manager退出')
                return
