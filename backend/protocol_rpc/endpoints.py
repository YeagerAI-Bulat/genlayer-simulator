# rpc/endpoints.py
import random
import json
from functools import partial
from flask_jsonrpc import JSONRPC

from backend.database_handler.db_client import DBClient
from backend.protocol_rpc.configuration import GlobalConfiguration
from backend.protocol_rpc.message_handler.base import MessageHandler
from backend.database_handler.accounts_manager import AccountsManager
from backend.database_handler.validators_registry import ValidatorsRegistry

from backend.node.create_nodes.create_nodes import (
    get_default_config_for_providers_and_nodes,
    get_providers,
    get_provider_models,
    random_validator_config,
)

from backend.protocol_rpc.endpoint_generator import (
    generate_rpc_endpoint,
    generate_rpc_endpoint_for_partial,
)
from backend.protocol_rpc.transactions_parser import (
    decode_signed_transaction,
    transaction_has_valid_signature,
    decode_method_call_data,
    decode_deployment_data,
)
from backend.errors.errors import InvalidAddressError, InvalidTransactionError

from backend.database_handler.transactions_processor import TransactionsProcessor
from backend.node.base import Node
from backend.node.genvm.types import Receipt, ExecutionResultStatus, ExecutionMode


def ping() -> dict:
    return {"status": "OK"}


def create_account(accounts_manager: AccountsManager) -> dict:
    new_account = accounts_manager.create_new_account(0)
    return {"account_address": new_account.address}


def fund_account(
    accounts_manager: AccountsManager, account_address: str, amount: int
) -> dict:
    if not accounts_manager.is_valid_address(account_address):
        raise InvalidAddressError(account_address)

    accounts_manager.fund_account(account_address, amount)
    return {"account_address": account_address, "amount": amount}


def send_transaction(
    transactions_processor: TransactionsProcessor,
    accounts_manager: AccountsManager,
    from_account: str,
    to_account: str,
    amount: int,
) -> dict:
    if not accounts_manager.is_valid_address(from_account):
        raise InvalidAddressError(from_account)

    if not accounts_manager.is_valid_address(to_account):
        raise InvalidAddressError(to_account)

    transaction_id = transactions_processor.insert_transaction(
        from_account, to_account, None, amount, 0
    )

    return {"transaction_id": transaction_id}


def get_transaction_by_id(
    transactions_processor: TransactionsProcessor, transaction_id: str
) -> dict:
    return transactions_processor.get_transaction_by_id(transaction_id)


def get_contract_schema(
    accounts_manager: AccountsManager, contract_address: str
) -> dict:
    if not accounts_manager.is_valid_address(contract_address):
        raise InvalidAddressError(
            contract_address,
            "Incorrect address format. Please provide a valid address.",
        )
    contract_account = accounts_manager.get_account_or_fail(contract_address)

    node = Node(
        contract_snapshot=None,
        address="",
        validator_mode=ExecutionMode.LEADER,
        stake=0,
        provider="",
        model="",
        config=None,
        leader_receipt=None,
    )
    return node.get_contract_schema(contract_account["data"]["code"])


def get_contract_schema_for_code(contract_code: str) -> dict:
    node = Node(
        contract_snapshot=None,
        address="",
        validator_mode=ExecutionMode.LEADER,
        stake=0,
        provider="",
        model="",
        config=None,
        leader_receipt=None,
    )
    return node.get_contract_schema(contract_code)


def get_contract_state(
    accounts_manager: AccountsManager,
    contract_address: str,
    method_name: str,
    method_args: list,
) -> dict:
    if not accounts_manager.is_valid_address(contract_address):
        raise InvalidAddressError(contract_address)

    contract_account = accounts_manager.get_account(contract_address)
    node = Node(
        contract_snapshot=None,
        address="",
        validator_mode=ExecutionMode.LEADER,
        stake=0,
        provider="",
        model="",
        config=None,
        leader_receipt=None,
    )
    return node.get_contract_data(
        code=contract_account["data"]["code"],
        state=contract_account["data"]["state"],
        method_name=method_name,
        method_args=method_args,
    )


def get_all_validators(validators_registry: ValidatorsRegistry) -> dict:
    return validators_registry.get_all_validators()


def get_validator(
    validators_registry: ValidatorsRegistry, validator_address: str
) -> dict:
    return validators_registry.get_validator(validator_address)


def create_validator(
    validators_registry: ValidatorsRegistry,
    accounts_manager: AccountsManager,
    stake: int,
    provider: str,
    model: str,
    config: json,
) -> dict:
    new_address = accounts_manager.create_new_account().address
    return validators_registry.create_validator(
        new_address, stake, provider, model, config
    )


def update_validator(
    validators_registry: ValidatorsRegistry,
    accounts_manager: AccountsManager,
    validator_address: str,
    stake: int,
    provider: str,
    model: str,
    config: json,
) -> dict:
    if not accounts_manager.is_valid_address(validator_address):
        raise InvalidAddressError(validator_address)
    return validators_registry.update_validator(
        validator_address, stake, provider, model, config
    )


def delete_validator(
    validators_registry: ValidatorsRegistry,
    accounts_manager: AccountsManager,
    validator_address: str,
) -> dict:
    if not accounts_manager.is_valid_address(validator_address):
        raise InvalidAddressError(validator_address)

    validators_registry.delete_validator(validator_address)
    return validator_address


def delete_all_validators(
    validators_registry: ValidatorsRegistry,
) -> dict:
    validators_registry.delete_all_validators()
    return validators_registry.get_all_validators()


def get_providers_and_models(config: GlobalConfiguration) -> dict:
    default_config = get_default_config_for_providers_and_nodes()
    providers = get_providers()
    providers_and_models = {}
    for provider in providers:
        providers_and_models[provider] = get_provider_models(
            default_config["providers"], provider, config.get_ollama_url
        )
    return providers_and_models


# TODO: Refactor this function to put the random config generator inside the domain
# and reuse the generate single random validator function
def create_random_validators(
    validators_registry: ValidatorsRegistry,
    accounts_manager: AccountsManager,
    config: GlobalConfiguration,
    count: int,
    min_stake: int,
    max_stake: int,
    providers: list = None,
    fixed_provider: str = None,
    fixed_model: str = None,
) -> dict:
    providers = providers or []

    for _ in range(count):
        stake = random.uniform(min_stake, max_stake)
        validator_address = accounts_manager.create_new_account().address
        details = random_validator_config(config.get_ollama_url, providers=providers)
        new_validator = validators_registry.create_validator(
            validator_address,
            stake,
            fixed_provider or details["provider"],
            fixed_model or details["model"],
            details["config"],
        )
        if not "id" in new_validator:
            raise SystemError("Failed to create Validator")
    response = validators_registry.get_all_validators()
    return response


def create_random_validator(
    validators_registry: ValidatorsRegistry,
    accounts_manager: AccountsManager,
    config: GlobalConfiguration,
    stake: int,
) -> dict:
    validator_address = accounts_manager.create_new_account().address
    details = random_validator_config(config.get_ollama_url)
    response = validators_registry.create_validator(
        validator_address,
        stake,
        details["provider"],
        details["model"],
        details["config"],
    )
    return response


def count_validators(validators_registry: ValidatorsRegistry) -> dict:
    return validators_registry.count_validators()


def clear_db_tables(db_client: DBClient, tables: list) -> dict:
    db_client.clear_tables(tables)


def send_raw_transaction(
    transactions_processor: TransactionsProcessor,
    accounts_manager: AccountsManager,
    signed_transaction: str,
) -> dict:
    # Decode transaction
    decoded_transaction = decode_signed_transaction(signed_transaction)

    # Validate transaction
    if decoded_transaction is None:
        raise InvalidTransactionError("Invalid transaction data")

    from_address = decoded_transaction.from_address
    if not accounts_manager.is_valid_address(from_address):
        raise InvalidAddressError(
            from_address, f"Invalid address from_address: {from_address}"
        )

    transaction_signature_valid = transaction_has_valid_signature(
        signed_transaction, decoded_transaction
    )
    if not transaction_signature_valid:
        raise InvalidTransactionError("Transaction signature verification failed")

    to_address = decoded_transaction.to_address

    transaction_data = {}
    result = {}
    transaction_type = -1
    if to_address and to_address != "0x":
        # Contract Call
        if not accounts_manager.is_valid_address(to_address):
            raise InvalidAddressError(
                to_address, f"Invalid address to_address: {to_address}"
            )
        decoded_data = decode_method_call_data(decoded_transaction.data)
        transaction_data = {
            "function_name": decoded_data.function_name,
            "function_args": decoded_data.function_args,
        }
        transaction_type = 2
    else:
        # Contract deployment
        decoded_data = decode_deployment_data(decoded_transaction.data)
        new_contract_address = accounts_manager.create_new_account().address

        transaction_data = {
            "contract_address": new_contract_address,
            "contract_code": decoded_data.contract_code,
            "constructor_args": decoded_data.constructor_args,
        }
        result["contract_address"] = new_contract_address
        to_address = None
        transaction_type = 1

    # Insert transaction into the database
    transaction_id = transactions_processor.insert_transaction(
        from_address, to_address, transaction_data, 0, transaction_type
    )
    result["transaction_id"] = transaction_id

    return result


def register_all_rpc_endpoints(
    jsonrpc: JSONRPC,
    msg_handler: MessageHandler,
    genlayer_db_client: DBClient,
    accounts_manager: AccountsManager,
    transactions_processor: TransactionsProcessor,
    validators_registry: ValidatorsRegistry,
    config: GlobalConfiguration,
):
    register_rpc_endpoint = partial(generate_rpc_endpoint, jsonrpc, msg_handler)
    register_rpc_endpoint_for_partial = partial(
        generate_rpc_endpoint_for_partial, register_rpc_endpoint
    )

    register_rpc_endpoint(ping)
    register_rpc_endpoint(get_contract_schema_for_code)

    register_rpc_endpoint_for_partial(
        clear_db_tables, genlayer_db_client, ["current_state", "transactions"]
    )
    register_rpc_endpoint_for_partial(get_providers_and_models, config)
    register_rpc_endpoint_for_partial(
        create_validator, validators_registry, accounts_manager
    )
    register_rpc_endpoint_for_partial(
        update_validator, validators_registry, accounts_manager
    )
    register_rpc_endpoint_for_partial(delete_validator, validators_registry)
    register_rpc_endpoint_for_partial(get_validator, validators_registry)
    register_rpc_endpoint_for_partial(delete_all_validators, validators_registry)
    register_rpc_endpoint_for_partial(get_all_validators, validators_registry)
    register_rpc_endpoint_for_partial(
        create_random_validator, validators_registry, accounts_manager, config
    )
    register_rpc_endpoint_for_partial(
        create_random_validators, validators_registry, accounts_manager, config
    )
    register_rpc_endpoint_for_partial(
        send_transaction, transactions_processor, accounts_manager
    )
    register_rpc_endpoint_for_partial(create_account, accounts_manager)
    register_rpc_endpoint_for_partial(fund_account, accounts_manager)
    register_rpc_endpoint_for_partial(get_contract_schema, accounts_manager)
    register_rpc_endpoint_for_partial(get_contract_state, accounts_manager)
    register_rpc_endpoint_for_partial(get_transaction_by_id, transactions_processor)
    register_rpc_endpoint_for_partial(
        send_raw_transaction, transactions_processor, accounts_manager
    )