"""
Copy of https://github.com/ptone/Lumos/blob/master/lumos/packet.py

This module defines the packet structures sent over E1.31

Copyright (c) 2012 by Preston Holmes

Redistribution and use in source and binary forms of the software as well
as documentation, with or without modification, are permitted provided
that the following conditions are met:

* Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above
  copyright notice, this list of conditions and the following
  disclaimer in the documentation and/or other materials provided
  with the distribution.

* The names of the contributors may not be used to endorse or
  promote products derived from this software without specific
  prior written permission.

THIS SOFTWARE AND DOCUMENTATION IS PROVIDED BY THE COPYRIGHT HOLDERS AND
CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER
OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE AND DOCUMENTATION, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
DAMAGE.
"""

import struct
import uuid

default_cid = uuid.uuid1().bytes

def int_to_16bit(i):
    """
    return an int as a pair of bytes
    """
    return ((i >> 8) & 0xff, i & 0xff)

def length_as_low12(i):
    """
    return a length as 2 bytes, with the value being the low 12 bits
    """
    return(int_to_16bit(0x7000 | i))

class LayerBase(object):
    def length(self):
        return len(self.data)

class DMPLayer(LayerBase):
    def __init__(self, data):
        if len(data) > 512:
            raise ValueError("Max of 512 values")
        self.data = data

    def packet_data(self):
        packet = bytearray()
        # packet length
        packet.extend(length_as_low12(10 + 1 + len(self.data)))
        # vector
        packet.append(0x02)
        # address type & data type
        packet.append(0xa1)
        # startcode
        packet.extend('\x00\x00')
        # increment value
        packet.extend('\x00\x01')
        value_count = int_to_16bit(1 + len(self.data))
        packet.extend(value_count)
        # DMX 512 startcode
        packet.append('\x00')
        # DMX 512 data
        packet.extend(self.data)
        return packet

    def length(self):
        return 10 + 1 + len(self.data)

class FramingLayer(LayerBase):
    def __init__(self, dmp_packet=None, universe=1, name=None, priority=100, sequence=0):
        self.universe = universe
        name = name or 'lumos'
        self.name = name
        self.priority = priority
        self.sequence = sequence
        self.dmp_packet = dmp_packet

    def packet_data(self):
        packet = bytearray()
        packet.extend(length_as_low12(77 + len(self.dmp_packet)))
        # vector
        packet.extend('\x00\x00\x00\x02')
        packet.extend(struct.pack('!64s', self.name))
        packet.append(self.priority)
        # reserved by spec
        packet.extend('\x00\x00')
        packet.append(self.sequence)
        # options
        packet.append('\x00')
        # universe
        packet.extend(struct.pack('!h', self.universe))
        packet.extend(self.dmp_packet)
        return packet


class RootLayer(LayerBase):

    def __init__(self, cid=None, framing_packet=None):
        self.cid = cid or default_cid
        if len(self.cid) > 16:
            raise ValueError("CID too long")
        self.framing_packet = framing_packet

    def packet_data(self):
        packet = bytearray()
        packet.extend('\x00\x10\x00\x00')
        packet.extend('ASC-E1.17\x00\x00\x00')
        # pdu size starts after byte 16 - there are 38 bytes of data in root layer
        # so size is 38 - 16 + framing layer
        packet.extend(length_as_low12(38 - 16 + len(self.framing_packet)))
        # vector
        packet.extend('\x00\x00\x00\x04')
        packet.extend(self.cid)
        packet.extend(self.framing_packet)
        return packet


class E131Packet(object):
    def __init__(self, cid=None, name=None, universe=None, data=[], sequence=0):
        self.dmp_packet = DMPLayer(data=data).packet_data()
        self.framing_packet = FramingLayer(name=name, universe=universe,
                dmp_packet=self.dmp_packet, sequence=sequence).packet_data()
        self.packet_data = RootLayer(cid=cid, framing_packet=self.framing_packet).packet_data()

