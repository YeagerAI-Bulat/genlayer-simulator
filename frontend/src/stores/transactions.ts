import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { TransactionItem } from '@/types';
import { useRpcClient, useWebSocketClient } from '@/hooks';
import { useContractsStore } from '@/stores';

export const useTransactionsStore = defineStore('transactionsStore', () => {
  const rpcClient = useRpcClient();
  const webSocketClient = useWebSocketClient();
  const transactions = ref<TransactionItem[]>([]);
  const contractsStore = useContractsStore();
  const subscriptions = new Set();

  function addTransaction(tx: TransactionItem) {
    transactions.value.unshift(tx); // Push on top in case there's no date property yet
    subscribe([tx.hash]);
  }

  function removeTransaction(tx: TransactionItem) {
    transactions.value = transactions.value.filter((t) => t.hash !== tx.hash);
    unsubscribe(tx.hash);
  }

  function updateTransaction(tx: any) {
    const currentTxIndex = transactions.value.findIndex(
      (t) => t.hash === tx.hash,
    );

    if (currentTxIndex !== -1) {
      const currentTx = transactions.value[currentTxIndex];

      transactions.value.splice(currentTxIndex, 1, {
        ...currentTx,
        status: tx.status,
        data: tx,
      });

      if (
        currentTx.status === 'ACCEPTED' &&
        currentTx.type === 'deploy' &&
        tx.status === 'FINALIZED'
      ) {
        contractsStore.addDeployedContract({
          contractId: currentTx.localContractId,
          address: tx.data.contract_address,
          defaultState: '{}',
        });
      }
    } else {
      // Temporary logging to debug always-PENDING transactions
      console.warn('Transaction not found', tx);
      console.trace('updateTransaction', tx);
    }
  }

  async function refreshPendingTransactions() {
    const pendingTxs = transactions.value.filter(
      (tx: TransactionItem) => tx.status !== 'FINALIZED',
    ) as TransactionItem[];

    await Promise.all(
      pendingTxs.map(async (tx) => {
        const newTx = await getTransaction(tx.hash);
        updateTransaction(newTx);
      }),
    );
  }

  async function getTransaction(hash: string) {
    return rpcClient.getTransactionByHash(hash);
  }

  function clearTransactionsForContract(contractId: string) {
    const contractTxs = transactions.value.filter(
      (t) => t.localContractId === contractId,
    );

    contractTxs.forEach((t) => unsubscribe(t.hash));

    transactions.value = transactions.value.filter(
      (t) => t.localContractId !== contractId,
    );
  }

  function subscribe(topics: string[]) {
    subscriptions.add(topics);
    if (webSocketClient.connected) {
      webSocketClient.emit('subscribe', topics);
    }
  }

  function unsubscribe(topic: string) {
    const deleted = subscriptions.delete(topic);
    if (deleted && webSocketClient.connected) {
      webSocketClient.emit('unsubscribe', [topic]);
    }
  }

  function initSubscriptions() {
    subscribe(transactions.value.map((t) => t.hash));
  }

  return {
    transactions,
    getTransaction,
    addTransaction,
    removeTransaction,
    updateTransaction,
    clearTransactionsForContract,
    refreshPendingTransactions,
    initSubscriptions,
  };
});
