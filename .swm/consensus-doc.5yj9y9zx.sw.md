---
title: consensus doc
---
# Introduction

This document will walk you through the implementation of the consensus feature.

The feature ensures that transactions are processed and validated by multiple nodes to achieve consensus.

We will cover:

1. Imported modules
2. Content flow
3. Functions
4. Outputs

# Imported modules

<SwmSnippet path="backend/consensus/base.py" line="9">

---

The necessary modules and classes are imported to handle database operations, transaction processing, and node communication.

```

from backend.consensus.vrf import get_validators_for_transaction
from backend.database_handler.chain_snapshot import ChainSnapshot
from backend.database_handler.contract_snapshot import ContractSnapshot
from backend.database_handler.db_client import DBClient
from backend.database_handler.transactions_processor import (
    TransactionsProcessor,
    TransactionStatus,
)
from backend.database_handler.accounts_manager import AccountsManager
from backend.database_handler.types import ConsensusData
from backend.node.base import Node
from backend.node.genvm.types import ExecutionMode, Vote
from backend.protocol_rpc.message_handler.base import MessageHandler
```

---

</SwmSnippet>

# Content flow

<SwmSnippet path="backend/consensus/base.py" line="23">

---

The consensus algorithm is initialized with a database client and a message handler.

```


class ConsensusAlgorithm:
    def __init__(
        self,
        dbclient: DBClient,
        msg_handler: MessageHandler,
    ):
        self.dbclient = dbclient
        self.msg_handler = msg_handler
        self.queues: dict[str, asyncio.Queue] = {}
```

---

</SwmSnippet>

<SwmSnippet path="backend/consensus/base.py" line="34">

---

The main loops for crawling snapshots and running consensus are defined.

```

    def run_crawl_snapshot_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._crawl_snapshot())
        loop.close()

    async def _crawl_snapshot(self):
        while True:
            with self.dbclient.get_session() as session:
                chain_snapshot = ChainSnapshot(session)
                pending_transactions = chain_snapshot.get_pending_transactions()
                for transaction in pending_transactions:
                    address = transaction["to_address"] or transaction["from_address"]
```

---

</SwmSnippet>

<SwmSnippet path="backend/consensus/base.py" line="48">

---

Pending transactions are added to queues for processing.

```

                    if address not in self.queues:
                        self.queues[address] = asyncio.Queue()
                    await self.queues[address].put(transaction)
            await asyncio.sleep(DEFAULT_CONSENSUS_SLEEP_TIME)

    def run_consensus_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._run_consensus())
        loop.close()
```

---

</SwmSnippet>

<SwmSnippet path="backend/consensus/base.py" line="59">

---

The consensus loop processes transactions using asynchronous tasks.

```

    async def _run_consensus(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        # watch out! as ollama uses GPU resources and webrequest aka selenium uses RAM
        # TODO: async sessions would be a good idea to not block the current thread
        while True:
            try:
                async with asyncio.TaskGroup() as tg:
                    for queue in [q for q in self.queues.values() if not q.empty()]:
                        # sessions cannot be shared between coroutines, we need to create a new session for each coroutine
                        # https://docs.sqlalchemy.org/en/20/orm/session_basics.html#is-the-session-thread-safe-is-asyncsession-safe-to-share-in-concurrent-tasks
                        transaction = await queue.get()
                        with self.dbclient.get_session() as session:
                            tg.create_task(
                                self.exec_transaction(
                                    transaction,
                                    TransactionsProcessor(session),
                                    ChainSnapshot(session),
                                    AccountsManager(session),
                                    session,
                                )
                            )
```

---

</SwmSnippet>

# Functions

## <SwmToken path="/backend/consensus/base.py" pos="35:3:3" line-data="    def run_crawl_snapshot_loop(self):">`run_crawl_snapshot_loop`</SwmToken>

<SwmSnippet path="backend/consensus/base.py" line="34">

---

Starts a new event loop to crawl snapshots and fetch pending transactions.

```

    def run_crawl_snapshot_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._crawl_snapshot())
        loop.close()

    async def _crawl_snapshot(self):
        while True:
            with self.dbclient.get_session() as session:
                chain_snapshot = ChainSnapshot(session)
                pending_transactions = chain_snapshot.get_pending_transactions()
                for transaction in pending_transactions:
                    address = transaction["to_address"] or transaction["from_address"]
```

---

</SwmSnippet>

## <SwmToken path="/backend/consensus/base.py" pos="54:3:3" line-data="    def run_consensus_loop(self):">`run_consensus_loop`</SwmToken>

<SwmSnippet path="backend/consensus/base.py" line="48">

---

Starts a new event loop to run the consensus process.

```

                    if address not in self.queues:
                        self.queues[address] = asyncio.Queue()
                    await self.queues[address].put(transaction)
            await asyncio.sleep(DEFAULT_CONSENSUS_SLEEP_TIME)

    def run_consensus_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._run_consensus())
        loop.close()
```

---

</SwmSnippet>

## <SwmToken path="/backend/consensus/base.py" pos="57:7:7" line-data="        loop.run_until_complete(self._run_consensus())">`_run_consensus`</SwmToken>

<SwmSnippet path="backend/consensus/base.py" line="59">

---

Processes transactions from the queues and executes them using multiple validators.

```

    async def _run_consensus(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        # watch out! as ollama uses GPU resources and webrequest aka selenium uses RAM
        # TODO: async sessions would be a good idea to not block the current thread
        while True:
            try:
                async with asyncio.TaskGroup() as tg:
                    for queue in [q for q in self.queues.values() if not q.empty()]:
                        # sessions cannot be shared between coroutines, we need to create a new session for each coroutine
                        # https://docs.sqlalchemy.org/en/20/orm/session_basics.html#is-the-session-thread-safe-is-asyncsession-safe-to-share-in-concurrent-tasks
                        transaction = await queue.get()
                        with self.dbclient.get_session() as session:
                            tg.create_task(
                                self.exec_transaction(
                                    transaction,
                                    TransactionsProcessor(session),
                                    ChainSnapshot(session),
                                    AccountsManager(session),
                                    session,
                                )
                            )
```

---

</SwmSnippet>

<SwmSnippet path="backend/consensus/base.py" line="81">

---

Handles exceptions and logs errors.

```

            except Exception as e:
                print("Error running consensus", e)
                print(traceback.format_exc())
            await asyncio.sleep(DEFAULT_CONSENSUS_SLEEP_TIME)

    async def exec_transaction(
        self,
        transaction: dict,
        transactions_processor: TransactionsProcessor,
        snapshot: ChainSnapshot,
        accounts_manager: AccountsManager,
        session: Session,
    ):
        if (
            transactions_processor.get_transaction_by_id(transaction["id"])["status"]
            != TransactionStatus.PENDING.value
        ):
            # This is a patch for a TOCTOU problem we have https://github.com/yeagerai/genlayer-simulator/issues/387
            # Problem: Pending transactions are checked by `_crawl_snapshot`, which appends them to queues. These queues are consumed by `_run_consensus`, which processes the transactions. This means that a transaction can be processed multiple times, since `_crawl_snapshot` can append the same transaction to the queue multiple times.
            # Partial solution: This patch checks if the transaction is still pending before processing it. This is not the best solution, but we'll probably refactor the whole consensus algorithm in the short term.
            print(" ~ ~ ~ ~ ~ TRANSACTION ALREADY IN PROCESS: ", transaction)
            return
```

---

</SwmSnippet>

## <SwmToken path="/backend/consensus/base.py" pos="73:3:3" line-data="                                self.exec_transaction(">`exec_transaction`</SwmToken>

<SwmSnippet path="backend/consensus/base.py" line="81">

---

Executes a transaction and updates its status. Checks if the transaction is still pending to avoid duplicate processing.

```

            except Exception as e:
                print("Error running consensus", e)
                print(traceback.format_exc())
            await asyncio.sleep(DEFAULT_CONSENSUS_SLEEP_TIME)

    async def exec_transaction(
        self,
        transaction: dict,
        transactions_processor: TransactionsProcessor,
        snapshot: ChainSnapshot,
        accounts_manager: AccountsManager,
        session: Session,
    ):
        if (
            transactions_processor.get_transaction_by_id(transaction["id"])["status"]
            != TransactionStatus.PENDING.value
        ):
            # This is a patch for a TOCTOU problem we have https://github.com/yeagerai/genlayer-simulator/issues/387
            # Problem: Pending transactions are checked by `_crawl_snapshot`, which appends them to queues. These queues are consumed by `_run_consensus`, which processes the transactions. This means that a transaction can be processed multiple times, since `_crawl_snapshot` can append the same transaction to the queue multiple times.
            # Partial solution: This patch checks if the transaction is still pending before processing it. This is not the best solution, but we'll probably refactor the whole consensus algorithm in the short term.
            print(" ~ ~ ~ ~ ~ TRANSACTION ALREADY IN PROCESS: ", transaction)
            return
```

---

</SwmSnippet>

<SwmSnippet path="backend/consensus/base.py" line="104">

---

Logs the execution of the transaction and updates its status.

```

        print(" ~ ~ ~ ~ ~ EXECUTING TRANSACTION: ", transaction)
        # Update transaction status
        transactions_processor.update_transaction_status(
            transaction["id"], TransactionStatus.PROPOSING
        )

        # If transaction is a transfer, execute it
        # TODO: consider when the transfer involves a contract account, bridging, etc.
        if transaction["type"] == 0:
            return self.execute_transfer(
                transaction, transactions_processor, accounts_manager
            )
```

---

</SwmSnippet>

<SwmSnippet path="backend/consensus/base.py" line="117">

---

Selects a leader and validators for the transaction.

```

        # Select Leader and validators
        all_validators = snapshot.get_all_validators()
        leader, remaining_validators = get_validators_for_transaction(
            all_validators, DEFAULT_VALIDATORS_COUNT
        )
        num_validators = len(remaining_validators) + 1
```

---

</SwmSnippet>

<SwmSnippet path="backend/consensus/base.py" line="124">

---

Creates a leader node and executes the transaction.

```

        contract_address = transaction.get("to_address", None)
        contract_snapshot = ContractSnapshot(contract_address, session)

        # Create Leader
        leader_node = Node(
            contract_snapshot=contract_snapshot,
            address=leader["address"],
            validator_mode=ExecutionMode.LEADER,
            stake=leader["stake"],
            provider=leader["provider"],
            model=leader["model"],
            config=leader["config"],
            msg_handler=self.msg_handler,
        )
```

---

</SwmSnippet>

<SwmSnippet path="backend/consensus/base.py" line="139">

---

Updates the transaction status and creates validator nodes.

```

        # Leader executes transaction
        leader_receipt = await leader_node.exec_transaction(transaction)
        votes = {leader["address"]: leader_receipt.vote.value}
        # Update transaction status
        transactions_processor.update_transaction_status(
            transaction["id"], TransactionStatus.COMMITTING
        )
```

---

</SwmSnippet>

<SwmSnippet path="backend/consensus/base.py" line="163">

---

Validators execute the transaction and their votes are collected.

```

        # Validators execute transaction
        validators_results = []
        validation_tasks = [
            (
                validator.exec_transaction(transaction)
            )  # watch out! as ollama uses GPU resources and webrequest aka selenium uses RAM
            for validator in validator_nodes
        ]
        validation_results = await asyncio.gather(*validation_tasks)
```

---

</SwmSnippet>

<SwmSnippet path="backend/consensus/base.py" line="173">

---

Updates the transaction status based on the votes.

```

        for i in range(len(validation_results)):
            votes[f"{validator_nodes[i].address}"] = validation_results[i].vote.value
        transactions_processor.update_transaction_status(
            transaction["id"],
            TransactionStatus.REVEALING,
        )
```

---

</SwmSnippet>

<SwmSnippet path="backend/consensus/base.py" line="180">

---

Checks if consensus is reached and updates the transaction status.

```

        if (
            len([vote for vote in votes.values() if vote == Vote.AGREE.value])
            < num_validators // 2
        ):
            raise Exception("Consensus not reached")

        transactions_processor.update_transaction_status(
            transaction["id"], TransactionStatus.ACCEPTED
        )
```

---

</SwmSnippet>

<SwmSnippet path="backend/consensus/base.py" line="190">

---

Creates consensus data and registers or updates contract state.

```

        final = False
        consensus_data = ConsensusData(
            final=final,
            votes=votes,
            leader_receipt=leader_receipt,
            validators=validators_results,
        ).to_dict()

        # Register contract if it is a new contract
        if transaction["type"] == 1:
            new_contract = {
                "id": transaction["data"]["contract_address"],
                "data": {
                    "state": leader_receipt.contract_state,
                    "code": transaction["data"]["contract_code"],
                },
            }
            contract_snapshot.register_contract(new_contract)

        # Update contract state if it is an existing contract
        else:
            contract_snapshot.update_contract_state(leader_receipt.contract_state)

        # Finalize transaction
        transactions_processor.set_transaction_result(
            transaction["id"],
            consensus_data,
        )
```

---

</SwmSnippet>

## <SwmToken path="/backend/consensus/base.py" pos="114:5:5" line-data="            return self.execute_transfer(">`execute_transfer`</SwmToken>

<SwmSnippet path="backend/consensus/base.py" line="219">

---

Handles the transfer of native tokens between accounts, updating balances and transaction status.

```

    def execute_transfer(
        self,
        transaction: dict,
        transactions_processor: TransactionsProcessor,
        accounts_manager: AccountsManager,
    ):
        """
        Executes a native token transfer between Externally Owned Accounts (EOAs).

        This function handles the transfer of native tokens from one EOA to another.
        It updates the balances of both the sender and recipient accounts, and
        manages the transaction status throughout the process.

        Args:
            transaction (dict): The transaction details including from_address, to_address, and value.
            transactions_processor (TransactionsProcessor): Processor to update transaction status.
            accounts_manager (AccountsManager): Manager to handle account balance updates.
        """

        # If from_address is None, it is a fund_account call
        if not transaction["from_address"] is None:
            # Get the balance of the sender account
            from_balance = accounts_manager.get_account_balance(
                transaction["from_address"]
            )

            # If the sender does not have enough balance, set the transaction status to UNDETERMINED
            if from_balance < transaction["value"]:
                transactions_processor.update_transaction_status(
                    transaction["id"], TransactionStatus.UNDETERMINED
                )
                return

            # Update the balance of the sender account
            accounts_manager.update_account_balance(
                transaction["from_address"], from_balance - transaction["value"]
            )

        # If to_address is None, it is a burn call
        if not transaction["to_address"] is None:
            to_balance = accounts_manager.get_account_balance(transaction["to_address"])

            # Update the balance of the recipient account
            accounts_manager.update_account_balance(
                transaction["to_address"], to_balance + transaction["value"]
            )

        transactions_processor.update_transaction_status(
            transaction["id"], TransactionStatus.FINALIZED
        )
```

---

</SwmSnippet>

# Outputs

<SwmSnippet path="backend/consensus/base.py" line="209">

---

The final output includes the transaction result, consensus data, and updated contract state.

```

        # Update contract state if it is an existing contract
        else:
            contract_snapshot.update_contract_state(leader_receipt.contract_state)

        # Finalize transaction
        transactions_processor.set_transaction_result(
            transaction["id"],
            consensus_data,
        )
```

---

</SwmSnippet>

<SwmMeta version="3.0.0" repo-id="Z2l0aHViJTNBJTNBZ2VubGF5ZXItc2ltdWxhdG9yJTNBJTNBWWVhZ2VyQUktQnVsYXQ=" repo-name="genlayer-simulator"><sup>Powered by [Swimm](https://app.swimm.io/)</sup></SwmMeta>
