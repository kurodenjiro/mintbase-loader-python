from mintbase import (
    MintbaseDocumentLoader,
    BlockchainType,
)

contractAddress = "nft.yearofchef.near"  # Year of chef contract address

blockchainType = BlockchainType.NEAR_MAINNET  # default value, optional parameter

blockchainLoader = MintbaseDocumentLoader(
    contract_address=contractAddress, blockchainType=blockchainType,api_key="omni-site"
)

nfts = blockchainLoader.load()

print(nfts[:2])
