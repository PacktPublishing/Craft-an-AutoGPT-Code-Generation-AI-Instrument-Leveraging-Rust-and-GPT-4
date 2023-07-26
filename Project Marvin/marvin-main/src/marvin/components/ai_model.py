import functools
from typing import Optional, Type, TypeVar

from pydantic import BaseModel

from marvin.engine.executors import OpenAIExecutor
from marvin.engine.language_models import ChatLLM
from marvin.prompts import library as prompt_library
from marvin.prompts import render_prompts
from marvin.tools.format_response import FormatResponse
from marvin.utilities.async_utils import run_sync
from marvin.utilities.types import LoggerMixin

T = TypeVar("T")


extract_structured_data_prompts = [
    prompt_library.System(content="""
            The user will provide context as text that you need to parse into a
            structured form. To validate your response, you must call the
            `FormatResponse` function. Use the provided text to extract or infer
            any parameters needed by `FormatResponse`, including any missing
            data.
            """),
    prompt_library.Now(),
    prompt_library.User(content="""The text to parse: {{ input_text }}"""),
]

generate_structured_data_prompts = [
    prompt_library.System(content="""
            The user may provide context as text that you need to parse to
            generate synthetic data. To validate your response, you must call
            the `FormatResponse` function. Use the provided text to generate or
            invent any parameters needed by `FormatResponse`, including any
            missing data. It is okay to make up representative data.
            """),
    prompt_library.Now(),
    prompt_library.User(content="""The text to parse: {{ input_text }}"""),
]


class AIModel(LoggerMixin, BaseModel):
    """Base class for AI models."""

    def __init__(
        self,
        text_: str = None,
        *,
        instructions_: str = None,
        model_: ChatLLM = None,
        **kwargs,
    ):
        """
        Args:
            text_: The text to parse into a structured form.
            instructions_: Additional instructions to assist the model.
            model_: The language model to use.
        """
        # the loggingmixin hasn't been instantiated yet

        if text_:
            if model_ is None:
                model_ = ChatLLM()

            # use the extract constructor to build the class
            kwargs = self.__class__.extract(
                text_=text_,
                instructions_=instructions_,
                model_=model_,
                as_dict_=True,
                **kwargs,
            )
        super().__init__(**kwargs)

    @classmethod
    def route(cls):
        def extract(q: str) -> cls:
            return cls(q)

        return extract

    @classmethod
    def extract(
        cls,
        text_: str = None,
        *,
        instructions_: str = None,
        model_: ChatLLM = None,
        as_dict_: bool = False,
        **kwargs,
    ):
        """Class method to extract structured data from text.

        Args:
            text_: The text to parse into a structured form.
            instructions_: Additional string instructions to assist the model.
            model_: The language model to use.
            as_dict_: Whether to return the result as a dictionary or as an
                instance of this class.
            kwargs: Additional keyword arguments to pass to the constructor.
        """
        if model_ is None:
            model_ = ChatLLM()
        prompts = extract_structured_data_prompts
        if instructions_:
            prompts.append(prompt_library.System(content=instructions_))
        messages = render_prompts(prompts, render_kwargs=dict(input_text=text_))
        arguments = cls._call_format_response_with_retry(model_, messages)
        arguments.update(kwargs)
        if as_dict_:
            return arguments
        else:
            return cls(**arguments)

    @classmethod
    def generate(
        cls,
        text_: str = None,
        *,
        instructions_: str = None,
        model_: ChatLLM = None,
        **kwargs,
    ):
        """Class method to generate structured data from text.

        Args:
            text_: The text to parse into a structured form.
            instructions_: Additional instructions to assist the model.
            model_: The language model to use.
            kwargs: Additional keyword arguments to pass to the constructor.
        """
        if model_ is None:
            model_ = ChatLLM()
        prompts = generate_structured_data_prompts
        if instructions_:
            prompts.append(prompt_library.System(content=instructions_))
        messages = render_prompts(prompts, render_kwargs=dict(input_text=text_))
        arguments = cls._call_format_response_with_retry(model_, messages)
        arguments.update(kwargs)
        return cls(**arguments)

    @classmethod
    def _call_format_response_with_retry(cls, model, messages):
        executor = OpenAIExecutor(
            engine=model,
            functions=[FormatResponse(type_=cls).as_openai_function()],
            function_call={"name": "FormatResponse"},
            max_iterations=3,
        )

        llm_call = executor.start(prompts=messages)
        responses = run_sync(llm_call)
        response = responses[-1]

        if response.data.get("is_error"):
            raise TypeError(
                f"Could not build AI Model; most recent error was: {response.content}"
            )

        return response.data.get("arguments", {})


def ai_model(
    cls: Optional[Type[T]] = None,
    *,
    instructions: str = None,
    model: ChatLLM = None,
) -> Type[T]:
    """Decorator to add AI model functionality to a class.

    Args:
        cls: The class to decorate.
        instructions: Additional instructions to assist the model.
        model: The language model to use.

    Example:
        Hydrate a class schema from a natural language description:
        ```python
        from pydantic import BaseModel
        from marvin import ai_model

        @ai_model
        class Location(BaseModel):
            city: str
            state: str
            latitude: float
            longitude: float

        Location("no way, I also live in the windy city")
        # Location(
        #   city='Chicago', state='Illinois', latitude=41.8781, longitude=-87.6298
        # )
        ```
    """
    if cls is None:
        return functools.partial(ai_model, instructions=instructions, model=model)

    # create a new class that subclasses AIModel and the original class
    ai_model_class = type(cls.__name__, (AIModel, cls), {})

    # Use setattr() to add the original class's methods and class variables to
    # the new class do not attempt to copy dunder methods
    for name, attr in cls.__dict__.items():
        if not name.startswith("__"):
            setattr(ai_model_class, name, attr)

    ai_model_class.__init__ = functools.partialmethod(
        ai_model_class.__init__, instructions_=instructions, model_=model
    )

    return ai_model_class
