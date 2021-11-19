from config import *
from net_monitor import *
from dns import resolver
import logging
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import os
import csv
import requests
from lxml import etree
import json

if __name__=='__main__':
    #配置日志记录器
    logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s  %(levelname)s  %(funcName)s   %(message)s')
    logger = logging.getLogger('my_logger')
    logger.setLevel(logging.DEBUG)
    filename = time.asctime(time.localtime(time.time())) + '.log'
    fh = logging.FileHandler(log_path + filename) #日志储存在当前目录的log文件夹下
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter(fmt='%(asctime)s  %(levelname)s  %(funcName)s   %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    #从dns种子获取初始节点列表
    addr_list = [] #储存探针已知的节点地址信息
    if net_name == 'testnet':
        seed_list = test_seed_list
        remote_port = 18333
    elif net_name == 'mainnet':
        seed_list = main_seed_list
        remote_port = 8333
    for seed in seed_list:
        temp_list = resolver.resolve(seed)
        for addr in temp_list:
            if str(addr) not in addr_list:
                addr_list.append({'addr':str(addr), 'port':remote_port, 'type':'ipv4'})
    print('初始连接节点列表:')
    i = 1
    for addr in addr_list:
        logger.info('地址%d:%s' %(i, addr))
        i += 1
    #搭建监测网络
    if net_name == 'testnet':
        bitcoind = AuthServiceProxy("http://%s:%s@127.0.0.1:%d"%(rpc_user, rpc_passwd, rpc_port)) #连接bitcoin core
        block_height = bitcoind.getblockcount() #获取当前区块高度信息
    elif net_name == 'mainnet':
        while 1:
            b_re = requests.get('https://chain.api.btc.com/v3/block/latest')
            if b_re.status_code == 200:
                break
            time.sleep(0.1)
        block_height = b_re.json()['data']['height']
    logger.info('开始第一层连接')
    node_list = [] #储存每个peer的信息
    peer_manager = Peer_Manager(node_list, logger)
    peer_manager.start()
    create_net1(node_list, addr_list, block_height, 0, 30, logger)
    i = 0
    while i < connect_depth-1:
        temp = [] #暂存新接收到的节点地址
        i += 1
        count = 0
        for node in node_list:
            count += 1
            if count%50 == 0:
                logger.info('当前地址处理进度：%f%%' %(count/len(node_list)*100))
            temp1 = node.return_peer()
            for addr in temp1:
                if addr not in temp:
                    if addr not in addr_list:
                        temp.append(addr)
        logger.info('开始第%d层连接' %(i+1))
        create_net(temp, block_height, node_list, 0, (i+2)*30, logger)
        for addr in temp:
            if addr not in addr_list:
                addr_list.append(addr)
    # 开始收集inv消息
    addr_msg_list = [] #储存从各节点接收到的addr消息内容
    tx_list = [] #储存tx hash信息
    logger.info('开始进行信息收集')
    tx_list, addr_msg_list = monitor(node_list, collect_time)
    for tx in tx_list:
        logger.info(tx)
    for  addr in addr_msg_list:
        logger.info(addr)
    # 将捕捉的数据储存为csv文件
    path = data_log_path + time.asctime(time.localtime(time.time()))
    if not os.path.exists(path):
        os.mkdir(path)
    addr_header = ['node_ip', 'addr', 'port', 'timestamp']
    csvFile = open(path + "/addr_msg.csv", "w", newline='')
    writer = csv.writer(csvFile)
    writer.writerow(addr_header)
    for data in addr_msg_list:
        node_ip = data['addr']
        for msg in data['msg']:
            timestamp = msg['time']
            for addr in msg['addr_list']:
                writer.writerow([node_ip, addr['addr'], addr['port'], timestamp])
    csvFile.close()
    csvFile = open(path + "/tx_hash.csv", "w", newline='')
    tx_header = ['txid', 'addr', 'timestamp']
    writer = csv.writer(csvFile)
    writer.writerow(tx_header)
    for tx in tx_list:
        writer.writerow([tx['hash'], tx['addr'], tx['time']])
    csvFile.close()
    peer_manager.end_flag = 1

        

