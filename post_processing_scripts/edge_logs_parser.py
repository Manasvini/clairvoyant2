import os

def _process_file(path, filename, delim):
    ret = []

    for line in open(path + "/" + filename, 'r').readlines():
        if delim not in line:
            continue

        line = line[line.find(delim) + len(delim)+1:-2]
        ret.append(line)

    return ret


def get_edge_number(edge_file_name):
    return int(edge_file_name[7:-5])


def parse_logs(path):
    ret = {}

    for filename in os.listdir(path):
        if "edge_go" not in filename or ".INFO" not in filename:
            continue

        print(f"pre-processing {filename}")

        lines = _process_file(path, filename, '[cache_event]')
        ret[filename] = lines

    return ret
    
            