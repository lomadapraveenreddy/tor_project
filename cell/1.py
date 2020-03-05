import struct
import sys
string='a234'
print(string.encode())
string=string.encode()
print(type(string))
string=string.decode()
print(string)