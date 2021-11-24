from netaddr.ip import IPAddress

def reversed_list_to_str(list):
    list.reverse()
    str = ''
    for i in list:
        str += i
    return str

def reversed_str(str):
    count = 0
    list = []
    while count < len(str):
        list.append(str[count:count+2])
        count += 2
    # print(list)
    new_str = reversed_list_to_str(list)

    return new_str

def isIP4or6(cfgstr):
    ipFlg = False
 
    if '/' in cfgstr:
        text = cfgstr[:cfgstr.rfind('/')]
    else:
        text = cfgstr
     
    try:
        addr = IPAddress(text)
        ipFlg = True
    except:
        ipFlg = False
 
    if ipFlg == True:
        return addr.version
    else:
        return False