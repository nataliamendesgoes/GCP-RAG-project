from maspy import *
 
class Seller(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)
        self.add(Goal("sell"))
 
    @pl(gain, Goal("sell"))
    def offer(self, src):
        self.print("Oferecendo 42 ao Buyer")
        self.send("Buyer", tell, Belief("price", 42))
        self.stop_cycle()
 
class Buyer(Agent):
    @pl(gain, Belief("price", Any))
    def evaluate(self, src, price):
        if price < 50:
            self.print(f"Aceito o preço {price}")
            self.stop_cycle()
        else:
            self.send(src, achieve, Goal("sell"))
 
if __name__ == "__main__":
    seller, buyer = Seller("Seller"), Buyer("Buyer")
    Admin().start_system()