from maspy import *
from random import randint
 
class Seller(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)
        self.add(Goal("start_negotiation"))
 
    @pl(gain, Goal("start_negotiation"))
    def start(self, src):
        price = randint(30, 70)
        self.print(f"Offering item for {price}")
        self.send("Buyer", achieve, Goal("Buy", price))
 
    @pl(gain, Belief("Accept", Any))
    def accepted(self, src, price):
        self.print(f"Offer of {price} accepted by {src}")
        self.stop_cycle()
 
    @pl(gain, Belief("Reject", Any))
    def rejected(self, src, price):
        self.print(f"Offer of {price} rejected by {src}")
        self.stop_cycle()
 
class Buyer(Agent):
    @pl(gain, Goal("Buy", Any))
    def buy_product(self, src, price):
        self.print(f"Evaluating offer of {price}")
        if price < 50:
            self.print(f"Accepting price {price}")
            self.send(src, tell, Belief("Accept", price))
        else:
            self.print(f"Rejecting price {price}")
            self.send(src, tell, Belief("Reject", price))
        self.stop_cycle()
 
if __name__ == "__main__":
    Seller()
    Buyer()
    Admin().start_system()