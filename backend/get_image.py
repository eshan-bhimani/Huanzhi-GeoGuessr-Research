import base64, re, requests, sys

state = requests.get("http://localhost:8000/environment/state").json()
data_url = state.get("image")
if not data_url:
    sys.exit("No image in state. Send a step first so image is set.")

m = re.match(r"data:(.*?);base64,(.*)", data_url)
if not m:
    sys.exit("Invalid image format in state.")
mime, b64 = m.groups()
with open("pano.jpg", "wb") as f:
    f.write(base64.b64decode(b64))
print("saved pano.jpg")