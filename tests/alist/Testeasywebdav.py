import easywebdav
from urllib.parse import unquote

webdav = easywebdav.connect(host='192.168.31.186',port=5678, username='guest', password='guest_Api789',protocol='http',path='dav/')
files=webdav.ls("/每日更新/动漫/国漫/2023/完美世界")

result=[]
def search(keyword,path):
    files=webdav.ls(path)
    for f in (files):
        name=unquote(f.name[4:])
        print(name)
        if(name==path or name==(path+"/")):
            continue
        if(keyword in name):
            if(f.size>0):
                result.append(f)
            search(keyword,name)
        else:
         search(keyword,name)

    return 1

# for f in files:
#     print(f)
#     print(unquote(f.name))
search("完美世界","/每日更新/动漫/国漫/2023")
for f in result:
    print(f)
    print(unquote(f.name))
