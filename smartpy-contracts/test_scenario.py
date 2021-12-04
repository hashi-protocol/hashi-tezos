import smartpy as sp

# if on SmartPy IDE:
FA2 = sp.io.import_template("FA2.py")

#if on local
#import FA2

class burnableFA2(FA2.FA2):
    @sp.entry_point
    def burn(self, params):
        sp.verify(self.data.ledger.contains((sp.sender,params.token_id)), "Ledger does not own")
        sp.verify(self.data.ledger[(sp.sender,params.token_id)].balance == 1,"Not the owner")
        # We don't check for pauseness because we're the admin.
        if self.config.single_asset:
            sp.verify(params.token_id == 0, message = "single-asset: token-id <> 0")
        if self.config.non_fungible:
            sp.verify(
                 self.token_id_set.contains(self.data.all_tokens, params.token_id),
                message = "NFT-asset: token not found"
            )
        user = self.ledger_key.make(sp.sender, params.token_id)
        sp.verify(self.data.ledger.contains(user), message = "NFT Owner does not correspond")
        sp.verify(self.data.token_metadata.contains(params.token_id),message = "NFT metadata not found")
        
        del self.data.ledger[user]
        del self.data.token_metadata[params.token_id]

        self.data.token_metadata[params.token_id] = sp.record(
                token_id    = params.token_id,
                token_info  = sp.map(l = {"eth_owner" : params.eth_owner } ),
            )
        self.data.total_supply[params.token_id] = 0

    @sp.offchain_view()
    def isBurned(self, tok):
        if self.config.store_total_supply:
            sp.verify(self.data.token_metadata.contains(tok), "Token not found")
            sp.result(self.data.total_supply[tok] == sp.nat(0))
        else:
            sp.set_type(tok, sp.TNat)
            sp.result("total-supply not supported")

#imported from FA2 to facilitate transfers
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


@sp.add_test(name = "Tests")
def test():
    scenario = sp.test_scenario()
    admin = sp.test_account("Admin")
    mark = sp.test_account("Mark")
    alice = sp.test_account("Alice")
    bob = sp.test_account("Bob")

    scenario.h2("Initializing Wrapper, Locker and a random NFT Contract")
    wrapper = burnableFA2(FA2.FA2_config(single_asset=False,non_fungible=True, assume_consecutive_token_ids=False), admin = admin.address, metadata = sp.big_map({"": sp.utils.bytes_of_string("tezos-storage:content"),"content": sp.utils.bytes_of_string("""{"name" : "NFT Wrapper "}""")}))
    scenario += wrapper
    locker = Locker(wrapper.address, admin.address)
    scenario += locker
    NFTContract = FA2.FA2(FA2.FA2_config(single_asset=False,non_fungible=True, assume_consecutive_token_ids=False), admin = admin.address, metadata = sp.big_map({"": sp.utils.bytes_of_string("tezos-storage:content"),"content": sp.utils.bytes_of_string("""{"name" : "NFT Contract Collection "}""")}))
    scenario += NFTContract

    scenario.h2("#1 - Wrapped token scenario")
    scenario.p("This is in this call we need to check the NFT is locked on Ethereum")
    scenario += wrapper.mint(address = mark.address,
                                amount = 1,
                                metadata = sp.map(l = {
            "name" : sp.utils.bytes_of_string('Wrapped CatPunk #768'),
            "image": sp.utils.bytes_of_string('ifps://myurl.com'),
        }),
                                token_id = 0).run(sender = admin)

    scenario.h3("Mark can sell his NFT to Alice")
    scenario += wrapper.transfer(
        [
            wrapper.batch_transfer.item(from_ = mark.address,
                                txs = [
                                    sp.record(to_ = alice.address,
                                                amount = 1,
                                                token_id = 0)
                                ])
        ]).run(sender = mark)

    scenario.h3("Mark wants to get back his NFT on Ethereum")
    scenario.p("He can't since he's not the owner anymore")
    scenario += wrapper.burn(address = alice.address, token_id = 0, eth_owner = sp.utils.bytes_of_string('0xadresseth')).run(sender=mark,valid=False)

    scenario.h2("Alice wants to get back his NFT on Ethereum")
    scenario.p("She needs to burn her wrapped NFT first")
    scenario += wrapper.burn(address = alice.address, token_id = 0, eth_owner = sp.utils.bytes_of_string('0xadresseth')).run(sender=alice)

    scenario.h2("Alice tries to transfer a burned NFT - it fails")
    scenario += wrapper.transfer(
    [
        wrapper.batch_transfer.item(from_ = alice.address,
                            txs = [
                                sp.record(to_ = mark.address,
                                            amount = 1,
                                            token_id = 0)
                            ])
    ]).run(sender = alice,valid=False)

    scenario.h2("#2 - Ethereum Bridging Scenario")
    scenario.p("Bob has an NFT DogePunk #77 he wants to bridge. He needs to lock the NFT First")
    scenario += NFTContract.mint(address = bob.address,
                            amount = 1,
                            metadata = sp.map(l = {
        "name" : sp.utils.bytes_of_string('DogePunk #77'),
        "image": sp.utils.bytes_of_string('ifps://myurl.com'),
    }),
                            token_id = 77).run(sender = admin)

    scenario.h3("Bob needs to allow the locker as an Operator (FA2 only, allowance on FA1.2")
    scenario += NFTContract.update_operators([
        sp.variant("add_operator", NFTContract.operator_param.make(
            owner = bob.address,
            operator = locker.address,
            token_id = 77
        ))
    ]).run(sender = bob, valid = True)



    scenario.h3("Then Bob can deposit and lock his token")
    scenario += locker.deposit(sp.record(contract_address = NFTContract.address, 
                                    token_id = 77)).run(sender= bob)


    scenario.h3("New owner withdraws the NFT")
    scenario.p("Bob did transactions on Ethereum. The last owner is mark, who wants to withdraw the token")
    
    scenario += locker.update_owner(internal_token_id = 0, new_owner = mark.address).run(sender=admin)
    scenario += locker.unlockToken(0).run(sender=mark)
    scenario += locker.withdraw(0).run(sender=mark)

