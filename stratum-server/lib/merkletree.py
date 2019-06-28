from Crypto.Hash import SHA256

class MerkleTree:
    def __init__(self, data):
        self.data = data

    def calculate_merkle_root(self, extranonce):
        L = self.data
        tx_root = SHA256.new(L[0] + L[1]).digest()
        metapackage_hash = SHA256.new(L[2] + extranonce.to_bytes(8, byteorder='big')).digest()
        return SHA256.new(metapackage_hash + tx_root).digest()[:16]