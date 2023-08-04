import openai
import pydantic
import functools


class ChatCompletionConfig(pydantic.BaseSettings):
    model: str = "gpt-3.5-turbo"
    temperature: float = 0
    functions: list = []
    messages: list = []
    api_key: str = pydantic.Field(default="", env="OPENAI_API_KEY")

    def merge(self, *args, **kwargs):
        _dict = self.dict(exclude_unset=True)
        for key, value in kwargs.items():
            if type(value) == list:
                _dict[key] = _dict.get(key, []) + value
            else:
                _dict[key] = value
        return _dict


class ChatCompletion(openai.ChatCompletion):
    def __new__(cls, *args, **kwargs):
        subclass = type(
            "ChatCompletion",
            (ChatCompletion,),
            {"__config__": ChatCompletionConfig(**kwargs)},
        )
        return subclass

    @classmethod
    def create(cls, *args, **kwargs):
        config = getattr(cls, "__config__", ChatCompletionConfig())
        payload = config.merge(**kwargs)
        return cls.observer(super(ChatCompletion, cls).create)(*args, **payload)

    @classmethod
    async def acreate(cls, *args, **kwargs):
        config = getattr(cls, "__config__", ChatCompletionConfig())
        payload = config.merge(**kwargs)
        return await cls.observer(super(ChatCompletion, cls).acreate)(*args, **payload)

    @staticmethod
    def observer(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ChatCompletion.on_send(*args, **kwargs)
            response = func(*args, **kwargs)
            response = ChatCompletion.on_receive(response, *args, **kwargs)
            return response

        return wrapper

    @classmethod
    def on_send(cls, *args, **kwargs):
        pass

    @classmethod
    def on_receive(cls, result, *args, **kwargs):
        return result
