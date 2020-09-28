"""Import hashing methods for verification."""
from utility.hash_util import has_string_256, hash_block
from wallet import Wallet


class Verification:
    """A helper class to verify blockchain."""

    @staticmethod
    def valid_proof(transactions, last_hash, proof):
        """Validate a proof for miners."""
        guess = (
            str([tx.to_ordered_dict for tx in transactions])
            + str(last_hash)
            + str(proof)
        ).encode()
        guess_hash = has_string_256(guess)
        return guess_hash[0:5] == "00000"

    @classmethod
    def verify_chain(cls, blockchain):
        """Verify current blockchain."""
        for (index, block) in enumerate(blockchain):
            if index == 0:
                continue
            if block.previous_hash != hash_block(blockchain[index - 1]):
                return False
            if not cls.valid_proof(
                block.transactions[:-1], block.previous_hash, block.proof
            ):
                print("{:-^80}".format("INVALID PROOF OF WORK!"))
                return False
        return True

    @staticmethod
    def verify_transaction(transaction, get_balance, check_funds=True):
        """Verify sender has sufficient funds for a given transaction."""
        if check_funds is True:
            sender_balance = get_balance()
            return (
                sender_balance >= transaction.amount
                and Wallet.verify_transaction(transaction)
            )
        else:
            return Wallet.verify_transaction(transaction)

    @classmethod
    def verify_transactions(cls, open_transactions, get_balance):
        """Verify all open transactions."""
        return all(
            [
                cls.verify_transaction(tx, get_balance, False)
                for tx in open_transactions
            ]
        )