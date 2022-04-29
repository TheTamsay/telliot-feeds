from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Optional

import requests
from requests import JSONDecodeError
from requests.adapters import HTTPAdapter
from telliot_core.datasource import DataSource
from telliot_core.dtypes.datapoint import DataPoint
from urllib3.util import Retry
from web3 import Web3

from telliot_feed_examples.utils.cfg import mainnet_config
from telliot_feed_examples.utils.log import get_logger

logger = get_logger(__name__)


cfg = mainnet_config()
cfg.get_endpoint().connect()
w3 = cfg.get_endpoint().web3


@dataclass
class TellorRNGManualSource(DataSource[Any]):
    """DataSource for TellorRNG manually-entered timestamp."""

    timestamp = 0

    def parse_user_val(self) -> int:
        """Parse timestamp from user input."""
        print("Enter timestamp for generating a random number: ")

        data = None
        while data is None:
            inpt = input()

            try:
                inpt = int(inpt)  # type: ignore
            except ValueError:
                print("Invalid input. Enter decimal value (int).")
                continue

            print(
                "Generating random number from timestamp: "
                f"{inpt}\nPress [ENTER] to confirm."
            )
            _ = input()
            data = inpt

        self.timestamp = data
        return data

    def block_num_from_timestamp(self, timestamp: int) -> Optional[int]:
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)

        with requests.Session() as s:
            s.mount("https://", adapter)
            try:
                rsp = s.get(
                    "https://api.etherscan.io/api"
                    "?module=block"
                    "&action=getblocknobytime"
                    f"&timestamp={timestamp}"
                    "&closest=after"
                    "&apikey="
                )
                if rsp is None:
                    logger.error("No response from Etherscan API")
                    return None
                try:
                    this_block = rsp.json()
                except JSONDecodeError as e:
                    logger.error("Etherscan API returned invalid JSON:", e.strerror)
                    return None
                if this_block["status"] != "1":
                    logger.error(
                        f"Etherscan API returned error: {this_block['message']}"
                    )
                    return None

                return int(this_block["result"])
            except requests.exceptions.RequestException as e:
                logger.error(f"Etherscan API error: {e}")
                return None

    def getEthHashByTimestamp(self, timestamp: int) -> Optional[str]:
        """Fetches next Ethereum blockhash after timestamp from API."""

        try:
            this_block = w3.eth.get_block("latest")
        except Exception as e:
            logger.error(f"Unable to retrieve latest block: {e}")
            return None

        if this_block["timestamp"] < timestamp:
            logger.error(
                f"Timestamp {timestamp} is older than current "
                "block timestamp {this_block['timestamp']}"
            )
            return None

        block_num = self.block_num_from_timestamp(timestamp)

        block = w3.eth.get_block(block_num)
        if block is None:
            return None
        if "hash" not in block:
            return None
        try:
            blockhash_hex_str = str(block["hash"].hex())
        except Exception as e:
            logger.error(
                f"Tellor RNG V1 ethereum API returned an invalid block hash: {e}"
            )
            return None

        return blockhash_hex_str

    def getBtcHashByTimestamp(self, timestamp: int) -> Optional[str]:
        """Fetches next Bitcoin blockhash after timestamp from API."""

        with requests.Session() as s:
            try:
                rsp = s.get(f"https://blockchain.info/blocks/{timestamp}?format=json")
                blocks = rsp.json()
                print(blocks)
                return blocks["blocks"][0]["hash"]
                # rsp = s.get("https://blockchain.info/latestblock")
                # if rsp is None:
                #     logger.error("Tellor RNG V1 no latest btc block returned from API")
                #     return None
                # try:
                #     this_block = rsp.json()
                # except JSONDecodeError as e:
                #     logger.error(
                #         "Tellor RNG V1 source returned invalid JSON:", e.strerror
                #     )
                #     return None
                # if this_block["time"] < timestamp:
                #     logger.error(
                #         f"Tellor RNG V1 current btc block time, {this_block['time']}"
                #         + f"is less than given timestamp {timestamp}"
                #     )
                #     return None
                

                # else:
                #     min_num: int = 723976
                #     max_num: int = this_block["height"]
                #     mid_num: int = 0
                #     while max_num - min_num > 1:
                #         mid_num = round((max_num + min_num) / 2)
                #         rsp = s.get(f"https://blockchain.info/rawblock/{mid_num}")
                #         try:
                #             this_block = rsp.json()
                #         except JSONDecodeError as e:
                #             logger.error(
                #                 "Tellor RNG V1 source returned invalid JSON:",
                #                 e.strerror,
                #             )
                #             return None
                #         if this_block is None:
                #             return None
                #         if this_block["time"] > timestamp:
                #             max_num = mid_num
                #         else:
                #             min_num = mid_num
                #     rsp = s.get(f"https://blockchain.info/rawblock/{max_num}")
                #     try:
                #         this_block = rsp.json()
                #     except JSONDecodeError as e:
                #         logger.error(
                #             "Tellor RNG V1 source returned invalid JSON:", e.strerror
                #         )
                #         return None
                #     if this_block is None:
                #         return None
                #     return str(this_block["hash"])
            except requests.exceptions.RequestException as e:
                logger.error(f"Tellor RNG V1 bitcoin API error: {e}")
                return ""

    async def fetch_new_datapoint(self) -> DataPoint[bytes]:
        """Update current value with time-stamped value fetched from user input.

        Returns:
            Current time-stamped value
        """

        if self.timestamp == 0:
            timestamp = self.parse_user_val()
        else:
            timestamp = self.timestamp
        eth_hash = self.getEthHashByTimestamp(timestamp)
        btc_hash = self.getBtcHashByTimestamp(timestamp)

        if eth_hash is None:
            logger.warning("No response from TellorRNG V1 Ethereum API")
            return None, None
        if btc_hash is None:
            logger.warning("No response from TellorRNG V1 Bitcoin API")
            return None, None

        data = Web3.solidityKeccak(["string", "string"], [eth_hash, btc_hash])
        dt = datetime.fromtimestamp(self.timestamp, tz=timezone.utc)
        datapoint = (data, dt)

        self.store_datapoint(datapoint)

        logger.info(f"Stored random number for timestamp {timestamp}: {data}")

        return datapoint
