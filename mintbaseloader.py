import os
import re
import time
from enum import Enum
from typing import List, Optional

import requests
import json
from langchain_core.documents import Document

from langchain_community.document_loaders.base import BaseLoader


class BlockchainType(Enum):
    """Enumerator of the supported blockchains."""

    NEAR_MAINNET = "mainnet"
    NEAR_TESTNET = "testnet"


class MintbaseDocumentLoader(BaseLoader):
    """Load elements from a blockchain smart contract.

    The supported blockchains are: Near mainnet, Near testnet.

    If no BlockchainType is specified, the default is Near mainnet.

    The Loader uses the Mintbase API to interact with the blockchain.
    MB_API_KEY environment variable must be set to use this loader.

    The API returns 100 NFTs per request and can be paginated using the
    startToken parameter.

    If get_all_tokens is set to True, the loader will get all tokens
    on the contract.  Note that for contracts with a large number of tokens,
    this may take a long time (e.g. 10k tokens is 100 requests).
    Default value is false for this reason.

    The max_execution_time (sec) can be set to limit the execution time
    of the loader.

    Future versions of this loader can:
        - Support additional Mintbase APIs (e.g. getTransactions, etc.)
    """

    def __init__(
        self,
        contract_address: str,
        blockchainType: BlockchainType = BlockchainType.NEAR_MAINNET,
        api_key: str = "",
        startToken: str = "",
        get_all_tokens: bool = False,
        max_execution_time: Optional[int] = None,
    ):
        """

        Args:
            contract_address: The address of the smart contract.
            blockchainType: The blockchain type.
            api_key: The Mintbase API key.
            startToken: The start token for pagination.
            get_all_tokens: Whether to get all tokens on the contract.
            max_execution_time: The maximum execution time (sec).
        """
        self.contract_address = contract_address
        self.blockchainType = blockchainType.value
        self.api_key = os.environ.get("MB_API_KEY") or api_key
        self.startToken = startToken
        self.get_all_tokens = get_all_tokens
        self.max_execution_time = max_execution_time

        if not self.api_key:
            raise ValueError("Mintbase API key not provided.")

        if not re.match(r"^(([a-z\d]+[\-_])*[a-z\d]+\.)*([a-z\d]+[\-_])*[a-z\d]+$", self.contract_address):
            raise ValueError(f"Invalid contract address {self.contract_address}")

    def load(self) -> List[Document]:
        result = []

        current_start_token = self.startToken

        start_time = time.time()

        while True:
            # Define the GraphQL query as a multi-line string
            operations_doc = """
            query MyQuery {
            mb_views_nft_tokens(where: {nft_contract_id: {_eq: "contract_address"}}) {
                base_uri
                burned_receipt_id
                burned_timestamp
                copies
                description
                expires_at
                extra
                issued_at
                last_transfer_receipt_id
                last_transfer_timestamp
                media
                media_hash
                metadata_content_flag
                metadata_id
                mint_memo
                minted_receipt_id
                minted_timestamp
                minter
                nft_contract_content_flag
                nft_contract_created_at
                nft_contract_icon
                nft_contract_id
                nft_contract_is_mintbase
                nft_contract_name
                nft_contract_owner_id
                nft_contract_reference
                nft_contract_spec
                nft_contract_symbol
                owner
                reference
                reference_blob
                reference_hash
                royalties
                royalties_percent
                splits
                starts_at
                title
                token_id
                updated_at
            }
            }
            """

            # Replace the placeholder with the actual contract address
            contract_address = "contract_address"  # Replace with your actual contract address
            operations_doc = operations_doc.replace("contract_address", self.contract_address)

            # Define the headers
            headers = {
                "mb-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            # Define the POST data
            data = {
                "query": operations_doc,
                "variables": {},
                "operationName": "MyQuery"
            }

            url = (
                f"https://graph.mintbase.xyz/{self.blockchainType}"
            )
            
            response = requests.post(url, headers=headers, data=json.dumps(data))

            if response.status_code != 200:
                raise ValueError(
                    f"Request failed with status code {response.status_code}"
                )

            items = response.json()["data"]["mb_views_nft_tokens"]

            

            if not items:
                break

            for item in items:
                
                content = str(item)
                tokenId = item["token_id"]
                metadata = {
                    "source": self.contract_address,
                    "blockchain": self.blockchainType,
                    "tokenId": tokenId,
                }
                result.append(Document(page_content=content, metadata=metadata))

            # exit after the first API call if get_all_tokens is False
            if not self.get_all_tokens:
                break

            # get the start token for the next API call from the last item in array
            current_start_token = result[-1].metadata["tokenId"]

            if (
                self.max_execution_time is not None
                and (time.time() - start_time) > self.max_execution_time
            ):
                raise RuntimeError("Execution time exceeded the allowed time limit.")

        if not result:
            raise ValueError(
                f"No NFTs found for contract address {self.contract_address}"
            )

        return result

