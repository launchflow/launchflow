try:
    from google.cloud import bigquery
except ImportError:
    bigquery = None  # type: ignore

import dataclasses
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs

_DATASET_NAME_PATTERN = r"^[\w]{1,1024}$"


@dataclasses.dataclass
class BigQueryDatasetOutputs(Outputs):
    gcp_project_id: str
    dataset_name: str


@dataclasses.dataclass
class BigQueryDatasetInputs(ResourceInputs):
    location: str
    allow_nonempty_delete: bool


class BigQueryDataset(GCPResource[BigQueryDatasetOutputs]):
    """A dataset in Google BigQuery.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/bigquery/docs/).

    ### Example Usage

    ```python
    from google.cloud import bigquery
    import launchflow as lf

    # Automatically creates / connects to a BigQuery Dataset in your GCP project
    dataset = lf.gcp.BigQueryDataset("my_dataset")

    schema = [
        bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("age", "INTEGER", mode="REQUIRED"),
    ]
    table = dataset.create_table("table_name", schema=schema)

    dataset.insert_table_data("table_name", [{"name": "Alice", "age": 30}])

    # You can also use the underlying resource directly
    # For example, for a table with columns name,age
    query = f\"\"\"
    SELECT name, age
    FROM `{dataset.dataset_id}.table_name`
    WHERE age > 10
    ORDER BY age DESC
    \"\"\"

    for row in dataset.client().query(query):
        print(row)
    ```
    """

    product = ResourceProduct.GCP_BIGQUERY_DATASET.value

    def __init__(
        self, name: str, *, location="US", allow_nonempty_delete: bool = False
    ) -> None:
        """Create a new BigQuery Dataset resource.

        **Args:**
        - `name (str)`: The name of the dataset. This must be globally unique.
        - `location (str)`: The location of the dataset. Defaults to "US".
        - `allow_nonempty_delete (bool)`: If True, the dataset can be deleted even if it is not empty. Defaults to False.
        """
        super().__init__(
            name=name,
            replacement_arguments={"location"},
        )
        if not re.match(_DATASET_NAME_PATTERN, name):
            raise ValueError(
                f"Invalid dataset ID `{name}`. Dataset IDs must be alphanumeric (plus underscores) and must be at most 1024 characters long."
            )
        # public metadata
        self.location = location
        self.allow_nonempty_delete = allow_nonempty_delete

    def inputs(self, environment_state: EnvironmentState) -> BigQueryDatasetInputs:
        return BigQueryDatasetInputs(
            resource_id=self.resource_id,
            location=self.location,
            allow_nonempty_delete=self.allow_nonempty_delete,
        )

    def _validate_installation(self) -> None:
        """Validate that the google-cloud-bigquery library is installed.

        **Raises:** `ImportError` if the library is not installed.
        """
        if bigquery is None:
            raise ImportError(
                "google-cloud-bigquery library is not installed. Please install it with `pip install launchflow[gcp]`."
            )

    @property
    def dataset_id(self) -> str:
        """Get the dataset id.

        **Returns:**
        - The dataset id.
        """
        return self.dataset().dataset_id

    def get_table_uuid(self, table_name: str) -> str:
        """Get the table UUID, {project_id}.{dataset_id}.{table_id}.

        **Args:**
        - `table_name (str)`: The name of the table.

        **Returns:**
        - The table UUID.
        """
        connection_info = self.outputs()
        return f"{connection_info.gcp_project_id}.{connection_info.dataset_name}.{table_name}"

    def client(self) -> "bigquery.Client":
        """Get the BigQuery Client object.

        **Returns:**
        - The [BigQuery Client](https://cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.client.Client) object.
        """
        self._validate_installation()

        connection_info = self.outputs()
        return bigquery.Client(project=connection_info.gcp_project_id)

    def dataset(self) -> "bigquery.Dataset":
        """Get the BigQuery Dataset object.

        **Returns:**
        - The [BigQuery Dataset](https://cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.dataset.Dataset) object.
        """
        self._validate_installation()

        connection_info = self.outputs()
        return bigquery.Dataset(
            f"{connection_info.gcp_project_id}.{connection_info.dataset_name}"
        )

    # TODO: Explore generating schema from a dataclass
    def create_table(
        self, table_name: str, *, schema: "Optional[List[bigquery.SchemaField]]" = None
    ) -> "bigquery.Table":
        """Create a table in the dataset.

        **Args:**
        - `table_name (str)`: The name of the table.
        - `schema (Optional[List[bigquery.SchemaField]])`: The schema of the table. Not required and defaults to None.

        **Returns:**
        - The [BigQuery Table](https://cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.table.Table) object.

        **Example usage:**
        ```python
        from google.cloud import bigquery
        import launchflow as lf

        dataset = lf.gcp.BigQueryDataset("my_dataset")

        schema = [
            bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("age", "INTEGER", mode="REQUIRED"),
        ]
        table = dataset.create_table("table_name", schema=schema)
        ```
        """
        self._validate_installation()

        # Create the table. It's OK to pass along None as the schema.
        table = bigquery.Table(self.get_table_uuid(table_name), schema)
        table = self.client().create_table(table)

        return table

    def delete_table(self, table_name: str) -> None:
        """Delete a table from the dataset.

        **Args:**
        - `table_name (str)`: The name of the table to delete.
        """
        self._validate_installation()

        table = bigquery.Table(self.get_table_uuid(table_name))
        self.client().delete_table(table)

    # TODO: Support more file formats
    def load_table_data_from_csv(self, table_name: str, file_path: Path) -> None:
        """Load data from a CSV file into a table.

        **Args:**
        - `table_name (str)`: The name of the table to load the data into.
        - `file_path (Path)`: The path to the CSV file to load.
        """
        self._validate_installation()

        table = self.client().get_table(self.get_table_uuid(table_name))

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            schema=table.schema,
        )
        with open(file_path, "rb") as f:
            job = self.client().load_table_from_file(f, table, job_config=job_config)

        # Wait for the data loading to complete.
        job.result()

    def insert_table_data(
        self, table_name: str, rows_to_insert: List[Dict[Any, Any]]
    ) -> None:
        """Insert in-memory data into a table.
        There's seems to be a bug in bigquery where if a table name is re-used (created and then deleted
        recently), streaming to it won't work. If you encounter an unexpected 404 error, try changing
        the table name.

        **Args:**
        - `table_name (str)`: The name of the table to insert the data into.
        - `rows_to_insert (List[Dict[Any, Any]])`: The data to insert into the table.

        **Raises:** ValueError if there were errors when inserting the data.
        """
        self._validate_installation()
        self.client().insert_rows_json(self.get_table_uuid(table_name), rows_to_insert)
