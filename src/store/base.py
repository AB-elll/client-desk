"""AbstractStore — ストアの共通インターフェース

SheetsStore / SupabaseStore はこのクラスを継承して実装する。
config.yml の store.type を変えるだけで差し替え可能。
"""
from abc import ABC, abstractmethod


class AbstractStore(ABC):

    @abstractmethod
    def upsert(self, client_id: str, category: str, record_key: str,
               fields: dict, **kwargs) -> str:
        """レコードを作成または更新する。IDを返す。"""
        ...

    @abstractmethod
    def get_all(self, client_id: str, category: str = None,
                status: str = "active") -> list[dict]:
        """レコード一覧を返す。category省略で全カテゴリ。"""
        ...

    @abstractmethod
    def get_expiring(self, client_id: str, within_days: int) -> list[dict]:
        """primary_deadline が within_days 日以内のレコードを返す。"""
        ...

    @abstractmethod
    def get_sync_state(self, key: str) -> str | None:
        """同期状態の値を取得する。"""
        ...

    @abstractmethod
    def set_sync_state(self, key: str, value: str):
        """同期状態の値を保存する。"""
        ...
