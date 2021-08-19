class Locker(sp.Contract):
    
    def __init__(self,nft_contract_address, admin_address):
        self.init(tokens = sp.map(),total_tokens = sp.nat(0),admin_address = admin_address,
        nft_contract = nft_contract_address)
        self.batch_transfer = Simple_batch_transfer()

    
    @sp.entry_point
    def deposit(self, address_from, contract_address, token_id):

        batch_type = self.batch_transfer.get_type()
        transfer_point = sp.contract(batch_type, self.data.nft_contract, entry_point = "transfer").open_some()
        data_to_send = [self.batch_transfer.item(from_ = sp.sender, txs = [ sp.record(to_ = self.address ,amount = 1,token_id = token_id)])]
            
        sp.transfer(data_to_send, sp.mutez(0), transfer_point)
        self.data.tokens[self.data.total_tokens] = sp.record(owner=sp.set_type_expr(address_from,sp.TAddress), 
                                        contract=sp.set_type_expr(contract_address,sp.TAddress),
                                        token_id=sp.set_type_expr(token_id,sp.TNat),
                                        status="deposited")
        self.data.total_tokens +=1
        self.lockToken(token_id)
        
        
    @sp.entry_point
    def lockToken(self, token_id):
        sp.verify(self.data.tokens.contains(token_id),message="Token not deposited")
        sp.verify(~ (self.data.tokens[token_id].status == "locked"),"Token already locked")
        sp.verify(sp.sender == self.data.tokens[token_id].owner,"Only owner can lock token")

        self.data.tokens[token_id].status = "locked"

    @sp.entry_point
    def unlockToken(self, token_id):
        sp.verify(self.data.tokens.contains(token_id),"Token not found") 
        sp.verify(sp.sender == self.data.tokens[token_id].owner, "Only owner can unlock")
        
        sp.verify(~ (self.data.tokens[token_id].status == "unlocked"),"Token already unlocked")

        self.data.tokens[token_id].status = "unlocked"

    @sp.entry_point
    def withdraw(self, token_id):
        sp.verify(self.data.tokens.contains(token_id),"Token not found") 
        sp.verify(sp.sender == self.data.tokens[token_id].owner,"Only owner can withdraw")
        sp.verify(self.data.tokens[token_id].status == "unlocked","Unlock token before withadraw")

        batch_type = self.batch_transfer.get_type()
        transfer_point = sp.contract(batch_type, self.data.nft_contract, entry_point = "transfer").open_some()

        data_to_send = [self.batch_transfer.item(from_ = self.address, txs = [ sp.record(to_ = sp.sender,amount = 1,token_id = token_id)])]
            
        sp.transfer(data_to_send, sp.mutez(0), transfer_point)
        del self.data.tokens[token_id]
        #self.data.total_tokens -= 1

    @sp.offchain_view
    def isLocked(self, token_id):
        sp.verify(self.data.tokens.contains(token_id),"Token not found") 
        sp.result(self.data.tokens[token_id].status == "unlocked")
