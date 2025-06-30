import snap7

class Plc:
    def __init__(self):
        self.client = None

    def init_plc(self):
        try:
            self.client = snap7.client.Client()
            self.client.connect("192.168.100.83", 0, 1)  # IP, rack, slot
            if self.client.get_connected():
                print("Conexão com o PLC estabelecida com sucesso!")
                return True
            else:
                print("Falha ao conectar ao PLC.")
                return False
        except Exception as e:
            print(f"Erro ao conectar ao PLC: {e}")
            return False

    @staticmethod
    def int_to_bytearray(number: int) -> bytearray:
        # Convert the integer to bytes
        byte_representation = number.to_bytes(4, byteorder='big', signed=False)

        # Convert the bytes to a bytearray
        return bytearray(byte_representation)

    def write_db(self, value: int) -> None:
        data = self.int_to_bytearray(value)
        self.client.db_write(1, 0, data)
