from maspy import *
from random import choice
 
class Sala(Environment):
    def __init__(self, env_name):
        super().__init__(env_name)
        if choice([True, False]):
            self.create(Percept("temperatura", "frio"))
        else:
            self.create(Percept("temperatura", "quente"))
 
    def ligar_aquecedor(self, src):
        self.print(f"Agente {src} ligou o aquecedor e fechou a janela")
 
class Termostato(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)
        self.add(Goal("regular_temperatura"))
 
    @pl(gain, Goal("regular_temperatura"), Belief("temperatura", Any, "T1"))
    def regular(self, src, status):
        if status == "frio":
            self.print("Ambiente frio, fechando a janela e ligando aquecedor")
            self.ligar_aquecedor()
            self.stop_cycle()
        else:
            self.print("Ambiente nao esta frio")
            self.stop_cycle()
 
if __name__ == "__main__":
    sala = Sala("T1")
    termostato = Termostato("Termostato")
    Admin().connect_to([termostato], sala)
    Admin().start_system()