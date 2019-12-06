import json
from typing import List
from connection.node import Node
from connection.skt import Skt
from cell.cell import Cell, CreateCellPayload, CreatedCellPayload, ExtendCellPayload
from cell.control_cell import TapSHData, TapCHData, LinkSpecifier
from crypto.core_crypto import CoreCryptoRSA, CoreCryptoDH


class Circuit:
	"""
	The class representing the Circuit object for the Onion Proxy.
	"""

	@staticmethod
	def get_rand_circ_id() -> int:
		"""
		Returns a random circId for the circuit. Follows the Tor Spec to create the circId section 5.1.1
		:return: circId --> integer
		"""
		return 1

	def __init__(self, node_container: List[Node], skt: Skt, circ_id: int):
		"""
		Constructor
		:param circ_id: The circuit Id for the given circuit
		:param node_container: The list of Node objects including the Client itself
		:param skt: The Client's socket object. We will use this to connect to the nodes in the container
		"""
		self.circ_id = circ_id
		self.node_container = node_container
		self.skt = skt
		self.session_key01 = None
		self.session_key02 = None
		self.session_key03 = None

	def open_connection(self, hop_i: int) -> int:
		"""

		:param hop_i: The index of the node in the node container that the client wants to connect to
		:return: Returns a status code. 0 --> Success and -1 means error
		"""
		err_code = self.skt.client_connect(self.node_container[hop_i].host, self.node_container[hop_i].port)
		if err_code == 0:
			return 0
		else:
			return -1

	def create_circuit_hop1(self) -> int:
		"""
		The function to setup circuit with the first hop in the circuit. Creates the CREATE/CREATE2 cell and sends it
		down the socket. It assumes that the open_connection was called on the first node and the socket is connected
		to the first node
		:return: Returns a status code. 0 --> Success DH Handshake and -1 --> Means error in processing the cell or the DH Handshake.
		On error it closes the socket to node 1
		"""
		# First create a CREATE2 Cell.

		# Making the create_cell
		create_cell = Cell()
		x, gx = create_cell.build_create_cell('TAP', 3, self.circ_id, self.node_container[1].onion_key_pub)

		# Sending a JSON String down the socket
		self.skt.client_send_data(create_cell.net_serialize())

		# Get the created cell in response and convert it to python Cell Object
		created_cell = Cell.net_deserialize(str(self.skt.client_recv_data()), [CreatedCellPayload.deserialize, TapSHData.deserialize])

		# The cell is correctly structured
		if created_cell.CIRCID == self.circ_id and created_cell.CMD == Cell.CMD_ENUM['CREATED2']:
			created_h_data = created_cell.PAYLOAD.HDATA
			gy = created_h_data.GY
			gxy = CoreCryptoDH.compute_dh_shared_key(gy, x)
			if created_h_data.KH == CoreCryptoRSA.kdf_tor(gxy):
				print("Handshake successful!")
				self.session_key01 = gxy
				return 0
			else:
				self.skt.close()
				return -1
		else:
			self.skt.close()
			return -1

	def extend_circuit_hop_i(self, i) -> int:
		"""
		The function to setup circuit with the ith hop in the circuit. Creates the EXTEND/EXTEND2 cell and sends it
		down the socket.
		:return: Returns a status code. 0 --> Success DH Handshake and -1 --> Means error in processing the cell or the DH Handshake.
		"""
		# First create a EXTEND2 Cell.

		extend_cell = Cell()
		x, gx = extend_cell.build_extend_cell('TAP', 3, self.circ_id, self.node_container[i].onion_key_pub, self.node_container[i].host, self.node_container[i].port, 1, 'IPv4')

		# Sending a JSON String down the socket
		self.skt.client_send_data(extend_cell.net_serialize())

		return 0
