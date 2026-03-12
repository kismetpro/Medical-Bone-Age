import urllib.request,uuid,json 
boundary='----WebKitFormBoundary'+uuid.uuid4().hex 
body=[] 
def add_field(n,v): 
   body.append(f'--{boundary}\r\nContent-Disposition: form-data; name=\"{n}\"\r\n\r\n{v}\r\n'.encode()) 
add_field('gender','male') 
img=bytes.fromhex('ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c19120f131d1a1f1e1d1a1c1c2024273029221c1e2d232c2e2f2f1f273334332d342a2e2fffda0008010100003f00f7fa28a2803ffd9') 
body.append(f'--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"t.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n'.encode()+img+b'\r\n') 
data=b''.join(body)+f'--{boundary}--\r\n'.encode() 
req=urllib.request.Request('http://127.0.0.1:8000/predict',data=data,method='POST') 
req.add_header('Content-Type',f'multipart/form-data; boundary={boundary}') 
try: 
   with urllib.request.urlopen(req,timeout=90) as r: print('状态',r.status); print(r.read()[:500]) 
except urllib.error.HTTPError as e: print('网络错误',e.code); print(e.read()[:800]) 
except Exception as e: print('错误',e) 
