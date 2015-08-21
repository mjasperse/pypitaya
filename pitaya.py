import socket, select
import numpy as np

### MAKE SURE SCPI-SERVER IS RUNNING ON THE PITAYA!!

class PitayaSCPI:
	def __init__(self, ipaddr, port=5000, timeout=1, querytime=1e-3, buffer=1024):
		self._querytime = querytime
		self._buffer = buffer
		# create the socket
		self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
		self._sock.settimeout(timeout)
		# connect to the unit
		self._sock.connect((ipaddr,port))	# times out unless SCPI server is running
		
	def _send(self, s):
		# send the string following by CRLF
		self._sock.send(s+"\r\n")
		# check to see if there's any instant reply (corresponding to an error)
		[rl,wl,xl] = select.select([self._sock],[],[],self._querytime)
		# return TRUE if reply is waiting
		return len(rl) > 0
		
	def query(self, query):
		# send the query string
		self._send(query)
		# we expect a reply to the query, so keep waiting until it's done
		resp = ""
		while not resp.endswith("\r\n"):
			# make sure we don't get an error message
			msg = self._sock.recv(self._buffer)
			if msg == "ERR!":
				raise RuntimeError("Invalid command "+repr(query))
			# accumulate packets
			resp = resp + msg
		# return the response, less the whitespace
		return resp[:-2]

	def cmd(self, cmd):
		# send the command
		if not self._send(cmd):
			# no immediate response, which is expected
			return None
		# if there was a response, it must be an error
		msg = self._sock.recv(self._buffer)
		assert msg == "ERR!", "Unknown reply"
		# raise an error that the command failed
		raise RuntimeError("Invalid command "+repr(cmd))
		
	def get_channel(self, channel):
		# validate input
		assert channel in [1,2]
		# perform query
		q = self.query("ACQ:SOUR%d:DATA?"%channel)
		# check response
		assert q[0] == '{' and q[-1] == '}'
		# parse string
		return np.fromstring(q[1:-1], sep=',')
		
	def get_data(self):
		# download both channels -- NB: may not work because WPOS moves on inbetween
		# print ">>", self.query("ACQ:WPOS?")
		ch1 = self.get_channel(1)
		# print ">>", self.query("ACQ:WPOS?")
		ch2 = self.get_channel(2)
		assert len(ch1) == len(ch2)
		# query sample rate and offset
		fs = float(self.query("ACQ:SRA:HZ?"))
		t0 = float(p.query("ACQ:TRIG:DLY?")) - len(ch1)/2.0
		# make time array
		t = (np.arange(len(ch1))+t0) / fs
		# convert to big array
		return np.vstack([t,ch1,ch2]).T
