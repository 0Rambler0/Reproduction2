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