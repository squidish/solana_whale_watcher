import json
import logging
import websockets
from solders.rpc.responses import GetTransactionResp
from solders.transaction_status import UiTransactionStatusMeta
from solders.signature import Signature
from solders.pubkey import Pubkey
from solders.rpc.api import Client

from typing import List, Dict

logging.basicConfig(level=logging.INFO)

LAMPORTS_PER_SOL = 1_000_000_000

__all__ = ["extract_sol_changes", "monitor_solana"]

def extract_sol_changes(meta: UiTransactionStatusMeta, account_keys: List[Pubkey]) -> List[Dict]:
    """Return SOL balance changes for each account in a transaction.

    Args:
        meta: The transaction meta object returned by the RPC API.
        account_keys: Ordered list of public keys for the transaction accounts.

    Returns:
        A list where each entry describes the SOL change for an account with the
        following keys:
            - ``account``: base58 account string
            - ``delta_lamports``: change in lamports
            - ``delta_SOL``: change in SOL
            - ``direction``: ``"gain"`` or ``"loss"``
            - ``reason``: text description of the change
    """
    pre = meta.pre_balances
    post = meta.post_balances
    fee = meta.fee

    result = []

    for i, (before, after) in enumerate(zip(pre, post)):
        if before != after:
            delta = after - before
            sol_delta = delta / LAMPORTS_PER_SOL
            direction = "gain" if delta > 0 else "loss"

            reason = "received SOL"
            if i == 0 and delta < 0 and abs(delta) == fee:
                reason = "fee"
            elif delta < 0:
                reason = "sent SOL or fee"

            result.append({
                "account": str(account_keys[i]),
                "delta_lamports": delta,
                "delta_SOL": sol_delta,
                "direction": direction,
                "reason": reason
            })

    return result


async def monitor_solana(max_events: int = 10, threshold_SOL: float = 0.0) -> List[Dict]:
    """
    Connects to Solana WebSocket, listens to finalized transaction logs, and returns
    a list of SOL balance changes above the threshold.

    Args:
        max_events: Maximum number of qualifying events to collect.
        threshold_SOL: Minimum delta_SOL to include in the result (absolute value).

    Returns:
        A list of dicts with account, delta_SOL, and reason.
    """
    client = Client("https://api.mainnet-beta.solana.com")
    url = "wss://api.mainnet-beta.solana.com"
    sol_changes_accum: List[Dict] = []

    async with websockets.connect(url) as ws:
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": ["all", {"commitment": "finalized"}]
        }
        await ws.send(json.dumps(req))
        logging.info("Connected to Solana WebSocket")

        count = 0
        while count < max_events:
            msg = await ws.recv()
            data = json.loads(msg)

            try:
                log_entry = data["params"]["result"]
                sig_str = log_entry["value"]["signature"]
                sig = Signature.from_string(sig_str)

                tx_resp: GetTransactionResp = client.get_transaction(
                    sig,
                    encoding="json",
                    max_supported_transaction_version=0
                )
                tx = tx_resp.value
                if tx is None:
                    continue

                meta = tx.transaction.meta
                account_keys = tx.transaction.transaction.message.account_keys
                changes = extract_sol_changes(meta, account_keys)

                filtered = [c for c in changes if abs(c["delta_SOL"]) >= threshold_SOL]
                if filtered:
                    for ch in filtered:
                        logging.info(
                            f"{ch['account']}: {ch['direction']} {abs(ch['delta_SOL']):.9f} SOL ({ch['reason']})"
                        )
                    sol_changes_accum.extend(filtered)
                    count += 1

            except Exception as e:
                logging.error(f"Error: {e}")
                continue

    return sol_changes_accum



