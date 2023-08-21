from webdav3.client import Client
options = {
 'webdav_hostname': "http://192.168.31.186:5678/dav/",
 'webdav_login':    "guest",
 'webdav_password': "guest_Api789"
}
client = Client(options)

# if client.check('/'):
#     print('连接成功！')
# else:
#     print('连接失败。')

files=client.list('/')
# files=client.search('完美世界')
for f in files:
    try:
        client.list(f)
    except Exception as e:
        print(e)
    print(f)
# print(files)
print("1111")