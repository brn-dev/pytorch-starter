import abc
import datetime
import inspect
import os.path
from pathlib import Path
from typing import Any, Callable, TypedDict, Optional

import torch
from tinydb import TinyDB, Query
from tinydb.queries import QueryLike
from torch import nn


class ModelEntry(TypedDict):
    model_id: str
    parent_model_id: Optional[str]
    state_dict_path: str

    model_info: dict[str, Any]

    init_function: Optional[str]

    last_update_time: str


class ModelDB(abc.ABC):

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @abc.abstractmethod
    def close(self):
        raise NotImplemented

    @abc.abstractmethod
    def save_model_state_dict(
            self,
            model: nn.Module,
            model_id: str,
            parent_model_id: str,
            model_info: dict[str, Any],
            init_function: Optional[Callable[[], nn.Module]] = None,
    ) -> ModelEntry:
        raise NotImplemented

    @abc.abstractmethod
    def load_model_state_dict(self, model: nn.Module, model_id: str) -> ModelEntry:
        raise NotImplemented

    @abc.abstractmethod
    def all_entries(self) -> list[ModelEntry]:
        raise NotImplemented

    @abc.abstractmethod
    def fetch_entry(self, model_id: str) -> ModelEntry:
        raise NotImplemented

    @abc.abstractmethod
    def delete_entry(self, model_id: str, delete_state_dict: bool) -> None:
        raise NotImplemented


class ModelTinyDB(ModelDB):

    def __init__(
            self,
            base_path: str,
            db_file_name: str = '_model_db.json',
    ):
        self.base_path = base_path
        Path(base_path).mkdir(parents=True, exist_ok=True)

        self.db_file_name = db_file_name

        self.db = TinyDB(os.path.join(self.base_path, self.db_file_name))

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.db.close()

    def save_model_state_dict(
            self,
            model: nn.Module,
            model_id: str,
            parent_model_id: str,
            model_info: dict[str, Any],
            init_function: Optional[Callable[[], nn.Module]] = None,
    ) -> ModelEntry:
        serialized_init_function: Optional[str] = None
        if init_function is not None:
            serialized_init_function = inspect.getsource(init_function)

        entry: ModelEntry = {
            'model_id': model_id,
            'parent_model_id': parent_model_id,
            'state_dict_path': '',
            'model_info': model_info,
            'init_function': serialized_init_function,
            'last_update_time': str(datetime.datetime.now())
        }

        state_dict_path = os.path.join(self.base_path, f'{model_id}--state_dict.pth')
        entry['state_dict_path'] = state_dict_path

        torch.save(model.state_dict(), state_dict_path)

        self.db.upsert(entry, cond=self.create_model_id_query(model_id))

        return entry

    def load_model_state_dict(
            self,
            model: nn.Module,
            model_id: str
    ) -> ModelEntry:
        entry: ModelEntry = self.fetch_entry(model_id)
        state_dict = torch.load(entry['state_dict_path'])
        model.load_state_dict(state_dict)

        return entry

    def all_entries(self) -> list[ModelEntry]:
        return self.db.all()

    def fetch_entry(self, model_id: str) -> ModelEntry:
        search_result = self.db.search(self.create_model_id_query(model_id))

        if len(search_result) == 0:
            raise ValueError(f'Model id {model_id} not found')

        return search_result[0]

    def delete_entry(self, model_id: str, delete_state_dict: bool) -> None:
        if delete_state_dict:
            entry = self.fetch_entry(model_id)
            os.remove(entry['state_dict_path'])

        self.db.remove(cond=self.create_model_id_query(model_id))

    @staticmethod
    def create_model_id_query(model_id: str) -> QueryLike:
        entry_query = Query()
        return entry_query.model_id == model_id


class DummyModelDB(ModelDB):

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def close(self):
        pass

    def save_model_state_dict(
            self,
            model: nn.Module,
            model_id: str,
            parent_model_id: str,
            model_info: dict[str, Any],
            init_function: Optional[Callable[[], nn.Module]] = None,
    ) -> ModelEntry:
        pass

    def load_model_state_dict(
            self,
            model: nn.Module,
            model_id: str
    ) -> ModelEntry:
        raise NotImplementedError('Dummy ModelDB can not load models')

    def all_entries(self) -> list[ModelEntry]:
        raise NotImplementedError('Dummy ModelDB fetch entries')

    def fetch_entry(self, model_id: str) -> ModelEntry:
        raise NotImplementedError('Dummy ModelDB fetch entries')

    def delete_entry(self, model_id: str, delete_state_dict: bool) -> None:
        pass
