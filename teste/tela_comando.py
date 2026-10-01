from maspy import *
 
class AgentA(Agent):
    @pl(gain, Goal("start_exchange", Any))
    def start(self, src, msg):
        self.print(f"Sending {msg} to AgentB")
        self.send("AgentB", achieve, Goal("receive_msg", msg))
        self.stop_cycle()
 
class AgentB(Agent):
    @pl(gain, Goal("receive_msg", Any))
    def receive(self, src, msg):
        self.print(f"Received: {msg} from {src}")
        self.stop_cycle()
 
if __name__ == "__main__":
    AgentA(goals=Goal("start_exchange", "Ping"))
    AgentB("AgentB")
    Admin().start_system()