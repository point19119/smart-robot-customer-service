from abc import ABC,abstractmethod
from typing import Optional
from langchain_core.embeddings import Embeddings
from langchain_community.chat_models.tongyi import BaseChatModel
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
from utils.config_handler import rag_conf

class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self)->Optional[Embeddings | BaseChatModel]:
        pass


class ChatModleFActory(BaseModelFactory):
    def generator(self)->Optional[Embeddings | BaseChatModel]:
        return ChatTongyi(model=rag_conf["chat_model_name"])
    

class EmbeddingsFacyory(BaseModelFactory):
    def generator(self)->Optional[Embeddings | BaseChatModel]:
        return DashScopeEmbeddings(model=rag_conf["embedding_model_name"])
    

chat_modle = ChatModleFActory().generator()
embed_model = EmbeddingsFacyory().generator()