import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useTransactionsStore } from '@/stores';
import { useRpcClient } from '@/hooks';
import { type TransactionItem } from '@/types';

vi.mock('@/hooks', () => ({
  useRpcClient: vi.fn(),
  useWebSocketClient: vi.fn(() => ({
    connected: true,
    emit: vi.fn(),
  })),
  useDb: vi.fn(() => ({
    transaction: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
  })),
  useSetupStores: vi.fn(() => ({
    setupStores: vi.fn(),
  })),
  useFileName: vi.fn(() => ({
    cleanupFileName: vi.fn(),
  })),
}));

const testTransaction: TransactionItem = {
  hash: '0x1234567890123456789012345678901234567890',
  type: 'deploy',
  status: 'PENDING',
  contractAddress: '0xAf4ec2548dBBdc43ab6dCFbD4EdcEedde3FEAFB5',
  localContractId: '47490604-6ee9-4c0e-bf31-05d33197eedd',
};

const updatedTransactionPayload = {
  ...testTransaction,
  status: 'FINALIZED',
};

describe('useTransactionsStore', () => {
  let transactionsStore: ReturnType<typeof useTransactionsStore>;
  const mockRpcClient = {
    getTransactionByHash: vi.fn(),
  };

  beforeEach(() => {
    setActivePinia(createPinia());
    (useRpcClient as Mock).mockReturnValue(mockRpcClient);
    transactionsStore = useTransactionsStore();
    transactionsStore.transactions = [];
    mockRpcClient.getTransactionByHash.mockClear();
  });

  it('should add a transaction', () => {
    transactionsStore.addTransaction(testTransaction);
    expect(transactionsStore.transactions).to.deep.include(testTransaction);
  });

  it('should remove an added transaction', () => {
    transactionsStore.addTransaction(testTransaction);
    expect(transactionsStore.transactions).to.deep.include(testTransaction);
    transactionsStore.removeTransaction(testTransaction);
    expect(transactionsStore.transactions).not.to.deep.include(testTransaction);
  });

  it('should update a transaction', () => {
    transactionsStore.addTransaction(testTransaction);
    transactionsStore.updateTransaction(updatedTransactionPayload);
    expect(transactionsStore.transactions[0].status).toBe('FINALIZED');
  });

  it('should get a transaction by hash using rpcClient', async () => {
    const transactionHash = '0x1234567890123456789012345678901234567890';
    const transactionData = { id: transactionHash, status: 'PENDING' };
    mockRpcClient.getTransactionByHash.mockResolvedValue(transactionData);

    const result = await transactionsStore.getTransaction(transactionHash);

    expect(mockRpcClient.getTransactionByHash).toHaveBeenCalledWith(
      transactionHash,
    );
    expect(result).toEqual(transactionData);
  });

  it('should clear transactions for a specific contract', () => {
    const tx1 = {
      ...testTransaction,
      hash: '0x1234567890123456789012345678901234567891',
      localContractId: 'contract-1',
    };
    const tx2 = {
      ...testTransaction,
      hash: '0x1234567890123456789012345678901234567892',
      localContractId: 'contract-2',
    };

    transactionsStore.addTransaction(tx1);
    transactionsStore.addTransaction(tx2);

    transactionsStore.clearTransactionsForContract('contract-1');

    expect(transactionsStore.transactions).toEqual([tx2]);
  });

  it('should refresh pending transactions', async () => {
    const pendingTransaction = {
      ...testTransaction,
      status: 'PENDING',
    };
    const updatedTransaction = {
      ...pendingTransaction,
      status: 'FINALIZED',
    };

    transactionsStore.addTransaction(pendingTransaction);
    mockRpcClient.getTransactionByHash.mockResolvedValue(updatedTransaction);

    await transactionsStore.refreshPendingTransactions();

    expect(mockRpcClient.getTransactionByHash).toHaveBeenCalledWith(
      pendingTransaction.hash,
    );
    expect(transactionsStore.transactions[0].status).toBe('FINALIZED');
  });
});
