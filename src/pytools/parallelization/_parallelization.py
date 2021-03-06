"""
Core implementation of :mod:`pytools.parallelization`.
"""
import itertools
import logging
from abc import ABCMeta, abstractmethod
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import joblib

from ..api import AllTracker, deprecated, inheritdoc, to_tuple

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = [
    "ParallelizableMixin",
    "Job",
    "JobQueue",
    "JobRunner",
    "SimpleQueue",
    "NestedQueue",
]

#
# Type variables
#

T = TypeVar("T")
T_JobRunner = TypeVar("T_JobRunner", bound="JobRunner")
T_Job_Result = TypeVar("T_Job_Result")
T_Queue_Result = TypeVar("T_Queue_Result")


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class ParallelizableMixin:
    """
    Mix-in class that supports parallelizing one or more operations using joblib.
    """

    def __init__(
        self,
        *,
        n_jobs: Optional[int] = None,
        shared_memory: Optional[bool] = None,
        pre_dispatch: Optional[Union[str, int]] = None,
        verbose: Optional[int] = None,
    ) -> None:
        """
        :param n_jobs: number of jobs to use in parallel;
            if ``None``, use joblib default (default: ``None``)
        :param shared_memory: if ``True``, use threads in the parallel runs; if
            ``False``, use multiprocessing (default: ``False``)
        :param pre_dispatch: number of batches to pre-dispatch;
            if ``None``, use joblib default (default: ``None``)
        :param verbose: verbosity level used in the parallel computation;
            if ``None``, use joblib default (default: ``None``)
        """
        super().__init__()
        #: Number of jobs to use in parallel; if ``None``, use joblib default.
        self.n_jobs = n_jobs

        #: If ``True``, use threads in the parallel runs;
        #: if ``False``, use multiprocessing.
        self.shared_memory = shared_memory

        #: Number of batches to pre-dispatch; if ``None``, use joblib default.
        self.pre_dispatch = pre_dispatch

        #: Verbosity level used in the parallel computation;
        #: if ``None``, use joblib default.
        self.verbose = verbose

        self._parallel_kwargs = {
            name: value
            for name, value in [
                ("n_jobs", n_jobs),
                ("require", "sharedmem" if shared_memory else None),
                ("pre_dispatch", pre_dispatch),
                ("verbose", verbose),
            ]
            if value is not None
        }

    @deprecated(message="this method is deprecated and will be removed in v1.1")
    def _parallel(self) -> joblib.Parallel:
        """
        Generate a :class:`joblib.Parallel` instance using the parallelization
        parameters of ``self``.

        `This method is deprecated and will be removed in v1.1.`

        :meta public:
        :return: the new :class:`joblib.Parallel` instance
        """
        return joblib.Parallel(**self._parallel_kwargs)

    @staticmethod
    @deprecated(message="this method is deprecated and will be removed in v1.1")
    def _delayed(
        function: Callable[..., T]
    ) -> Callable[..., Tuple[Callable[..., T], Tuple, Dict[str, Any]]]:
        """
        Decorate the given function for delayed execution.

        Convenience method preventing having to import :mod:`joblib`;
        defers to function :func:`joblib.delayed`.

        `This method is deprecated and will be removed in v1.1.`

        :meta public:
        :param function: the function to be delayed
        :return: the delayed function
        """
        return joblib.delayed(function)


class Job(Generic[T_Job_Result], metaclass=ABCMeta):
    """
    A job to be run as part of a parallelizable :class:`.JobQueue`.
    """

    @abstractmethod
    def run(self) -> T_Job_Result:
        """
        Run this job.

        :return: the result produced by the job
        """
        pass

    @classmethod
    def delayed(
        cls, function: Callable[..., T_Job_Result]
    ) -> "Callable[..., Job[T_Job_Result]]":
        """
        A decorator creating a `delayed` version of the given function which,
        if called with arguments, does not run immediately but instead returns a
        :class:`.Job` that will call the function with the given arguments.

        Once the job is run, it will call the function with the given arguments.

        :param function: a function returning the job result
        :return: the delayed version of the function
        """

        @wraps(function)
        def _delayed_function(*args, **kwargs: Any) -> Job[T_Job_Result]:
            @inheritdoc(match="""[see superclass]""")
            class _Job(Job[T_Job_Result]):
                def run(self) -> T_Job_Result:
                    """[see superclass]"""
                    return function(*args, **kwargs)

            return _Job()

        return _delayed_function


class JobQueue(Generic[T_Job_Result, T_Queue_Result], metaclass=ABCMeta):
    """
    A queue of jobs to be run in parallel, generating a collective result.

    Supports :meth:`.len` to determine the number of jobs in this queue.
    """

    @abstractmethod
    def jobs(self) -> Iterable[Job[T_Job_Result]]:
        """
        Iterate the jobs in this queue.

        :return: the jobs in this queue
        """
        pass

    def on_run(self) -> None:
        """
        Called by :meth:`.JobRunner.run` when starting to run the jobs in this queue.

        Does nothing by default; overload as required to initialize the queue before
        each run.
        """

    @abstractmethod
    def collate(self, job_results: List[T_Job_Result]) -> T_Queue_Result:
        """
        Called by :meth:`.JobRunner.run` to collate the results of all jobs once they
        have all been run.

        :param job_results: list of job results, ordered corresponding to the sequence
            of jobs generated by method :meth:`.jobs`
        :return: the collated result of running the queue
        """
        pass

    @abstractmethod
    def __len__(self) -> int:
        pass


class JobRunner(ParallelizableMixin):
    """
    Runs job queues in parallel and collates results.
    """

    @classmethod
    def from_parallelizable(
        cls: Type[T_JobRunner], parallelizable: ParallelizableMixin
    ) -> T_JobRunner:
        """
        Create a new :class:`JobRunner` using the parameters of the given parallelizable
        object.

        :param parallelizable: the parallelizable instance whose parameters to use
            for the job runner
        :return: the new job runner
        """
        cls: Type[T_JobRunner]
        return cls(
            n_jobs=parallelizable.n_jobs,
            shared_memory=parallelizable.shared_memory,
            pre_dispatch=parallelizable.pre_dispatch,
            verbose=parallelizable.verbose,
        )

    def run_jobs(self, *jobs: Job[T_Job_Result]) -> List[T_Job_Result]:
        """
        Run all given jobs in parallel.

        :param jobs: the jobs to run in parallel
        :return: the results of all jobs
        """
        simple_queue: JobQueue[T_Job_Result, List[T_Job_Result]] = SimpleQueue(
            jobs=jobs
        )
        return self.run_queue(simple_queue)

    def run_queue(self, queue: JobQueue[Any, T_Queue_Result]) -> T_Queue_Result:
        """
        Run all jobs in the given queue, in parallel.

        :param queue: the queue to run
        :return: the result of all jobs, collated using method :meth:`.JobQueue.collate`
        :raise AssertionError: the number of results does not match the number of jobs
            in the queue
        """

        queue.on_run()

        with self._parallel() as parallel:
            results: List[T_Job_Result] = parallel(
                joblib.delayed(lambda job: job.run())(job) for job in queue.jobs()
            )

        if len(results) != len(queue):
            raise AssertionError(
                f"Number of results ({len(results)}) does not match length of "
                f"queue ({len(queue)}): check method {type(queue).__name__}.__len__()"
            )

        return queue.collate(job_results=results)

    def run_queues(
        self, *queues: JobQueue[Any, T_Queue_Result]
    ) -> Iterator[T_Queue_Result]:
        """
        Run all jobs in the given queues, in parallel.

        :param queues: the queues to run
        :return: the result of all jobs, collated per queue using method
            :meth:`.JobQueue.collate`
        :raise AssertionError: the number of results does not match the total number of
            jobs in the queues
        """

        for queue in queues:
            queue.on_run()

        with self._parallel() as parallel:
            results: List[T_Job_Result] = parallel(
                joblib.delayed(lambda job: job.run())(job)
                for queue in queues
                for job in queue.jobs()
            )

        queues_len = sum(len(queue) for queue in queues)
        if len(results) != queues_len:
            raise AssertionError(
                f"Number of results ({len(results)}) does not match length of "
                f"queues ({queues_len}): check method __len__() of the queue class(es)"
            )

        first_job = 0
        for queue in queues:
            last_job = first_job + len(queue)
            yield queue.collate(results[first_job:last_job])
            first_job = last_job

    def _parallel(self) -> joblib.Parallel:
        # Generate a :class:`joblib.Parallel` instance using the parallelization
        # parameters of ``self``.
        return joblib.Parallel(**self._parallel_kwargs)


@inheritdoc(match="""[see superclass]""")
class SimpleQueue(JobQueue[T_Job_Result, List[T_Job_Result]], Generic[T_Job_Result]):
    """
    A simple queue, running a given list of jobs and returning their results as a list.
    """

    #: The jobs run by this queue.
    _jobs: Tuple[T_Job_Result, ...]

    def __init__(self, jobs: Iterable[Job[T_Job_Result]]) -> None:
        """
        :param jobs: jobs to be run by this queue in the given order
        """
        super().__init__()
        self._jobs = to_tuple(jobs)

    def jobs(self) -> Iterable[Job[T_Job_Result]]:
        """[see superclass]"""
        return self._jobs

    def collate(self, job_results: List[T_Job_Result]) -> T_Queue_Result:
        """
        Return the list of job results as-is, without collating them any further.

        :param job_results: list of job results, ordered corresponding to the sequence
            of jobs generated by method :meth:`.jobs`
        :return: the identical list of job results
        """
        return job_results

    def __len__(self) -> int:
        return len(self._jobs)


@inheritdoc(match="""[see superclass]""")
class NestedQueue(JobQueue[T_Job_Result, List[T_Job_Result]]):
    """
    Runs all jobs in a given list of compatible queues and returns their results as a
    flat list.
    """

    #: The queues run by this queue.
    queues: Tuple[JobQueue[T_Job_Result, List[T_Job_Result]], ...]

    def __init__(
        self, queues: Sequence[JobQueue[T_Job_Result, List[T_Job_Result]]]
    ) -> None:
        """
        :param queues: queues to be run by this queue in the given order
        """
        super().__init__()
        self.queues = to_tuple(queues)

    def jobs(self) -> Iterable[Job[T_Job_Result]]:
        """[see superclass]"""
        return itertools.chain.from_iterable(queue.jobs() for queue in self.queues)

    def collate(self, job_results: List[T_Job_Result]) -> T_Queue_Result:
        """
        Return the list of job results as-is, without collating them any further.

        :param job_results: list of job results, ordered corresponding to the sequence
            of jobs generated by method :meth:`.jobs`
        :return: the identical list of job results
        """
        return job_results

    def __len__(self) -> int:
        return sum(len(queue) for queue in self.queues)


__tracker.validate()
