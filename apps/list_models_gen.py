from google import genai
import os

client = genai.Client(api_key='AIzaSyAoUrcxIO07sTt-SY68jwzct0KuufN9Bbg')

for m in client.models.list():
    name = getattr(m, "name", None) or str(m)
    # Some SDK versions expose supported methods differently
    print(name)