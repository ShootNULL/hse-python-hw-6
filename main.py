from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass(frozen=True)
class Operation:
    """Структура одной операции по счёту."""
    op_type: str                 # 'deposit' | 'withdraw'
    amount: float
    timestamp: datetime
    balance_after: float
    status: str                  # 'success' | 'fail'
    credit_used: Optional[bool] = None  # только для CreditAccount (True/False), иначе None


class Account:
    """
    Базовый банковский счёт.
    - Баланс не может быть отрицательным.
    - Все попытки операций фиксируются в истории (включая fail).
    """

    def __init__(self, account_holder: str, balance: float = 0.0) -> None:
        if not isinstance(account_holder, str) or not account_holder.strip():
            raise ValueError("account_holder должен быть непустой строкой")

        if not isinstance(balance, (int, float)):
            raise TypeError("balance должен быть числом")

        if balance < 0:
            raise ValueError("Начальный баланс не может быть отрицательным")

        self.holder: str = account_holder.strip()
        self._balance: float = float(balance)  # приватный баланс
        self.operations_history: List[Operation] = []

    def _add_operation(
        self,
        op_type: str,
        amount: float,
        status: str,
        credit_used: Optional[bool] = None,
    ) -> None:
        """Внутренний метод: добавляет запись об операции в историю."""
        op = Operation(
            op_type=op_type,
            amount=float(amount),
            timestamp=datetime.now(),
            balance_after=float(self._balance),
            status=status,
            credit_used=credit_used,
        )
        self.operations_history.append(op)

    @staticmethod
    def _validate_amount(amount: Any) -> float:
        """Проверка суммы: должна быть числом > 0."""
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма операции должна быть числом")
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Сумма операции должна быть положительной")
        return amount

    def deposit(self, amount: float) -> bool:
        """
        Пополнение счёта.
        Возвращает True при успехе.
        """
        amount = self._validate_amount(amount)

        self._balance += amount
        self._add_operation(op_type="deposit", amount=amount, status="success")
        return True

    def withdraw(self, amount: float) -> bool:
        """
        Снятие средств.
        Если средств недостаточно — операция fail, но попытка фиксируется.
        Возвращает True при успехе, иначе False.
        """
        amount = self._validate_amount(amount)

        if amount > self._balance:
            self._add_operation(op_type="withdraw", amount=amount, status="fail")
            return False

        self._balance -= amount
        self._add_operation(op_type="withdraw", amount=amount, status="success")
        return True

    def get_balance(self) -> float:
        """Текущий баланс (геттер)."""
        return float(self._balance)

    def get_history(self) -> List[Dict[str, Any]]:
        """
        История операций в удобном формате (list[dict]).
        datetime возвращаем в ISO-строке, чтобы было удобно печатать/сохранять.
        """
        history: List[Dict[str, Any]] = []
        for op in self.operations_history:
            row = asdict(op)
            row["timestamp"] = op.timestamp.isoformat(sep=" ", timespec="seconds")
            history.append(row)
        return history


class CreditAccount(Account):
    """
    Кредитный счёт:
    - баланс может быть отрицательным, но не ниже -credit_limit
    - можно узнать доступный кредит: balance + credit_limit
    - в истории хранится credit_used (использовались ли кредитные средства)
    """

    def __init__(self, account_holder: str, balance: float = 0.0, credit_limit: float = 0.0) -> None:
        if not isinstance(credit_limit, (int, float)):
            raise TypeError("credit_limit должен быть числом")

        credit_limit = float(credit_limit)
        if credit_limit < 0:
            raise ValueError("credit_limit не может быть отрицательным")

        # Для кредитного счета баланс может быть отрицательным, но не ниже -credit_limit.
        if not isinstance(balance, (int, float)):
            raise TypeError("balance должен быть числом")

        balance = float(balance)
        if balance < -credit_limit:
            raise ValueError("Начальный баланс не может быть ниже -credit_limit")

        # Не вызываем Account.__init__ с проверкой balance>=0 — делаем вручную.
        if not isinstance(account_holder, str) or not account_holder.strip():
            raise ValueError("account_holder должен быть непустой строкой")

        self.holder: str = account_holder.strip()
        self._balance: float = balance
        self.credit_limit: float = credit_limit
        self.operations_history: List[Operation] = []

    def get_available_credit(self) -> float:
        """Сколько кредитных средств ещё доступно."""
        return float(self._balance + self.credit_limit)

    def deposit(self, amount: float) -> bool:
        """
        Пополнение кредитного счёта.
        credit_used=False (пополнение не 'использует кредит').
        """
        amount = self._validate_amount(amount)

        self._balance += amount
        self._add_operation(op_type="deposit", amount=amount, status="success", credit_used=False)
        return True

    def withdraw(self, amount: float) -> bool:
        """
        Снятие с кредитного счёта.
        Разрешаем уход в минус до -credit_limit.
        В историю пишем credit_used=True, если после операции баланс < 0
        или если уже был минус (т.е. кредит точно задействован).
        """
        amount = self._validate_amount(amount)

        new_balance = self._balance - amount
        if new_balance < -self.credit_limit:
            # fail, но попытка фиксируется
            credit_used = self._balance < 0  # если уже в минусе, кредит задействован
            self._add_operation(op_type="withdraw", amount=amount, status="fail", credit_used=credit_used)
            return False

        was_credit_used_before = self._balance < 0
        self._balance = new_balance
        credit_used = was_credit_used_before or (self._balance < 0)

        self._add_operation(op_type="withdraw", amount=amount, status="success", credit_used=credit_used)
        return True

if __name__ == "__main__":
    acc = Account("Иван", 100)
    acc.deposit(50)
    acc.withdraw(500)  # fail
    acc.withdraw(120)  # success
    print("Account balance:", acc.get_balance())
    print("Account history:", acc.get_history())

    cacc = CreditAccount("Пётр", balance=0, credit_limit=300)
    cacc.withdraw(100)   # success, credit_used=True (уходит в -100)
    cacc.withdraw(250)   # fail (попытка уйти в -350 < -300)
    cacc.deposit(80)     # success
    print("Credit balance:", cacc.get_balance())
    print("Available credit:", cacc.get_available_credit())
    print("Credit history:", cacc.get_history())
