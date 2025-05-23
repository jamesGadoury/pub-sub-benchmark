"""LCM type definitions
This file automatically generated by lcm.
DO NOT MODIFY BY HAND!!!!
"""


from io import BytesIO
import struct

class bench_t(object):

    __slots__ = ["num_bytes", "blob", "creation_timestamp_ns"]

    __typenames__ = ["int32_t", "byte", "int64_t"]

    __dimensions__ = [None, ["num_bytes"], None]

    def __init__(self):
        self.num_bytes = 0
        """ LCM Type: int32_t """
        self.blob = b""
        """ LCM Type: byte[num_bytes] """
        self.creation_timestamp_ns = 0
        """ LCM Type: int64_t """

    def encode(self):
        buf = BytesIO()
        buf.write(bench_t._get_packed_fingerprint())
        self._encode_one(buf)
        return buf.getvalue()

    def _encode_one(self, buf):
        buf.write(struct.pack(">i", self.num_bytes))
        buf.write(bytearray(self.blob[:self.num_bytes]))
        buf.write(struct.pack(">q", self.creation_timestamp_ns))

    @staticmethod
    def decode(data: bytes):
        if hasattr(data, 'read'):
            buf = data
        else:
            buf = BytesIO(data)
        if buf.read(8) != bench_t._get_packed_fingerprint():
            raise ValueError("Decode error")
        return bench_t._decode_one(buf)

    @staticmethod
    def _decode_one(buf):
        self = bench_t()
        self.num_bytes = struct.unpack(">i", buf.read(4))[0]
        self.blob = buf.read(self.num_bytes)
        self.creation_timestamp_ns = struct.unpack(">q", buf.read(8))[0]
        return self

    @staticmethod
    def _get_hash_recursive(parents):
        if bench_t in parents: return 0
        tmphash = (0x3b788e96a62baede) & 0xffffffffffffffff
        tmphash  = (((tmphash<<1)&0xffffffffffffffff) + (tmphash>>63)) & 0xffffffffffffffff
        return tmphash
    _packed_fingerprint = None

    @staticmethod
    def _get_packed_fingerprint():
        if bench_t._packed_fingerprint is None:
            bench_t._packed_fingerprint = struct.pack(">Q", bench_t._get_hash_recursive([]))
        return bench_t._packed_fingerprint

    def get_hash(self):
        """Get the LCM hash of the struct"""
        return struct.unpack(">Q", bench_t._get_packed_fingerprint())[0]

