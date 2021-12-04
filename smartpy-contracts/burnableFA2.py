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