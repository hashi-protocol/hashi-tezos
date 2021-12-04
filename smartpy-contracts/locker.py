import smartpy as sp

class Batch_transfer:
  
    def get_transfer_type(self):
        tx_type = sp.TRecord(to_ = sp.TAddress,
                             token_id = sp.TNat,
                             amount = sp.TNat)

        tx_type = tx_type.layout(
                ("to_", ("token_id", "amount"))
            )
        transfer_type = sp.TRecord(from_ = sp.TAddress,
                                   txs = sp.TList(tx_type)).layout(
                                       ("from_", "txs"))
        return transfer_type
    def get_type(self):
        return sp.TList(self.get_transfer_type())
    def item(self, from_, txs):
        v = sp.record(from_ = from_, txs = txs)
        return sp.set_type_expr(v, self.get_transfer_type())

class Locker(sp.Contract):
    
    def __init__(self,nft_contract_address, admin_address):
        self.init(tokens = sp.map(),total_tokens = sp.nat(0),admin_address = admin_address,
        nft_contract = nft_contract_address)
        self.batch_transfer = Batch_transfer()

    
    @sp.entry_point
    def deposit(self, contract_address, token_id):

        batch_type = self.batch_transfer.get_type()
        transfer_point = sp.contract(batch_type, contract_address, entry_point = "transfer").open_some()
        data_to_send = [self.batch_transfer.item(from_ = sp.sender, txs = [ sp.record(to_ = self.address ,amount = 1,token_id = token_id)])]
            
        sp.transfer(data_to_send, sp.mutez(0), transfer_point)
        self.data.tokens[self.data.total_tokens] = sp.record(owner=sp.set_type_expr(sp.sender,sp.TAddress), 
                                        contract=sp.set_type_expr(contract_address,sp.TAddress),
                                        token_id=sp.set_type_expr(token_id,sp.TNat),
                                        status="deposited")
        self.lockToken(self.data.total_tokens)
        self.data.total_tokens +=1
        
        
        
    @sp.entry_point
    def lockToken(self, internal_token_id):
        sp.verify(self.data.tokens.contains(internal_token_id),message="Token not deposited")
        sp.verify(~ (self.data.tokens[internal_token_id].status == "locked"),"Token already locked")
        sp.verify(sp.sender == self.data.tokens[internal_token_id].owner,"Only owner can lock token")

        self.data.tokens[internal_token_id].status = "locked"

    @sp.entry_point
    def unlockToken(self, internal_token_id):
        sp.verify(self.data.tokens.contains(internal_token_id),"Token not found") 
        sp.verify(sp.sender == self.data.tokens[internal_token_id].owner, "Only owner can unlock")
        sp.verify(~ (self.data.tokens[internal_token_id].status == "unlocked"),"Token already unlocked")

        self.data.tokens[internal_token_id].status = "unlocked"

    @sp.entry_point
    def withdraw(self, internal_token_id):
        sp.verify(self.data.tokens.contains(internal_token_id),"Token not found") 
        sp.verify(sp.sender == self.data.tokens[internal_token_id].owner,"Only owner can withdraw")
        sp.verify(self.data.tokens[internal_token_id].status == "unlocked","Unlock token before withadraw")

        batch_type = self.batch_transfer.get_type()
        transfer_point = sp.contract(batch_type, self.data.tokens[internal_token_id].contract, entry_point = "transfer").open_some()
        external_token_id = self.data.tokens[internal_token_id].token_id

        data_to_send = [self.batch_transfer.item(from_ = self.address, txs = [ sp.record(to_ = sp.sender,amount = 1,token_id = external_token_id)])]
            
        sp.transfer(data_to_send, sp.mutez(0), transfer_point)
        del self.data.tokens[internal_token_id]
        
    @sp.entry_point
    def update_owner(self, internal_token_id, new_owner):
        sp.verify(self.data.tokens.contains(internal_token_id),"Token not found") 
        sp.verify(self.data.tokens[internal_token_id].status == "locked","Only locked token owners can be modified")
        sp.verify(sp.sender == self.data.admin_address, "Only admin can change owner")

        self.data.tokens[internal_token_id].owner = new_owner

    @sp.offchain_view()
    def isLocked(self, internal_token_id):
        sp.verify(self.data.tokens.contains(internal_token_id),"Token not found") 
        sp.result(self.data.tokens[internal_token_id].status == "unlocked")