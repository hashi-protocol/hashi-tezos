# :hammer_and_wrench: EXPERIMENTAL VERSION :hammer_and_wrench:
Tezos smart contracts of the Hashi protocol. 
The oracle part has not been implemented yet. Thereforce, this code is a Proof of Concept but is far from final protocol.


## burnableFA2 (Wrapper) Contract
This contract is the Tezos wrapper contract of the protocol. Basically, it is a FA2 Contract with a *burn* entrypoint, and a *isBurned* view.

 - `burn`: Take a params record with *token_id* (sp.TNat) and *eth_owner* (sp.TString, designing the new Eth Owner)
 - `isBurned`: An offchain view that returns if a token is burned, takes *token_id* (sp.TNat) as parameter.

## Locker Contract
This contract implements the locking protocol of Hashi.

 - `deposit` : Deposit and lock a token in the contract. Params: *contract_address* the NFT Contract on Tezos (sp.TAddress) and *token_id* , the NFT Token id on this contract (sp.TNAt)
 - `unlockToken`: Change a status of a locked NFT from "locked" to "unlocked". Requisite to withdraw. Take a *internal_token_id* (sp.TNat) as parameter.
 - `withdraw`: Get back a token that has been bridged on Ethereum, after unlocking it. Take a *internal_token_id* (sp.TNat) as parameter.
 - `isLocked`: An offchain view to check if a token is locked. Necessary to check it before minting the wrapped token on Ethereum. Take a *internal_token_id* (sp.TNat) as parameter.

