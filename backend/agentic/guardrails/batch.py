import asyncio
from typing import AsyncGenerator, Awaitable, Callable, Generic, List, Optional, TypeVar

from .base import BaseDetector, Extra, ExtrasImport
T = TypeVar("T")
R = TypeVar("R")

Extra.extras = {}

DEFAULT_PROMPT_INJECTION_MODEL = "protectai/deberta-v3-base-prompt-injection-v2"

PRESIDIO_EXTRA = Extra(
    "PII and Secrets Scanning (using Presidio)",
    "Enables the detection of personally identifiable information (PII) and secret scanning in text",
    {
        "presidio_analyzer": ExtrasImport("presidio_analyzer", "presidio-analyzer", ">=2.2.354"),
        "spacy": ExtrasImport("spacy", "spacy", ">=3.7.5"),
    },
)

transformers_extra = Extra(
    "Transformers",
    "Enables the use of `transformer`-based models and classifiers in the analyzer",
    {
        "transformers": ExtrasImport("transformers", "transformers", ">=4.41.1"),
        "torch": ExtrasImport("torch", "torch", ">=2.3.0"),
    },
)

class BatchAccumulator(Generic[T, R]):
    """
    A simple asyncio batch accumulator that collects items and processes them in batches.

    This is useful for batching API calls, database operations, or other operations
    where processing items in bulk is more efficient than processing them individually.
    """

    def __init__(
        self,
        batch_processor: Callable[[List[T]], Awaitable[List[R]]],
        max_batch_size: int = 100,
        max_wait_time: float = 1.0,
    ):
        """
        Initialize a new batch accumulator.

        Args:
            batch_processor: Async function that processes a batch of items
            max_batch_size: Maximum number of items to collect before processing
            max_wait_time: Maximum time to wait before processing a partial batch (in seconds)
        """
        self.batch_processor = batch_processor
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time

        self._queue: List[asyncio.Future[R]] = []
        self._items: List[T] = []
        self._batch_task: Optional[asyncio.Task] = None
        self._timer_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._running = False

    async def start(self) -> None:
        """Start the batch accumulator."""
        if self._running:
            return

        self._running = True
        self._timer_task = asyncio.create_task(self._timer_loop())

    async def stop(self) -> None:
        """Stop the batch accumulator and process any remaining items."""
        if not self._running:
            return

        self._running = False

        if self._timer_task:
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
               pass 

        # Process any remaining items
        if self._items:
            await self._process_batch()

    async def add(self, item: T) -> R:
        """
        Add an item to the batch and return a future that will resolve when the item is processed.

        Args:
            item: The item to add to the batch

        Returns:
            A Future that resolves to the result of processing the item
        """
        if not self._running:
            raise RuntimeError("BatchAccumulator is not running. Call start() first.")

        future: asyncio.Future[R] = asyncio.Future()

        async with self._lock:
            self._items.append(item)
            self._queue.append(future)

            if len(self._items) >= self.max_batch_size:
                # We've hit the max batch size, process immediately
                await self._process_batch()

        return await future

    async def _timer_loop(self) -> None:
        """Background task that processes batches after max_wait_time has elapsed."""
        try:
            while self._running:
                await asyncio.sleep(self.max_wait_time)
                async with self._lock:
                    if self._items:
                        await self._process_batch()
        except asyncio.CancelledError:
            # if this gets cancelled, we are shutting down this instance
            # new start() call will re-initialize the instance
            self._running = False
        except Exception:
            import traceback

            traceback.print_exc()

    async def _process_batch(self) -> None:
        """Process the current batch of items."""
        if not self._items:
            return

        items = self._items.copy()
        futures = self._queue.copy()
        self._items = []
        self._queue = []

        try:
            results = await self.batch_processor(items)

            # Resolve futures with results
            if len(results) != len(futures):
                error = ValueError(
                    f"Batch processor returned {len(results)} results for {len(futures)} items"
                )
                for future in futures:
                    if not future.done():
                        future.set_exception(error)
            else:
                for future, result in zip(futures, results):
                    if not future.done():
                        future.set_result(result)
        except Exception as e:
            # If batch processing fails, propagate the error to all futures
            for future in futures:
                if not future.done():
                    future.set_exception(e)



class BatchedDetector(BaseDetector):
    """
    A batched detector that uses a BatchAccumulator to process items in batches.

    To subclass, implement the `adetect_batch` method.
    """

    def __init__(self, max_batch_size: int = 1, max_wait_time: float = 0.1):
        # separate accumulators for any serialized args-kwargs combination
        self.accumulators = {}
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time

    def get_accumulator(self, args, kwargs):
        key = (args, tuple(kwargs.items()))
        if key not in self.accumulators:

            async def batch_processor(texts):
                return await self.adetect_all_batch(texts, *args, **kwargs)

            self.accumulators[key] = BatchAccumulator(
                batch_processor=batch_processor,
                max_batch_size=self.max_batch_size,
                max_wait_time=self.max_wait_time,
            )
        return self.accumulators[key]

    async def adetect_all_batch(self, texts, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement the adetect_all_batch method")

    async def adetect(self, text, *args, **kwargs):
        result = await self.adetect_all(text, *args, **kwargs)
        return len(result) > 0

    async def adetect_all(self, text, *args, **kwargs):
        accumulator = self.get_accumulator(args, kwargs)
        await accumulator.start()
        return await accumulator.add(text)

    def detect(
            self, 
            text, 
            *args, 
            **kwargs
    ):
        raise NotImplementedError(
            "Batched detectors do not support synchronous detect(). Please use adetect() instead"
        )

    def detect_all(self, text, *args, **kwargs):
        raise NotImplementedError(
            "Batched detectors do not support synchronous detect_all(). Please use adetect_all() instead"
        )



class PromptInjectionAnalyzer(BatchedDetector):
    """Analyzer for detecting prompt injections via classifier.

    The analyzer uses a pre-trained classifier (e.g., a model available on Huggingface) to detect prompt injections in text.
    Note that this is just a heuristic, and relying solely on the classifier is not sufficient to prevent the security vulnerabilities.
    """

    def __init__(self):
        super().__init__(max_batch_size=16, max_wait_time=0.1)
        self.pipe_store = dict()

    async def preload(self):
        # preloads the model
        await self.adetect("Testing")

    def _load_model(self, model):
        pipeline = transformers_extra.package("transformers").import_names("pipeline")
        self.pipe_store[model] = pipeline("text-classification", model=model, top_k=None)

    def _get_model(self, model):
        return self.pipe_store[model]

    def _has_model(self, model):
        return model in self.pipe_store

    async def adetect_all_batch(
        self, texts: list[str], model: str = DEFAULT_PROMPT_INJECTION_MODEL, threshold: float = 0.9
    ) -> bool:
        """Detects whether text contains prompt injection.

        Args:
            text: The text to analyze.
            model: The model to use for prompt injection detection.
            threshold: The threshold for the model score above which text is considered prompt injection.

        Returns:
            A boolean indicating whether the text contains prompt injection.
        """
        if not self._has_model(model):
            self._load_model(model)

        # make sure texts is list of str
        assert type(texts) is list and all(
            type(t) is str for t in texts
        ), "texts must be a list of str"

        model = self._get_model(model)
        scores = model(texts)

        return [
            [scores[i][0]["label"] == "INJECTION" and scores[i][0]["score"] > threshold]
            for i in range(len(scores))
        ]

    async def adetect(self, text, *args, **kwargs):
        result = await self.adetect_all(text, *args, **kwargs)
        return result[0] is True
