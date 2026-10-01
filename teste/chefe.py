from maspy import *

class Funcionario(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)
        self.add(Goal("pedir_ferias"))
        
    @pl(gain, Goal("pedir_ferias"))
    def solicitar(self, src):
        self.print("Solicitando férias ao Gerente")
        self.send("Gerente", achieve, Goal("processar_pedido", "Ferias"))

    @pl(gain, Goal("resposta_recebida", Any))
    def finalizar(self, src, status):
        self.print(f"Resposta recebida do gerente: {status}")
        self.stop_cycle()

class Gerente(Agent):
    @pl(gain, Goal("processar_pedido", Any))
    def processar(self, src, pedido):
        self.print(f"Processando pedido de {pedido} do agente {src}")
        self.add(Belief("pedido", pedido))
        self.send(src, achieve, Goal("resposta_recebida", "Aprovado"))
        self.stop_cycle()

if __name__ == "__main__":
    Funcionario("Func")
    Gerente("Gerente")
    Admin().start_system()