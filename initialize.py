#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2018-09-17 14:32:32
# @Author  : giantbranch (giantbranch@gmail.com)
# @Link    : http://www.giantbranch.cn/
# @tags : 

from config import *
import os
import sys
import uuid
import json

def getChallList():
    challlist = []
    for challname in os.listdir(PWN_BIN_PATH):
        if not os.path.isfile(PWN_BIN_PATH + "/" + challname + "/" + challname) or\
                not os.path.isfile(PWN_BIN_PATH + "/" + challname + "/" + "libc_" + challname + ".so") or \
                not os.path.isfile(PWN_BIN_PATH + "/" + challname + "/" + "ld_" + challname + ".so"):
            sys.stderr.write("Error: Can't find binary, libc or ld for " + challname + "!\n")
            sys.exit(1)
        challlist.append(challname)
    challlist.sort()
    return challlist

def isExistBeforeGetFlagAndPort(challname, contentBefore):
    challname_tmp = ""
    tmp_dict = ""
    ret = False
    for line in contentBefore:
        tmp_dict = json.loads(line)
        challname_tmp = tmp_dict["challname"]
        if challname == challname_tmp:
            ret = [tmp_dict["flag"], tmp_dict["port"]]
    return ret

def generateFlags(challlist):
    tmp_flag = ""
    contentBefore = []
    if not os.path.exists(FLAG_BAK_FILENAME):
        os.popen("touch " + FLAG_BAK_FILENAME)

    with open(FLAG_BAK_FILENAME, 'r') as f:
        while 1:
            line = f.readline()
            if not line:
                break
            contentBefore.append(line)
    # bin's num != flags.txt's linenum, empty the flags.txt
    if len(challlist) != len(contentBefore):
        os.popen("echo '' > " + FLAG_BAK_FILENAME)
        contentBefore = []
    port = PORT_LISTEN_START_FROM + len(contentBefore)
    flags = []
    with open(FLAG_BAK_FILENAME, 'w') as f:
        for challname in challlist:
            flag_dict = {}
            ret = isExistBeforeGetFlagAndPort(challname, contentBefore)
            if ret == False:
                tmp_flag = "flag{" + str(uuid.uuid4()) + "}"
                flag_dict["port"] = port
                port = port + 1
            else:
                tmp_flag = ret[0]
                flag_dict["port"] = ret[1]

            flag_dict["challname"] = challname
            flag_dict["flag"] = tmp_flag
            flag_json = json.dumps(flag_dict)
            print flag_json
            f.write(flag_json + "\n")
            flags.append(tmp_flag)
    return flags

def generateXinetd(challlist):
    contentBefore = []
    with open(FLAG_BAK_FILENAME, 'r') as f:
        while 1:
            line = f.readline()
            if not line:
                break
            contentBefore.append(line)
    conf = ""
    uid = 1000
    for challname in challlist:
        port = isExistBeforeGetFlagAndPort(challname, contentBefore)[1]
        conf += XINETD % (port, str(uid) + ":" + str(uid), challname, challname)
        uid = uid + 1
    with open(XINETD_CONF_FILENAME, 'w') as f:
            f.write(conf)

def generateDockerfile(challlist, flags):
    conf = ""
    # useradd and put flag
    runcmd = "RUN "
    
    for challname in challlist:
        runcmd += "useradd -m " + challname + " && "
   
    for x in xrange(0, len(challlist)):
        if x == len(challlist) - 1:
            runcmd += "echo '" + flags[x] + "' > /home/" + challlist[x] + "/flag.txt" 
        else:
            runcmd += "echo '" + flags[x] + "' > /home/" + challlist[x] + "/flag.txt" + " && "
    # print runcmd 

    # copy all files which name contains `challname`
    copybin = ""
    for challname in challlist:
        copybin += "COPY " + PWN_BIN_PATH + "/" + challname + "/*" + " /home/" + challname + "/" + "\n"
        if REPLACE_BINSH:
            copybin += "COPY ./catflag" + " /home/" + challname + "/bin/sh\n"
        else:
            copybin += "COPY ./catflag" + " /home/" + challname + "/bin/sh\n"

    # print copybin

    # chown & chmod
    chown_chmod = "RUN "
    for x in xrange(0, len(challlist)):
        chown_chmod += "chown -R root:" + challlist[x] + " /home/" + challlist[x] + " && "
        chown_chmod += "chmod -R 750 /home/" + challlist[x] + " && "
        if x == len(challlist) - 1:
            chown_chmod += "chmod 740 /home/" + challlist[x] + "/flag.txt"
        else:
            chown_chmod += "chmod 740 /home/" + challlist[x] + "/flag.txt" + " && "
    # print chown_chmod

    # copy lib,/bin 
    # dev = '''mkdir /home/%s/dev && mknod /home/%s/dev/null c 1 3 && mknod /home/%s/dev/zero c 1 5 && mknod /home/%s/dev/random c 1 8 && mknod /home/%s/dev/urandom c 1 9 && chmod 666 /home/%s/dev/* && '''
    dev = '''mkdir /home/%s/dev && mknod /home/%s/dev/null c 1 3 && mknod /home/%s/dev/zero c 1 5 && mknod /home/%s/dev/random c 1 8 && mknod /home/%s/dev/urandom c 1 9 && chmod 666 /home/%s/dev/* '''
    if not REPLACE_BINSH:
        # ness_bin = '''mkdir /home/%s/bin && cp /bin/sh /home/%s/bin && cp /bin/ls /home/%s/bin && cp /bin/cat /home/%s/bin'''
        ness_bin = '''&& cp /bin/sh /home/%s/bin && cp /bin/ls /home/%s/bin && cp /bin/cat /home/%s/bin'''
    copy_lib_bin_dev = "RUN "
    for x in xrange(0, len(challlist)):
        copy_lib_bin_dev += "cp -R /lib* /home/" + challlist[x]  + " && "
        copy_lib_bin_dev += "cp -R /usr/lib* /home/" + challlist[x]  + " && "
        copy_lib_bin_dev += dev % (challlist[x], challlist[x], challlist[x], challlist[x], challlist[x], challlist[x])
        if x == len(challlist) - 1:
            if not REPLACE_BINSH:
                copy_lib_bin_dev += ness_bin % (challlist[x], challlist[x], challlist[x])
            pass                
        else: 
            if not REPLACE_BINSH:   
                copy_lib_bin_dev += ness_bin % (challlist[x], challlist[x], challlist[x]) + " && "
            else:
                copy_lib_bin_dev += " && "

    # print copy_lib_bin_dev

    conf = DOCKERFILE % (runcmd, copybin, chown_chmod, copy_lib_bin_dev)

    with open("Dockerfile", 'w') as f:
        f.write(conf)

def generateDockerCompose(length):
    conf = ""
    ports = ""
    port = PORT_LISTEN_START_FROM
    for x in xrange(0,length):
        ports += "- " + str(port) + ":" + str(port) + "\n    "
        port = port + 1

    conf = DOCKERCOMPOSE % ports
    # print conf
    with open("docker-compose.yml", 'w') as f:
        f.write(conf)

# def generateBinPort(challlist):
#     port = PORT_LISTEN_START_FROM
#     tmp = ""
#     for challname in challlist:
#         tmp += challname  + "'s port: " + str(port) + "\n"
#         port = port + 1
#     print tmp
#     with open(PORT_INFO_FILENAME, 'w') as f:
#         f.write(tmp)
    
challlist = getChallList()
flags = generateFlags(challlist)
# generateBinPort(challlist)
generateXinetd(challlist)
generateDockerfile(challlist, flags)
generateDockerCompose(len(challlist))



