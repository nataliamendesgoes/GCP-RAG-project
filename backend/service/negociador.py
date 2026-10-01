from maspy import *

from random import randint

class Initiator(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)
        self.add(Goal("iniciar_leilao"))
        self.add(Belief("estado", "verde"))  # Adicionado para garantir que o Iniciador tenha uma crença inicial

    @pl(gain, Goal("iniciar_leilao"))
    def iniciar_leilao(self, src, *args):
        self.print(f"Iniciador abrindo o leilão")
        self.send(ParticipanteA().my_name, achieve, Goal("fazer_proposta"))
        self.send(ParticipanteB().my_name, achieve, Goal("fazer_proposta"))

    @pl(gain, Belief("proposta_A", Any))
    def receber_proposta_A(self, src, valor, *args):
        self.print(f"Iniciador recebeu proposta A de {valor}")

    @pl(gain, Belief("proposta_B", Any))
    def receber_proposta_B(self, src, valor, *args):
        self.print(f"Iniciador recebeu proposta B de {valor}")

class ParticipanteA(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)
        self.add(Goal("fazer_proposta"))
        self.add(Belief("estado", "verde"))  # Adicionado para garantir que o Participante A tenha uma crença inicial

    @pl(gain, Goal("fazer_proposta"))
    def fazer_proposta(self, src, *args):
        valor = 100
        self.print(f"Participante A fazendo proposta de {valor}")
        self.send(src, tell, Belief("proposta_A", valor))
        self.stop_cycle()

class ParticipanteB(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)
        self.add(Goal("fazer_proposta"))
        self.add(Belief("estado", "verde"))  # Adicionado para garantir que o Participante B tenha uma crença inicial

    @pl(gain, Goal("fazer_proposta"))
    def fazer_proposta(self, src, *args):
        valor = 80
        self.print(f"Participante B fazendo proposa de {valor}")
        self.send(src, tell, Belief("proposta_B", valor))
        self.stop_cycle()

if __name__ == "__main__":
    Admin().console_settings(True)
    iniciador = Initiator("Initiator")
    participante_a = ParticipanteA("ParticipanteA")
    participante_b = ParticipanteB("ParticipanteB")

    canal = Channel()
    ##ambiente1 = Ambiente1()

    Admin().connect_to([iniciador, participante_a, participante_b], [Channel(), canal])

    iniciador.start_cycle()  # Iniciado o ciclo do Iniciador
    Admin().start_system()