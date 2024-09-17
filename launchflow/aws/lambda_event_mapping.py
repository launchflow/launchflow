from dataclasses import dataclass

import launchflow as lf
from launchflow.aws.lambda_function import LambdaFunction
from launchflow.aws.resource import AWSResource
from launchflow.aws.sqs import SQSQueue
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Depends, Outputs
from launchflow.resource import ResourceInputs


@dataclass
class LambdaEventMappingInputs(ResourceInputs):
    event_source_arn: str
    function_arn: str
    batch_size: int
    # filter_criteria TODO: Support filter criteria


@dataclass
class LambdaEventMappingOutputs(Outputs):
    pass


class LambdaEventMapping(AWSResource[LambdaEventMappingOutputs]):
    """A mapping between an event source and a Lambda function.

    ### Example Usage
    ```python
    import launchflow as lf

    mapping = lf.aws.LambdaEventMapping("my-event-mapping")
    ```
    """

    product = ResourceProduct.AWS_LAMBDA_EVENT_MAPPING.value

    def __init__(
        self,
        name: str,
        *,
        lambda_container: LambdaFunction,
        sqs_queue: SQSQueue,
        batch_size: int = 10,
    ) -> None:
        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
        )
        self.lambda_container = lambda_container
        self.sqs_queue = sqs_queue
        self.batch_size = batch_size

    def inputs(self, environment_state: EnvironmentState) -> LambdaEventMappingInputs:
        event_source_arn = Depends(self.sqs_queue).aws_arn  # type: ignore
        function_arn = Depends(self.lambda_container).aws_arn  # type: ignore
        return LambdaEventMappingInputs(
            resource_id=self.resource_id,
            event_source_arn=event_source_arn,
            function_arn=function_arn,
            batch_size=self.batch_size,
        )
