"""LCM type definitions
This file automatically generated by lcm.
DO NOT MODIFY BY HAND!!!!
"""


from io import BytesIO
import struct

class handshake_t(object):

    __slots__ = ["pid"]

    __typenames__ = ["int32_t"]

    __dimensions__ = [None]

    def __init__(self):
        self.pid = 0
        """ LCM Type: int32_t """

    def encode(self):
        buf = BytesIO()
        buf.write(handshake_t._get_packed_fingerprint())
        self._encode_one(buf)
        return buf.getvalue()

    def _encode_one(self, buf):
        buf.write(struct.pack(">i", self.pid))

    @staticmethod
    def decode(data: bytes):
        if hasattr(data, 'read'):
            buf = data
        else:
            buf = BytesIO(data)
        if buf.read(8) != handshake_t._get_packed_fingerprint():
            raise ValueError("Decode error")
        return handshake_t._decode_one(buf)

    @staticmethod
    def _decode_one(buf):
        self = handshake_t()
        self.pid = struct.unpack(">i", buf.read(4))[0]
        return self

    @staticmethod
    def _get_hash_recursive(parents):
        if handshake_t in parents: return 0
        tmphash = (0xd21b643a13323c57) & 0xffffffffffffffff
        tmphash  = (((tmphash<<1)&0xffffffffffffffff) + (tmphash>>63)) & 0xffffffffffffffff
        return tmphash
    _packed_fingerprint = None

    @staticmethod
    def _get_packed_fingerprint():
        if handshake_t._packed_fingerprint is None:
            handshake_t._packed_fingerprint = struct.pack(">Q", handshake_t._get_hash_recursive([]))
        return handshake_t._packed_fingerprint

    def get_hash(self):
        """Get the LCM hash of the struct"""
        return struct.unpack(">Q", handshake_t._get_packed_fingerprint())[0]

