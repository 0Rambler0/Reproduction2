# bitcoind rpc用户名和密码, testnet的区块高度获取需要借助bitcoind，必须在本地运行bitcoind并配置该参数，mainnet可以忽略
rpc_user = "test"
rpc_passwd = "123456"
rpc_port = 18332 # mainnet为8332，testnet为18332
# bitcoin  dns种子列表
test_seed_list = ['testnet-seed.bitcoin.jonasschnelli.ch',
             'seed.tbtc.petertodd.org',
             'seed.testnet.bitcoin.sprovoost.nl',
             'testnet-seed.bluematt.me']

main_seed_list = ['seed.bitcoin.sipa.be.',
                  'dnsseed.bluematt.me.',
                  'dnsseed.bitcoin.dashjr.org.',
                  'seed.bitcoinstats.com.',
                  'seed.bitcoin.jonasschnelli.ch.',
                  'seed.btc.petertodd.org.',
                  'seed.bitcoin.sprovoost.nl.',
                  'dnsseed.emzy.de.',
                  'seed.bitcoin.wiz.biz.']
# 程序日志的存放路径
log_path = '/root/Reproduction/Reproduction2/log/'
# 收集的数据的存放路径
data_log_path = '/root/Reproduction/Reproduction2/data/'
# 节点连接层数
connect_depth = 5
# 数据收集定时器
collect_time = 3600
# 每个节点的并行连接数
parallel_connection_count = 5
# TCP连接的超时时间
tcp_timeout = 1.5
# BTC网络
net_name = 'mainnet'
